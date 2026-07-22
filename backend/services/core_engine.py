from .terrain_service import TerrainManager
from .mesh_service import MeshBuilder
from .graph_service import GraphManager
from .pathfinding_service import PathfindingEngine
from src.config import SMOOTH_PATH_LAMBDA

class MountainPathFinder:
    """
    Master engine orchestrating the terrain, mesh, graph, and pathfinding services.
    Designed to be instantiated and used by FastAPI endpoints, preserving the functional src logic.
    """
    def __init__(self):
        self.terrain = TerrainManager()
        self.mesh = MeshBuilder()
        self.graph = GraphManager()
        self.engine = PathfindingEngine()

    def load_terrain_from_stac(self, bbox, apply_wbm=True, progress_callback=None):
        """Loads terrain for a given bounding box from STAC."""
        self.terrain.load_from_stac(bbox, apply_wbm=apply_wbm, progress_callback=progress_callback)

    def load_terrain_from_file(self, filepath):
        """Loads terrain from a local GeoTIFF file."""
        self.terrain.load_from_file(filepath)

    def build_graph(self, start_pixel=None, end_pixel=None, progress_callback=None):
        """Generates the mesh and graph from the currently loaded terrain."""
        if self.terrain.matrix is None:
            raise ValueError("Terrain must be loaded before building the graph.")
            
        self.mesh.build(self.terrain, start_pixel=start_pixel, end_pixel=end_pixel, progress_callback=progress_callback)
        self.graph.build_from_mesh(self.mesh.height_points, self.mesh.edges, self.terrain, progress_callback=progress_callback)

    def find_path(self, start_pixel, end_pixel, smooth=True, lam=SMOOTH_PATH_LAMBDA, progress_callback=None):
        """
        Finds a path between two pixel coordinates (x, y).
        
        Returns:
            tuple: (path_3d, source_idx, target_idx)
        """
        if self.graph.nk_graph is None:
            raise ValueError("Graph must be built before finding a path.")
            
        source_idx = self.mesh.source_idx if self.mesh.source_idx is not None else self.graph.get_nearest_node(start_pixel[0], start_pixel[1])
        target_idx = self.mesh.target_idx if self.mesh.target_idx is not None else self.graph.get_nearest_node(end_pixel[0], end_pixel[1])
        
        path_3d = self.engine.find_path(self.graph, self.terrain, source_idx, target_idx, progress_callback=progress_callback)
        
        if len(path_3d) > 0 and smooth:
            path_3d = self.engine.smooth_path(path_3d, self.terrain, lam=lam, progress_callback=progress_callback)
            
        return path_3d, source_idx, target_idx
