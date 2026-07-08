import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from .config import (
    DEFAULT_QUADTREE_MAX_DEPTH,
    DEFAULT_QUADTREE_MIN_VARIANCE,
    INITIAL_QUADTREE_MAX_DEPTH,
    INITIAL_QUADTREE_MIN_VARIANCE,
    VARIANCE_PERCENTILE_THRESHOLD,
    MIN_SUBREGION_SIZE,
    DEFAULT_FIGSIZE,
    LINEWIDTH_QUADTREE_BORDER,
    PROC_TERRAIN_SIZE,
    PROC_TERRAIN_NUM_HILLS,
    PROC_TERRAIN_ROUGHNESS,
    PROC_TERRAIN_SEED
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


def draw_quadtree(matrix, regions, max_depth=DEFAULT_QUADTREE_MAX_DEPTH, savepath=None, show=False, ax=None):
    """Draws the terrain heatmap and overlays red quadtree leaf boundaries."""
    if ax is None:
        fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
        created_fig = True
    else:
        fig = ax.get_figure()
        created_fig = False

    ax.imshow(matrix, cmap='viridis', interpolation='nearest', origin='lower', aspect='auto')
    ax.set_box_aspect(1)
    ax.grid(False)
    ax.set_xlim(0, matrix.shape[1])
    ax.set_ylim(0, matrix.shape[0])

    # Draw a bounding rectangle for each leaf region
    for reg in regions:
        x, y, w, h = reg['x'], reg['y'], reg['w'], reg['h']
        rect = patches.Rectangle(
            (x, y), w, h,
            linewidth=LINEWIDTH_QUADTREE_BORDER,
            edgecolor='red',
            facecolor='none',
        )
        ax.add_patch(rect)

    ax.set_title('Quadtree Region Overlay')
    if savepath and created_fig:
        fig.savefig(savepath, bbox_inches='tight')
    if show:
        plt.show()
    if created_fig:
        plt.close(fig)


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

if __name__ == "__main__":
    from src.generate_terrain import generate_terrain
    print("Testing build_quadtree standalone...")
    
    # Generate a procedural mock terrain
    terrain = generate_terrain(size=PROC_TERRAIN_SIZE, num_hills=PROC_TERRAIN_NUM_HILLS, roughness=PROC_TERRAIN_ROUGHNESS, seed=PROC_TERRAIN_SEED)

    # 1. Run an initial pass with min_variance=0 to get variances of all regions
    initial_regions = quadtree_regions(terrain, max_depth=INITIAL_QUADTREE_MAX_DEPTH, min_variance=INITIAL_QUADTREE_MIN_VARIANCE)
    stats = calculate_region_stats(terrain, initial_regions)
    
    # 2. Filter by the 95th percentile of variance to focus density in high-roughness areas
    stats_variances = [s['var'] for s in stats]
    min_variance = np.percentile(stats_variances, VARIANCE_PERCENTILE_THRESHOLD) if len(stats_variances) > 0 else 0
    print(f"95th percentile variance threshold: {min_variance:.3f}")

    # 3. Regenerate quadtree using the filtered variance threshold
    regions = quadtree_regions(terrain, max_depth=INITIAL_QUADTREE_MAX_DEPTH, min_variance=min_variance)
    print(f"Generated {len(regions)} regions.")

    # Show the quadtree overlay plot
    draw_quadtree(terrain, regions, max_depth=INITIAL_QUADTREE_MAX_DEPTH, show=True)