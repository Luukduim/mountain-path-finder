from src.pathfinding import astar, smooth_path
from src.config import SMOOTH_PATH_LAMBDA

class PathfindingEngine:
    """
    Handles routing and path smoothing.
    Wraps the functions from src.pathfinding.
    """
    def find_path(self, graph_manager, terrain_manager, source_idx, target_idx, progress_callback=None):
        """
        Runs A* shortest path search on the NetworKit graph.
        """
        if progress_callback:
            progress_callback("Running A* search...")
        return astar(
            graph_manager.nk_graph, 
            source_idx, 
            target_idx, 
            graph_manager.height_points, 
            dx=terrain_manager.dx, 
            dy=terrain_manager.dy
        )

    def smooth_path(self, path_3d, terrain_manager, lam=SMOOTH_PATH_LAMBDA, progress_callback=None):
        """
        Creates a smooth path between the source and target points.
        """
        if progress_callback:
            progress_callback("Smoothing path...")
        return smooth_path(
            path_3d, 
            terrain_manager.matrix, 
            lam=lam, 
            water_elevation=terrain_manager.water_elevation
        )
