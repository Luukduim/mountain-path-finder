import numpy as np
import networkit as nk
from src.pathfinding import get_heuristic, astar, smooth_path


def test_get_heuristic():
    points = np.array([
        [0.0, 0.0, 0.0],
        [3.0, 4.0, 0.0]
    ])
    heu = get_heuristic(points, target_idx=1, dx=1.0, dy=1.0)
    assert len(heu) == 2
    assert np.isclose(heu[1], 0.0)
    assert np.isclose(heu[0], 5.0)  # sqrt(3^2 + 4^2) = 5.0


def test_astar_pathfinding():
    # 3 nodes in a line: 0 -> 1 -> 2
    nodes = np.array([
        [0.0, 0.0, 10.0],
        [5.0, 0.0, 10.0],
        [10.0, 0.0, 10.0]
    ])
    graph = nk.Graph(3, weighted=True)
    graph.addEdge(0, 1, 5.0)
    graph.addEdge(1, 2, 5.0)
    
    path = astar(graph, source_idx=0, target_idx=2, nodes=nodes, dx=1.0, dy=1.0)
    assert len(path) == 3
    assert np.all(path[0] == nodes[0])
    assert np.all(path[-1] == nodes[2])


def test_smooth_path():
    path_3d = np.array([
        [0.0, 0.0, 10.0],
        [2.5, 2.5, 15.0],
        [5.0, 5.0, 20.0],
        [7.5, 7.5, 25.0],
        [10.0, 10.0, 30.0]
    ])
    terrain = np.ones((20, 20)) * 25.0
    
    smoothed = smooth_path(path_3d, terrain, lam=0.5)
    assert smoothed.shape[1] == 3
    assert len(smoothed) == len(path_3d)
    # Check that z coordinates were sampled from the terrain matrix
    assert np.all(smoothed[:, 2] == 25.0)


def test_smooth_path_avoids_water():
    # Original path nodes are strictly on land (y <= 3)
    path_3d = np.array([
        [0.0, 1.0, 10.0],
        [2.0, 3.0, 10.0],
        [5.0, 3.0, 10.0],
        [8.0, 3.0, 10.0],
        [10.0, 1.0, 10.0]
    ])
    terrain = np.ones((20, 20)) * 25.0
    water_val = -9999.0
    # Place a water obstacle at y=4..8
    terrain[4:8, 2:8] = water_val

    smoothed = smooth_path(path_3d, terrain, lam=100.0, water_elevation=water_val)
    # Ensure no coordinate in the smoothed path sampled the water value
    assert not np.any(smoothed[:, 2] == water_val), "Smoothed path should never sample water elevation values"
