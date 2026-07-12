import os
import sys

# Ensure project root is in the system path for seamless relative imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay

import rasterio
from rasterio.windows import from_bounds
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from pystac_client import Client
import planetary_computer

# Import pipeline steps from modularized files
from src.load_terrain import load_terrain, select_bbox_interactively
from src.generate_terrain import generate_terrain
from src.build_quadtree import quadtree_regions, calculate_region_stats, draw_quadtree
from src.create_points import (
    sample_poisson_disk_points_numba,
    round_and_clamp_points,
    filter_water_points,
    build_height_point_cloud,
    get_edges,
    plot_2d_delaunay,
    plot_3d_pointcloud_pyvista,
    plot_terrain_surface_pyvista,
    find_nearest_point_index,
    filter_border_edges
)
from src.create_graph import make_graph, astar, smooth_path
from src.select_points import select_points
from src.config import (
    DEFAULT_TERRAIN_PATH,
    DEFAULT_METRIC_RESOLUTION,
    GEOGRAPHIC_DEGREE_THRESHOLD,
    INITIAL_QUADTREE_MAX_DEPTH,
    INITIAL_QUADTREE_MIN_VARIANCE,
    VARIANCE_PERCENTILE_THRESHOLD,
    FINAL_QUADTREE_MAX_DEPTH,
    DEFAULT_MIN_DEPTH,
    MAIN_MAX_RADIUS,
    MAIN_MIN_RADIUS,
    MAIN_SLOPE_PENALTY_ALPHA,
    SMOOTH_PATH,
    SMOOTH_PATH_LAMBDA,
    APPLY_WATER_BODY_MASK,
    WATER_BODY_ELEVATION
)

def main():
    
    # 1. Generate/Load Terrain
    #file_path = DEFAULT_TERRAIN_PATH
    #terrain = load_terrain(file_path=file_path)

    catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)

    # Let user select bbox interactively
    print("Opening map for bounding box selection...")
    bbox = select_bbox_interactively(start_lat=0.0, start_lon=0.0, zoom=1)
    if bbox is None:
        print("No bounding box selected. Using default (Norway region).")
        bbox = [5.433225, 60.405077, 5.599050, 60.486869]

    search = catalog.search(collections=["cop-dem-glo-30"], bbox=bbox)

    items = list(search.items())
    print(f"Found {len(items)} DEM tiles covering this area.\n")
    
    terrain = None
    res_x, res_y = None, None
    bounds = None
    wbm_aligned = None

    if items:
        env_options = {
            'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR',
            'CPL_VSIL_CURL_ALLOWED_EXTENSIONS': 'tif',
            'VSI_CACHE': True
        }
        
        with rasterio.Env(**env_options):
            src_files = []
            try:
                for item in items:
                    cog_url = item.assets["data"].href
                    print(f"Opening DEM tile: {item.id}")
                    src = rasterio.open(cog_url)
                    src_files.append(src)
                
                if src_files:
                    # Merge all tiles and clip/crop directly to our bbox
                    mosaic, out_trans = merge(src_files, bounds=bbox)
                    # Extract the first band and cast to float32
                    terrain = mosaic[0].astype(np.float32)
                    
                    # Store resolution and bounds from the first source tile
                    res_x, res_y = src_files[0].res
                    bounds = src_files[0].bounds
                    print(f"Successfully loaded and merged {len(src_files)} tiles covering the selected bounding box.")

                    # Apply Water Body Mask if enabled
                    if APPLY_WATER_BODY_MASK:
                        print("\nQuerying Water Body Mask (JRC GSW)...")
                        try:
                            search_gsw = catalog.search(collections=["jrc-gsw"], bbox=bbox)
                            items_gsw = list(search_gsw.items())
                            if items_gsw:
                                print(f"Found {len(items_gsw)} GSW tiles. Loading and aligning...")
                                src_files_gsw = []
                                try:
                                    for item_gsw in items_gsw:
                                        gsw_url = item_gsw.assets["extent"].href
                                        src_files_gsw.append(rasterio.open(gsw_url))
                                    
                                    gsw_mosaic, gsw_trans = merge(src_files_gsw, bounds=bbox)
                                    gsw_raw = gsw_mosaic[0]
                                    gsw_crs = src_files_gsw[0].crs
                                    dem_crs = src_files[0].crs
                                    
                                    wbm_aligned = np.zeros_like(terrain, dtype=np.uint8)
                                    reproject(
                                        source=gsw_raw,
                                        destination=wbm_aligned,
                                        src_transform=gsw_trans,
                                        src_crs=gsw_crs,
                                        dst_transform=out_trans,
                                        dst_crs=dem_crs,
                                        resampling=Resampling.nearest
                                    )
                                    
                                    num_water_pixels = np.sum(wbm_aligned == 1)
                                    terrain[wbm_aligned == 1] = WATER_BODY_ELEVATION
                                    print(f"Successfully applied water body mask. Found {num_water_pixels} water pixels.")
                                finally:
                                    for s in src_files_gsw:
                                        s.close()
                            else:
                                print("No Water Body Mask tiles found for this area. Skipping.")
                        except Exception as e:
                            print(f"Warning: Failed to load or apply Water Body Mask: {e}")
            finally:
                for src in src_files:
                    src.close()
    
    if terrain is None:
        raise ValueError("Failed to load terrain. No STAC items found or loading failed.")

    # Mask ocean/sea-level pixels (elevation <= 0) as water
    terrain[terrain <= 0.0] = WATER_BODY_ELEVATION

    height, width = terrain.shape
    print(f"Loaded terrain matrix of size: {width}x{height} (width x height)")


    # Load spatial resolution
    dx, dy = DEFAULT_METRIC_RESOLUTION, DEFAULT_METRIC_RESOLUTION
    if res_x is not None and res_y is not None and bounds is not None:
        # If the resolution is extremely small (< 0.1), the coordinates are in degrees rather than meters
        R = 6371000
        if res_x < GEOGRAPHIC_DEGREE_THRESHOLD:
            # Find the borders of the tif file (left/right are in longitude, bottom/top are in latitude)
            left, bottom, right, top = bounds
            # Use the center latitude for a more accurate conversion from degrees to meters
            center_lat = (bottom + top) / 2.0
            center_lat_rad = np.radians(center_lat)

            # Use formula for converting degrees to meters at a given latitude
            dx = res_x * (np.cos(center_lat_rad) * np.pi * R) / 180
            dy = res_y *(np.pi * R) / 180
            print("\n" + "="*80)
            print("The loaded GeoTIFF uses geographic degrees (e.g. EPSG:4326) instead of meters.")
            print(f"The code will estimate the metric pixel size at this latitude as:")
            print(f"          dx = {dx:.2f}m, dy = {dy:.2f}m per pixel.")
            print("="*80 + "\n")
        else:
            dx, dy = res_x, res_y
            print(f"Loaded spatial resolution from TIFF: dx={dx:.3f}m, dy={dy:.3f}m per pixel")
    else:
        print("Using default spatial resolution: dx=1.0, dy=1.0 (No TIFF resolution found)")

    # 2. Build Quadtree
    print("Decomposing terrain using Quadtree...")
    # Calculate initial regions for variance statistics
    initial_regions = quadtree_regions(terrain, max_depth=INITIAL_QUADTREE_MAX_DEPTH, min_variance=INITIAL_QUADTREE_MIN_VARIANCE)
    stats = calculate_region_stats(terrain, initial_regions)
    stats_variances = [s['var'] for s in stats]

    # Filter regions based on the 95th percentile of variance
    min_variance = np.percentile(stats_variances, VARIANCE_PERCENTILE_THRESHOLD) if len(stats_variances) > 0 else 0
    regions = quadtree_regions(terrain, max_depth=FINAL_QUADTREE_MAX_DEPTH, min_variance=min_variance)
    print(f"Quadtree generated {len(regions)} leaf regions.")
    
    # Plot raw terrain and allow user to select start/end coordinates interactively
    start_coord, end_coord = select_points(terrain, dx=dx, dy=dy)

    # 3. Sample Points
    print("Sampling points, this could take a while depending on the parameters and size of the terrain.")
    raw_points = sample_poisson_disk_points_numba(
        regions,
        min_depth=DEFAULT_MIN_DEPTH,
        max_depth=FINAL_QUADTREE_MAX_DEPTH,
        max_radius=MAIN_MAX_RADIUS,
        min_radius=MAIN_MIN_RADIUS
    )
    print("Points generated succesfully.")
    points = round_and_clamp_points(raw_points, width, height)
    if APPLY_WATER_BODY_MASK:
        points = filter_water_points(points, terrain, wbm_mask=wbm_aligned, water_elevation=WATER_BODY_ELEVATION)
    height_points = build_height_point_cloud(points, terrain)
    print(f"Sampled {len(height_points)} 3D points.")

    # 4. Triangulate and Extract Edges
    print("Calculating Delaunay Triangulation and extracting edges...")
    triangulation = Delaunay(points)
    raw_edges = get_edges(triangulation)
    edges = filter_border_edges(raw_edges, points, width, height)
    print(f"Extracted {len(raw_edges)} unique edges.")

    # 5. Build Graph
    slope_penalty_alpha = MAIN_SLOPE_PENALTY_ALPHA
    print(f"Building NetworKit Graph (slope penalty alpha = {slope_penalty_alpha})...")
    graph = make_graph(
        edges, height_points, dx=dx, dy=dy, alpha=slope_penalty_alpha,
        wbm_mask=wbm_aligned if APPLY_WATER_BODY_MASK else None,
        terrain=terrain,
        water_elevation=WATER_BODY_ELEVATION if APPLY_WATER_BODY_MASK else None
    )

    # 6. Run Pathfinding (A*)
    # Specify coordinates as (x, y) to find nearest points. If None, defaults to first/last node.
    # (Coordinates selected interactively during step 2)

    if start_coord is not None:
        source_idx = find_nearest_point_index(points, start_coord)
        nearest_start = points[source_idx]
        start_dist = np.linalg.norm(nearest_start - np.array(start_coord))
        print(f"Nearest point to start coord {start_coord} is node {source_idx} at {tuple(nearest_start)} (dist: {start_dist:.2f} px)")
    else:
        source_idx = 0

    if end_coord is not None:
        target_idx = find_nearest_point_index(points, end_coord)
        nearest_end = points[target_idx]
        end_dist = np.linalg.norm(nearest_end - np.array(end_coord))
        print(f"Nearest point to end coord {end_coord} is node {target_idx} at {tuple(nearest_end)} (dist: {end_dist:.2f} px)")
    else:
        target_idx = len(height_points) - 1

    print(f"Finding A* shortest path from node {source_idx} to node {target_idx}...")
    path_3d = astar(graph, source_idx, target_idx, height_points, dx=dx, dy=dy)

    if len(path_3d) > 0:
        print(f"Path successfully found containing {len(path_3d)} nodes.")
        if SMOOTH_PATH:
            print(f"Smoothing path with lam={SMOOTH_PATH_LAMBDA}")
            path_3d = smooth_path(path_3d, terrain, lam=SMOOTH_PATH_LAMBDA)
    else:
        print("Could not find a path between source and target.")

    # 7. Visualization
    print("Displaying visualizations...")

    # Plot 3D Point Cloud and Path using PyVista (GPU, interactive)
    plot_3d_pointcloud_pyvista(height_points, path_3d=path_3d, dx=dx, dy=dy)
    
    # Plot complete warped 3D terrain surface and Path using PyVista (GPU, interactive)
    plot_terrain_surface_pyvista(terrain, dx=dx, dy=dy, path_3d=path_3d)

    print("Showing plots. Close windows to finish.")
    plt.show()

if __name__ == '__main__':
    main()
