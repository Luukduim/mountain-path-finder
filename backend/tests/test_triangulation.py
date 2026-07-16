import numpy as np
from scipy.spatial import Delaunay
from src.triangulation import get_edges, filter_border_edges


def test_get_edges():
    # 4 points forming a square with a diagonal
    points = np.array([
        [0.0, 0.0],
        [10.0, 0.0],
        [10.0, 10.0],
        [0.0, 10.0]
    ])
    tri = Delaunay(points)
    edges = get_edges(tri)
    
    # All edges should be tuples (u, v) with u < v
    for u, v in edges:
        assert u < v, f"Edge ({u}, {v}) must satisfy u < v"
    
    # For a triangulated quad, there are 5 unique edges
    assert len(edges) == 5


def test_filter_border_edges():
    width, height = 100, 100
    points = np.array([
        [0, 0],       # 0: corner border
        [0, 50],      # 1: left border
        [50, 50],     # 2: interior land point
        [50, 99]      # 3: top border
    ])
    edges = {
        (0, 1),       # both endpoints on border -> should be filtered out
        (1, 2),       # one endpoint interior -> keep
        (2, 3),       # one endpoint interior -> keep
        (0, 3)        # both endpoints on border -> should be filtered out
    }
    
    filtered = filter_border_edges(edges, points, width, height)
    assert filtered == {(1, 2), (2, 3)}, f"Expected {{(1, 2), (2, 3)}}, got {filtered}"
