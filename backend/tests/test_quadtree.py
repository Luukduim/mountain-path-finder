import numpy as np
from src.quadtree import quadtree_regions, calculate_region_stats, decompose_terrain_quadtree



def test_quadtree_flat_terrain():
    # Constant flat terrain has 0 variance
    matrix = np.ones((64, 64)) * 100.0
    regions = quadtree_regions(matrix, depth=0, max_depth=4, min_variance=1.0)
    
    # Flat terrain should not be split beyond the root region
    assert len(regions) == 1, f"Flat terrain with 0 variance should result in 1 leaf region, got {len(regions)}"
    assert regions[0]['depth'] == 0
    assert regions[0]['x'] == 0 and regions[0]['y'] == 0


def test_quadtree_regions_coverage():
    # Variable synthetic terrain
    h, w = 64, 64
    matrix = np.random.RandomState(42).normal(100, 50, (h, w))
    regions = quadtree_regions(matrix, depth=0, max_depth=3, min_variance=10.0)
    
    total_area = sum(r['w'] * r['h'] for r in regions)
    assert total_area == w * h, f"Sum of leaf region areas ({total_area}) must equal total matrix area ({w * h})"


def test_calculate_region_stats():
    matrix = np.ones((64, 64)) * 10.0
    regions = [
        {'x': 0, 'y': 0, 'w': 32, 'h': 32, 'depth': 1},
        {'x': 32, 'y': 0, 'w': 32, 'h': 32, 'depth': 2},
        {'x': 0, 'y': 32, 'w': 32, 'h': 32, 'depth': 2}
    ]
    stats = calculate_region_stats(matrix, regions)
    assert len(stats) == 3
    assert stats[0]['var'] == 0.0 and stats[0]['mean'] == 10.0


def test_decompose_terrain_quadtree():
    matrix = np.random.RandomState(42).normal(100, 50, (64, 64))
    regions, min_variance = decompose_terrain_quadtree(
        matrix,
        initial_max_depth=3,
        initial_min_variance=0.0,
        variance_percentile=50.0,
        final_max_depth=4
    )
    assert len(regions) > 0
    assert min_variance >= 0.0
