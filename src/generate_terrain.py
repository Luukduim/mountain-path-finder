import numpy as np
import matplotlib.pyplot as plt
from src.config import (
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
    DEFAULT_FIGSIZE,
    SAVED_PLOT_DPI
)

def generate_terrain(size=PROC_TERRAIN_SIZE, num_hills=PROC_TERRAIN_NUM_HILLS, roughness=PROC_TERRAIN_ROUGHNESS, seed=PROC_TERRAIN_SEED):
    """
    Generates a procedural terrain heightmap in meters.
    Combines Gaussian hills for macro-topology and fractal layered noise for micro-roughness.
    
    Parameters:
        size (int): Dimension of the output square matrix (size x size).
        num_hills (int): Number of random Gaussian hills to place on the terrain.
        roughness (float): Persistence coefficient for fractal noise layers.
        seed (int): Random seed for reproducibility.
        
    Returns:
        np.ndarray: 2D array of simulated elevation values in meters.
    """
    rng = np.random.RandomState(seed)
    terrain = np.zeros((size, size), dtype=float)

    # 1. Macro-Topology: Generate Gaussian Hills
    xs = np.arange(size)
    ys = np.arange(size)
    xx, yy = np.meshgrid(xs, ys)

    for _ in range(num_hills):
        # Random center coordinate
        cx = rng.uniform(0, size)
        cy = rng.uniform(0, size)
        
        # Scale heights and widths (sigma) relative to terrain size
        height = rng.uniform(size * PROC_TERRAIN_MIN_HILL_HEIGHT_SCALE, size * PROC_TERRAIN_MAX_HILL_HEIGHT_SCALE)
        sigma = rng.uniform(size * PROC_TERRAIN_MIN_HILL_WIDTH_SCALE, size * PROC_TERRAIN_MAX_HILL_WIDTH_SCALE)
        
        # Calculate squared Euclidean distance to center coordinate
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        # Add 2D Gaussian density function
        terrain += height * np.exp(-d2 / (PROC_TERRAIN_GAUSSIAN_DENOMINATOR_FACTOR * sigma ** 2))

    # 2. Micro-Topology: Add Layered Fractal Noise
    noise = np.zeros_like(terrain)
    octaves = PROC_TERRAIN_OCTAVES
    for octave in range(octaves):
        freq = PROC_TERRAIN_OCTAVE_BASE ** octave
        # Create a coarse random grid for this frequency octave
        small_shape = (int(np.ceil(size / freq)) + 1, int(np.ceil(size / freq)) + 1)
        small = rng.normal(scale=1.0, size=small_shape)
        
        # Upscale the coarse grid to fit the main map dimensions
        scale = int(np.ceil(size / small.shape[0]))
        up = np.repeat(np.repeat(small, scale, axis=0), scale, axis=1)[:size, :size]
        
        # Apply persistence factor (amplitude drops as frequency increases)
        persistence = roughness ** octave
        noise += up * persistence

    # Scaled noise overlay
    terrain += noise * (size * PROC_TERRAIN_NOISE_SCALE_FACTOR)

    # 3. Normalization: Map to realistic heights (0m to 4000m elevation)
    mn, mx = terrain.min(), terrain.max()
    if mx > mn:
        norm = (terrain - mn) / (mx - mn)
    else:
        norm = np.zeros_like(terrain)

    return norm * PROC_TERRAIN_MAX_ELEVATION
