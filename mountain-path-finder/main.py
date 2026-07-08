import sys
from pathlib import Path
# Add parent directory to path so that 'src' is importable
sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Delaunay

# Import pipeline steps from modularized files
from src.load_terrain import load_terrain
from src.generate_terrain import generate_terrain
from src.build_quadtree import quadtree_regions, calculate_region_stats, draw_quadtree
from src.create_points import (
    sample_poisson_disk_points_numba,
    round_and_clamp_points,
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
    SMOOTH_PATH_LAMBDA
)

def main():
    
    # 1. Generate/Load Terrain
    file_path = DEFAULT_TERRAIN_PATH
    terrain = load_terrain(file_path=file_path)
    height, width = terrain.shape
    print(f"Loaded terrain matrix of size: {width}x{height} (width x height)")

    # Load spatial resolution
    dx, dy = DEFAULT_METRIC_RESOLUTION, DEFAULT_METRIC_RESOLUTION
    try:
        import rasterio
        with rasterio.open(file_path) as src:
            res_x, res_y = src.res
            # If the resolution is extremely small (< 0.1), the coordinates are in degrees rather than meters
            R = 6371000
            if res_x < GEOGRAPHIC_DEGREE_THRESHOLD:
                # Find the borders of the tif file (left/right are in longitude, bottom/top are in latitude)
                left, bottom, right, top = src.bounds
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
    except Exception as e:
        print(f"Using default spatial resolution: dx=1.0, dy=1.0 (No TIFF resolution found: {e})")

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
    graph = make_graph(edges, height_points, dx=dx, dy=dy, alpha=slope_penalty_alpha)

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
