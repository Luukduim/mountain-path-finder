import rasterio
import numpy as np
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import array_bounds
from pystac_client import Client
import planetary_computer

from src.config import (
    DEFAULT_RASTER_BAND,
    PROC_TERRAIN_SIZE,
    PROC_TERRAIN_NUM_HILLS,
    PROC_TERRAIN_ROUGHNESS,
    PROC_TERRAIN_SEED,
    PROC_TERRAIN_MAX_ELEVATION,
    PROC_TERRAIN_MIN_HILL_HEIGHT_SCALE,
    PROC_TERRAIN_MAX_HILL_HEIGHT_SCALE,
    PROC_TERRAIN_MIN_HILL_WIDTH_SCALE,
    PROC_TERRAIN_MAX_HILL_WIDTH_SCALE,
    PROC_TERRAIN_GAUSSIAN_DENOMINATOR_FACTOR,
    PROC_TERRAIN_OCTAVES,
    PROC_TERRAIN_NOISE_SCALE_FACTOR,
    PROC_TERRAIN_OCTAVE_BASE,
    GEOGRAPHIC_DEGREE_THRESHOLD
)


def load_terrain(file_path):
    """
    Loads a single-band GeoTIFF heightmap file and returns it as a NumPy float32 matrix.
    
    Parameters:
        file_path (str): Path to the .tif heightmap file.
        
    Returns:
        np.ndarray: 2D array of elevation values.
    """
    try:
        with rasterio.open(file_path) as src:
            terrain_matrix = src.read(DEFAULT_RASTER_BAND).astype(np.float32)
        print(f"Terrain successfully loaded. Matrix shape: {terrain_matrix.shape}")
        return terrain_matrix
    except Exception as e:
        raise RuntimeError(f"Failed to load terrain file from {file_path}: {e}")


def generate_terrain(size=PROC_TERRAIN_SIZE, num_hills=PROC_TERRAIN_NUM_HILLS, roughness=PROC_TERRAIN_ROUGHNESS, seed=PROC_TERRAIN_SEED):
    """
    Generates a procedural terrain heightmap in meters.
    Combines Gaussian hills for macro-topology and fractal layered noise for micro-roughness.
    """
    rng = np.random.RandomState(seed)
    terrain = np.zeros((size, size), dtype=float)

    xs = np.arange(size)
    ys = np.arange(size)
    xx, yy = np.meshgrid(xs, ys)

    for _ in range(num_hills):
        cx = rng.uniform(0, size)
        cy = rng.uniform(0, size)
        height = rng.uniform(size * PROC_TERRAIN_MIN_HILL_HEIGHT_SCALE, size * PROC_TERRAIN_MAX_HILL_HEIGHT_SCALE)
        sigma = rng.uniform(size * PROC_TERRAIN_MIN_HILL_WIDTH_SCALE, size * PROC_TERRAIN_MAX_HILL_WIDTH_SCALE)
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        terrain += height * np.exp(-d2 / (PROC_TERRAIN_GAUSSIAN_DENOMINATOR_FACTOR * sigma ** 2))

    noise = np.zeros_like(terrain)
    octaves = PROC_TERRAIN_OCTAVES
    for octave in range(octaves):
        freq = PROC_TERRAIN_OCTAVE_BASE ** octave
        small_shape = (int(np.ceil(size / freq)) + 1, int(np.ceil(size / freq)) + 1)
        small = rng.normal(scale=1.0, size=small_shape)
        scale = int(np.ceil(size / small.shape[0]))
        up = np.repeat(np.repeat(small, scale, axis=0), scale, axis=1)[:size, :size]
        persistence = roughness ** octave
        noise += up * persistence

    terrain += noise * (size * PROC_TERRAIN_NOISE_SCALE_FACTOR)

    mn, mx = terrain.min(), terrain.max()
    if mx > mn:
        norm = (terrain - mn) / (mx - mn)
    else:
        norm = np.zeros_like(terrain)

    return norm * PROC_TERRAIN_MAX_ELEVATION


def load_dem_from_stac(bbox, apply_wbm=True, water_elevation=-9999.0):
    """
    Queries Microsoft Planetary Computer STAC catalog for DEM tiles covering bbox.
    Optionally loads and applies JRC GSW water body mask.
    Returns (terrain, res_x, res_y, bounds, wbm_aligned).
    """
    catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    search = catalog.search(collections=["cop-dem-glo-30"], bbox=bbox)
    items = list(search.items())
    print(f"Found {len(items)} DEM tiles covering this area.\n")

    if not items:
        raise ValueError("Failed to load terrain. No STAC items found or loading failed.")

    terrain = None
    res_x, res_y = None, None
    bounds = None
    wbm_aligned = None
    out_trans = None

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
                mosaic, out_trans = merge(src_files, bounds=bbox)
                terrain = mosaic[0].astype(np.float32)
                res_x, res_y = src_files[0].res
                bounds = array_bounds(terrain.shape[0], terrain.shape[1], out_trans)
                print(f"Successfully loaded and merged {len(src_files)} tiles covering the selected bounding box.")

                if apply_wbm:
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
                                terrain[wbm_aligned == 1] = water_elevation
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

    terrain[terrain <= 0.0] = water_elevation
    return terrain, res_x, res_y, bounds, wbm_aligned, out_trans


def compute_metric_resolution(res_x, res_y, bounds, default_res=1.0):
    """
    Computes metric pixel resolution (dx, dy) in meters per pixel.
    Converts geographic degrees to meters if needed.
    """
    if res_x is None or res_y is None or bounds is None:
        print(f"Using default spatial resolution: dx={default_res}, dy={default_res} (No TIFF resolution found)")
        return default_res, default_res

    R = 6371000.0
    if res_x < GEOGRAPHIC_DEGREE_THRESHOLD:
        left, bottom, right, top = bounds
        center_lat = (bottom + top) / 2.0
        center_lat_rad = np.radians(center_lat)

        dx = res_x * (np.cos(center_lat_rad) * np.pi * R) / 180.0
        dy = res_y * (np.pi * R) / 180.0
        print("\n" + "=" * 80)
        print("The loaded GeoTIFF uses geographic degrees (e.g. EPSG:4326) instead of meters.")
        print("The code will estimate the metric pixel size at this latitude as:")
        print(f"          dx = {dx:.2f}m, dy = {dy:.2f}m per pixel.")
        print("=" * 80 + "\n")
        return dx, dy

    dx, dy = res_x, res_y
    print(f"Loaded spatial resolution from TIFF: dx={dx:.3f}m, dy={dy:.3f}m per pixel")
    return dx, dy
