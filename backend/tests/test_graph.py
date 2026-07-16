import numpy as np
import networkit as nk
from src.graph import slope_penalty_weight, check_water_crossing, make_graph


def test_slope_penalty_weight_flat_vs_steep():
    height_points = np.array([
        [0.0, 0.0, 10.0],
        [10.0, 0.0, 10.0], # flat ground: dz = 0
        [10.0, 0.0, 110.0] # steep incline: dz = 100
    ])
    
    cost_flat = slope_penalty_weight(height_points, 0, 1, dx=1.0, dy=1.0, alpha=10.0)
    cost_steep = slope_penalty_weight(height_points, 0, 2, dx=1.0, dy=1.0, alpha=10.0)
    
    # Flat cost = 3D distance = 10.0
    assert np.isclose(cost_flat, 10.0)
    # Steep cost must be strictly greater than Euclidean 3D distance due to quadratic slope penalty
    euclidean_3d = np.sqrt(10.0**2 + 100.0**2)
    assert cost_steep > euclidean_3d


def test_check_water_crossing():
    p1 = np.array([0, 5, 10])
    p2 = np.array([10, 5, 10])
    
    terrain = np.ones((20, 20)) * 50.0
    # Create river column at x=5
    terrain[:, 5] = 0.0
    
    crosses = check_water_crossing(p1, p2, terrain=terrain, water_elevation=0.0)
    assert crosses is True, "Segment from x=0 to x=10 crossing column x=5 at sea level must detect water crossing"
    
    # Check land-only segment
    p3 = np.array([0, 2, 10])
    p4 = np.array([4, 2, 10])
    crosses_land = check_water_crossing(p3, p4, terrain=terrain, water_elevation=0.0)
    assert crosses_land is False


def test_make_graph():
    height_points = np.array([
        [0.0, 0.0, 10.0],
        [10.0, 0.0, 10.0],
        [10.0, 10.0, 10.0]
    ])
    edges = {(0, 1), (1, 2)}
    
    graph = make_graph(edges, height_points, dx=1.0, dy=1.0, alpha=1.0)
    assert isinstance(graph, nk.Graph)
    assert graph.isWeighted()
    assert graph.numberOfNodes() == 3
    assert graph.numberOfEdges() == 2
