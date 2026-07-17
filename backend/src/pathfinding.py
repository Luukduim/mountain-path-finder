import numpy as np
import networkit as nk
from scipy.interpolate import make_smoothing_spline
from src.config import (
    DEFAULT_METRIC_RESOLUTION,
    NETWORKIT_INFINITY_THRESHOLD,
    WATER_BODY_ELEVATION
)


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


def smooth_path(path_3d, terrain, lam=1.0, water_elevation=WATER_BODY_ELEVATION):
    """
    Creates a smooth path between the source and target points by applying spline smoothing.
    Prevents any smoothed coordinates from landing on water pixels by reverting water-crossing points
    to their original land node coordinates.
    """
    if len(path_3d) < 5:
        return path_3d.copy()

    # Collect t values (distance along the path) for each point
    t_values = [0.0]
    for index in range(1, len(path_3d)):
        dist = np.linalg.norm(path_3d[index, :2] - path_3d[index - 1, :2])
        t_values.append(t_values[-1] + dist)

    # Make splines
    spline_x = make_smoothing_spline(t_values, path_3d[:, 0], lam=lam)
    spline_y = make_smoothing_spline(t_values, path_3d[:, 1], lam=lam)

    # Evaluate splines along t_values
    x_coords = spline_x(t_values)
    y_coords = spline_y(t_values)

    # Strictly anchor the start and end of the smoothed path to the exact start and end coordinates
    x_coords[0], y_coords[0] = path_3d[0, 0], path_3d[0, 1]
    x_coords[-1], y_coords[-1] = path_3d[-1, 0], path_3d[-1, 1]

    h, w = terrain.shape
    x_coords = np.clip(x_coords, 0, w - 1)
    y_coords = np.clip(y_coords, 0, h - 1)

    ix = np.round(x_coords).astype(int)
    iy = np.round(y_coords).astype(int)

    # Check if any smoothed point lands on a water pixel
    if water_elevation is not None:
        is_water = (terrain[iy, ix] == water_elevation) | (terrain[iy, ix] <= 0.0)
    else:
        is_water = terrain[iy, ix] <= 0.0

    # Revert any smoothed point that would land on water back to its original valid land coordinate
    x_coords[is_water] = path_3d[is_water, 0]
    y_coords[is_water] = path_3d[is_water, 1]

    ix = np.round(x_coords).astype(int)
    iy = np.round(y_coords).astype(int)

    smoothed_path_z = terrain[iy, ix]
    return np.column_stack((x_coords, y_coords, smoothed_path_z))
