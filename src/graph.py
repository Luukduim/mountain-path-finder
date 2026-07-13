import numpy as np
import networkit as nk
from src.config import (
    DEFAULT_METRIC_RESOLUTION,
    DEFAULT_SLOPE_PENALTY_ALPHA,
    WATER_CROSSING_PENALTY
)


def slope_penalty_weight(height_points, u, v, dx=DEFAULT_METRIC_RESOLUTION, dy=DEFAULT_METRIC_RESOLUTION, alpha=DEFAULT_SLOPE_PENALTY_ALPHA):
    """
    Calculates the 3D travel distance between two points, penalizing steep inclines.
    Uses the formula: cost = 3D_dist * (1 + alpha * slope^2)
    
    Parameters:
        height_points (np.ndarray): Array of shape (N, 3) representing [x, y, z] points.
        u, v (int): Node indices.
        dx, dy (float): Spatial resolution in meters per pixel.
        alpha (float): Penalty coefficient scaling slope difficulty.
        
    Returns:
        float: Calculated weighted edge cost.
    """
    p1 = height_points[u]
    p2 = height_points[v]
    
    # Horizontal ground distance in meters
    dist_2d = np.sqrt(((p1[0] - p2[0]) * dx)**2 + ((p1[1] - p2[1]) * dy)**2)
    
    # Elevation difference in meters
    dz = abs(p1[2] - p2[2])
    
    # Real 3D geometric distance in meters
    dist_3d = np.sqrt(dist_2d**2 + dz**2)
    
    # Slope (rise/run)
    slope = (dz / dist_2d) if dist_2d > 0 else 0.0
    
    # Apply slope penalty to 3D distance
    return dist_3d * (1 + alpha * (slope ** 2))


def check_water_crossing(p1, p2, wbm_mask=None, terrain=None, water_elevation=None):
    """Check if the line segment between p1 and p2 in pixel space crosses any water pixel."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = np.sqrt(dx**2 + dy**2)
    if dist < 1e-5:
        return False
        
    num_steps = int(np.ceil(dist)) + 1
    t = np.linspace(0, 1, num_steps)
    
    xs = np.round(p1[0] + t * dx).astype(int)
    ys = np.round(p1[1] + t * dy).astype(int)
    
    if terrain is not None:
        h, w = terrain.shape
        xs = np.clip(xs, 0, w - 1)
        ys = np.clip(ys, 0, h - 1)
        if water_elevation is not None:
            if np.any(terrain[ys, xs] == water_elevation):
                return True
                
    if wbm_mask is not None:
        h, w = wbm_mask.shape
        xs = np.clip(xs, 0, w - 1)
        ys = np.clip(ys, 0, h - 1)
        if np.any(wbm_mask[ys, xs] == 1):
            return True
            
    return False


def make_graph(edges, height_points, dx=DEFAULT_METRIC_RESOLUTION, dy=DEFAULT_METRIC_RESOLUTION, 
               alpha=DEFAULT_SLOPE_PENALTY_ALPHA, wbm_mask=None, terrain=None, water_elevation=None,
               water_penalty=WATER_CROSSING_PENALTY):
    """Builds a weighted NetworKit graph representing the mesh connections."""
    graph = nk.Graph(len(height_points), weighted=True)
    for u, v in edges:
        weight = slope_penalty_weight(height_points, u, v, dx=dx, dy=dy, alpha=alpha)
        
        # Apply water crossing penalty if the edge intersects a water body (proportional to 3D distance in meters)
        if check_water_crossing(height_points[u], height_points[v], wbm_mask, terrain, water_elevation):
            p1 = height_points[u]
            p2 = height_points[v]
            dist_2d = np.sqrt(((p1[0] - p2[0]) * dx)**2 + ((p1[1] - p2[1]) * dy)**2)
            dz = abs(p1[2] - p2[2])
            dist_3d = np.sqrt(dist_2d**2 + dz**2)
            weight += water_penalty * dist_3d**2
            
        graph.addEdge(u, v, weight)        
    return graph
