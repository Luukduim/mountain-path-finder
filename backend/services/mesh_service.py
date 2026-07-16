from scipy.spatial import Delaunay
from src.quadtree import decompose_terrain_quadtree
from src.sampling import (
    sample_poisson_disk_points_numba,
    round_and_clamp_points,
    filter_water_points,
    build_height_point_cloud
)
from src.triangulation import get_edges, filter_border_edges
from src.config import (
    INITIAL_QUADTREE_MAX_DEPTH,
    INITIAL_QUADTREE_MIN_VARIANCE,
    VARIANCE_PERCENTILE_THRESHOLD,
    FINAL_QUADTREE_MAX_DEPTH,
    DEFAULT_MIN_DEPTH,
    MAIN_MAX_RADIUS,
    MAIN_MIN_RADIUS,
    APPLY_WATER_BODY_MASK
)

class MeshBuilder:
    """
    Handles decomposing the terrain, sampling points, and triangulating them.
    Wraps the functions from src.quadtree, src.sampling, and src.triangulation.
    """
    def __init__(self):
        self.points = None
        self.height_points = None
        self.edges = None

    def build(self, terrain_manager):
        """
        Builds the mesh from a TerrainManager instance.
        """
        if terrain_manager.matrix is None:
            raise ValueError("Terrain matrix is not loaded.")

        print("Decomposing terrain using Quadtree...")
        regions, _ = decompose_terrain_quadtree(
            terrain_manager.matrix,
            INITIAL_QUADTREE_MAX_DEPTH,
            INITIAL_QUADTREE_MIN_VARIANCE,
            VARIANCE_PERCENTILE_THRESHOLD,
            FINAL_QUADTREE_MAX_DEPTH
        )
        print(f"Quadtree generated {len(regions)} leaf regions.")

        print("Sampling points...")
        raw_points = sample_poisson_disk_points_numba(
            regions,
            min_depth=DEFAULT_MIN_DEPTH,
            max_depth=FINAL_QUADTREE_MAX_DEPTH,
            max_radius=MAIN_MAX_RADIUS,
            min_radius=MAIN_MIN_RADIUS
        )
        print("Points generated successfully.")
        
        self.points = round_and_clamp_points(raw_points, terrain_manager.width, terrain_manager.height)
        
        if APPLY_WATER_BODY_MASK and terrain_manager.wbm_mask is not None:
            self.points = filter_water_points(
                self.points, 
                terrain_manager.matrix, 
                wbm_mask=terrain_manager.wbm_mask, 
                water_elevation=terrain_manager.water_elevation
            )
            
        self.height_points = build_height_point_cloud(self.points, terrain_manager.matrix)
        print(f"Sampled {len(self.height_points)} 3D points.")

        print("Calculating Delaunay Triangulation and extracting edges...")
        triangulation = Delaunay(self.points)
        raw_edges = get_edges(triangulation)
        self.edges = filter_border_edges(raw_edges, self.points, terrain_manager.width, terrain_manager.height)
        print(f"Extracted {len(self.edges)} unique edges.")
        
        return self.height_points, self.edges
