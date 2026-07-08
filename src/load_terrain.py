import rasterio
import numpy as np
from src.config import DEFAULT_RASTER_BAND

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
            # Read first band and cast to float for stability in variance / slope math
            terrain_matrix = src.read(DEFAULT_RASTER_BAND).astype(np.float32)
        print(f"Terrain successfully loaded. Matrix shape: {terrain_matrix.shape}")
        return terrain_matrix
    except Exception as e:
        raise RuntimeError(f"Failed to load terrain file from {file_path}: {e}")
