import numpy as np
import networkit as nk
from src.config import (
    DEFAULT_METRIC_RESOLUTION,
    DEFAULT_SLOPE_PENALTY_ALPHA,
    PENALTY_BASE_SCALE,
    NETWORKIT_INFINITY_THRESHOLD,
    WATER_CROSSING_PENALTY
)
from scipy.interpolate import make_smoothing_spline

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


def get_heuristic(height_points, target_idx, dx=DEFAULT_METRIC_RESOLUTION, dy=DEFAULT_METRIC_RESOLUTION):
    """Vectorized Euclidean 3D distance heuristic from all nodes to the target in meters."""
    scaled_points = height_points.copy()
    scaled_points[:, 0] *= dx
    scaled_points[:, 1] *= dy
    
    target = scaled_points[target_idx]
    diff = scaled_points - target
    return np.linalg.norm(diff, axis=1).tolist()


def astar(graph, source_idx, target_idx, nodes, dx=DEFAULT_METRIC_RESOLUTION, dy=DEFAULT_METRIC_RESOLUTION):
    """
    Runs A* shortest path search on the NetworKit graph.
    Uses Euclidean 3D distance as an admissible heuristic.
    """
    distanceHeu = get_heuristic(nodes, target_idx, dx=dx, dy=dy)
    
    # Run the NetworKit A* solver
    astar_algo = nk.distance.AStar(graph, distanceHeu, source_idx, target_idx, True)
    astar_algo.run()
    
    # NetworKit returns a distance near infinity if no path is found
    if astar_algo.getDistance() > NETWORKIT_INFINITY_THRESHOLD:
        return np.empty((0, 3))
        
    # Reconstruct route coordinates
    path_nodes = [source_idx] + astar_algo.getPath() + [target_idx]
    return nodes[path_nodes]


def smooth_path(path_3d, terrain, lam=1.0):
    """
     Creates a smooth path between the source and target points by applying spline smoothing.
    
    The path is in 3d space, but because the path goes over the terrain (which is 2D), we can treat it as a 2D problem in the xy plane, and 
    only use the z values from the terrain.

    Our path can not be fitted by functions of the form f(x) = y since there might be multiple y values for a single x value.
    
    Therefore we parameterize the path with a variable t, representing the path length to account for the geometry of the path.
    """

    # Collect t values (distance along the path) for each point
    t_values = [0]
    for index in range(1, len(path_3d)):
        # Calculate the 2D distance between the current point and the previous point
        t_values.append(t_values[-1] + np.linalg.norm(np.array([path_3d[index][0], path_3d[index][1]]) - np.array([path_3d[index-1][0], path_3d[index-1][1]])))

    # Make splines
    spline_x = make_smoothing_spline(t_values, path_3d[:, 0], lam=lam)
    spline_y = make_smoothing_spline(t_values, path_3d[:, 1], lam=lam)

    # Input our t_values into the splines to get the smoothed path
    x_coords = spline_x(t_values)
    y_coords = spline_y(t_values)
    
    # Get z values from terrain
    smoothed_path_z = terrain[y_coords.astype(int), x_coords.astype(int)]
    
    # create smoothed path
    smoothed_path = np.column_stack((x_coords, y_coords, smoothed_path_z))
    
    return smoothed_path

    




    
    
    