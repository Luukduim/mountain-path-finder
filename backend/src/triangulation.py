import numpy as np


def get_edges(triangulation):
    """Vectorized: Extract unique undirected edges (u, v) where u < v from Delaunay triangulation."""
    simplices = triangulation.simplices
    e1 = np.column_stack((simplices[:, 0], simplices[:, 1]))
    e2 = np.column_stack((simplices[:, 1], simplices[:, 2]))
    e3 = np.column_stack((simplices[:, 2], simplices[:, 0]))
    
    all_edges = np.vstack((e1, e2, e3))
    all_edges.sort(axis=1)  # Ensure u < v
    unique_edges = np.unique(all_edges, axis=0)
    return {tuple(edge) for edge in unique_edges}


def filter_border_edges(edges, points, width, height):
    """Vectorized: Remove edges where BOTH endpoints lie on the outer boundaries of the map."""
    x, y = points[:, 0], points[:, 1]
    on_border = (x <= 0) | (x >= width - 1) | (y <= 0) | (y >= height - 1)
    
    # Filter out edges where both end nodes are flagged as being on the border
    return {(u, v) for u, v in edges if not (on_border[u] and on_border[v])}
