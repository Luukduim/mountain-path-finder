import numpy as np
from .config import (
    DEFAULT_QUADTREE_MAX_DEPTH,
    DEFAULT_QUADTREE_MIN_VARIANCE,
    MIN_SUBREGION_SIZE
)


def quadtree_regions(matrix, x=0, y=0, h=None, w=None, depth=0, max_depth=DEFAULT_QUADTREE_MAX_DEPTH, min_variance=DEFAULT_QUADTREE_MIN_VARIANCE):
    """
    Recursively partitions the terrain matrix into quadtree leaf regions.
    Splits a region into 4 quadrants if its height variance exceeds the threshold.
    
    Parameters:
        matrix (np.ndarray): 2D terrain elevation array.
        x, y (int): Pixel coordinates of the top-left corner of the sub-region.
        h, w (int): Dimensions of the sub-region in pixels.
        depth (int): Current recursion depth.
        max_depth (int): Maximum depth where recursion is forced to stop.
        min_variance (float): Elevation variance below which splitting stops.
        
    Returns:
        list of dict: Bounding boxes and stats of all leaf regions.
    """
    if h is None or w is None:
        h, w = matrix.shape

    # Extract sub-matrix and calculate stats
    sub = matrix[y:y+h, x:x+w]
    var = float(np.var(sub)) if sub.size > 0 else 0.0
    mean = float(np.mean(sub)) if sub.size > 0 else 0.0

    # Stopping criteria: reach max depth, variance is low, or size is 1x1 pixel
    if depth >= max_depth or var < min_variance or h <= MIN_SUBREGION_SIZE or w <= MIN_SUBREGION_SIZE:
        return [{
            'x': x, 'y': y, 'w': w, 'h': h,
            'depth': depth, 'var': var, 'mean': mean
        }]

    # Handle odd quadrant dimensions gracefully using floor/ceil splits
    h1, w1 = h // 2, w // 2
    h2, w2 = h - h1, w - w1

    # Recurse for Top-Left, Top-Right, Bottom-Left, and Bottom-Right quadrants
    regions = []
    regions.extend(quadtree_regions(matrix, x, y, h1, w1, depth+1, max_depth, min_variance))
    regions.extend(quadtree_regions(matrix, x + w1, y, h1, w2, depth+1, max_depth, min_variance))
    regions.extend(quadtree_regions(matrix, x, y + h1, h2, w1, depth+1, max_depth, min_variance))
    regions.extend(quadtree_regions(matrix, x + w1, y + h1, h2, w2, depth+1, max_depth, min_variance))

    return regions


def calculate_region_stats(matrix, regions):
    """Calculates variance and mean for an arbitrary list of bounding boxes."""
    stats = []
    for reg in regions:
        x, y, w, h = reg['x'], reg['y'], reg['w'], reg['h']
        sub = matrix[y:y+h, x:x+w]
        var = float(np.var(sub)) if sub.size > 0 else 0.0
        mean = float(np.mean(sub)) if sub.size > 0 else 0.0
        stats.append({'x': x, 'y': y, 'w': w, 'h': h, 'var': var, 'mean': mean})
    return stats


def decompose_terrain_quadtree(terrain, initial_max_depth, initial_min_variance, variance_percentile, final_max_depth):
    """
    Performs two-pass quadtree decomposition:
    1. Computes initial regions and calculates 95th (or configured) percentile variance threshold.
    2. Runs final quadtree decomposition with that threshold.
    Returns (regions, min_variance).
    """
    initial_regions = quadtree_regions(terrain, max_depth=initial_max_depth, min_variance=initial_min_variance)
    stats = calculate_region_stats(terrain, initial_regions)
    stats_variances = [s['var'] for s in stats]

    min_variance = np.percentile(stats_variances, variance_percentile) if len(stats_variances) > 0 else 0.0
    regions = quadtree_regions(terrain, max_depth=final_max_depth, min_variance=min_variance)
    return regions, min_variance
