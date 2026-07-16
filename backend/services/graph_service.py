from src.graph import make_graph
from src.sampling import find_nearest_point_index
from src.config import MAIN_SLOPE_PENALTY_ALPHA, APPLY_WATER_BODY_MASK

class GraphManager:
    """
    Builds and manages the NetworKit routing graph.
    Wraps the functions from src.graph.
    """
    def __init__(self):
        self.nk_graph = None
        self.height_points = None
        self.alpha = MAIN_SLOPE_PENALTY_ALPHA

    def build_from_mesh(self, height_points, edges, terrain_manager):
        """
        Builds the NetworKit graph from mesh edges using src.graph.make_graph.
        """
        self.height_points = height_points
        
        print(f"Building NetworKit Graph (slope penalty alpha = {self.alpha})...")
        
        wbm_mask = terrain_manager.wbm_mask if APPLY_WATER_BODY_MASK else None
        water_elevation = terrain_manager.water_elevation if APPLY_WATER_BODY_MASK else None

        self.nk_graph = make_graph(
            edges, 
            height_points, 
            dx=terrain_manager.dx, 
            dy=terrain_manager.dy, 
            alpha=self.alpha,
            wbm_mask=wbm_mask,
            terrain=terrain_manager.matrix,
            water_elevation=water_elevation
        )

    def get_nearest_node(self, coord_x, coord_y):
        """
        Finds the index of the node closest to the given (x, y) pixel coordinates.
        Uses find_nearest_point_index from src.sampling.
        """
        if self.height_points is None or len(self.height_points) == 0:
            raise ValueError("Graph is not built or empty.")
            
        return find_nearest_point_index(self.height_points[:, :2], (coord_x, coord_y))
