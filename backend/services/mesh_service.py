from scipy.spatial import Delaunay
from src.quadtree import decompose_terrain_quadtree
from src.sampling import (
    sample_poisson_disk_points_numba,
    round_and_clamp_points,
    filter_water_points,
    build_height_point_cloud,
    inject_exact_endpoints
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
        self.vis_height_points = None
        self.edges = None
        self.simplices = None
        self.source_idx = None
        self.target_idx = None

    def build(self, terrain_manager, start_pixel=None, end_pixel=None, progress_callback=None):
        """
        Builds the mesh from a TerrainManager instance.
        """
        if terrain_manager.matrix is None:
            raise ValueError("Terrain matrix is not loaded.")

        if progress_callback:
            progress_callback("Building quadtree...")
        print("Decomposing terrain using Quadtree...")
        regions, _ = decompose_terrain_quadtree(
            terrain_manager.matrix,
            INITIAL_QUADTREE_MAX_DEPTH,
            INITIAL_QUADTREE_MIN_VARIANCE,
            VARIANCE_PERCENTILE_THRESHOLD,
            FINAL_QUADTREE_MAX_DEPTH
        )
        print(f"Quadtree generated {len(regions)} leaf regions.")

        if progress_callback:
            progress_callback("Sampling points...")
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
            
        if start_pixel is not None or end_pixel is not None:
            print("Injecting exact start and end points into point cloud...")
            self.points, injected_indices = inject_exact_endpoints(
                self.points, [start_pixel, end_pixel], min_dist=1.5
            )
            if start_pixel is not None and len(injected_indices) > 0 and injected_indices[0] is not None:
                self.source_idx = injected_indices[0]
            if end_pixel is not None and len(injected_indices) > 1 and injected_indices[1] is not None:
                self.target_idx = injected_indices[1]
            
        self.height_points = build_height_point_cloud(self.points, terrain_manager.matrix)
        print(f"Sampled {len(self.height_points)} 3D points.")

        if progress_callback:
            progress_callback("Triangulating mesh...")
        print("Calculating Delaunay Triangulation and extracting edges...")
        triangulation = Delaunay(self.points)
        raw_edges = get_edges(triangulation)
        self.edges = filter_border_edges(raw_edges, self.points, terrain_manager.width, terrain_manager.height)
        
        # Build unfiltered visualization point cloud for post-triangulation masking (Method 1)
        vis_points = round_and_clamp_points(raw_points, terrain_manager.width, terrain_manager.height)
        if start_pixel is not None or end_pixel is not None:
            vis_points, _ = inject_exact_endpoints(vis_points, [start_pixel, end_pixel], min_dist=1.5)
        self.vis_height_points = build_height_point_cloud(vis_points, terrain_manager.matrix)
        
        vis_triangulation = Delaunay(vis_points)
        raw_simplices = vis_triangulation.simplices.tolist()
        
        valid_simplices = []
        wbm = terrain_manager.wbm_mask if APPLY_WATER_BODY_MASK else None
        water_elev = terrain_manager.water_elevation
        
        for simplex in raw_simplices:
            is_water_triangle = False
            for idx in simplex:
                x_p, y_p = vis_points[idx]
                iy, ix = int(y_p), int(x_p)
                iy = max(0, min(terrain_manager.height - 1, iy))
                ix = max(0, min(terrain_manager.width - 1, ix))
                z_val = self.vis_height_points[idx, 2]
                if (water_elev is not None and z_val == water_elev) or z_val <= 0.0 or (wbm is not None and wbm[iy, ix] == 1):
                    is_water_triangle = True
                    break
            if not is_water_triangle:
                valid_simplices.append(simplex)
                
        self.simplices = valid_simplices
        print(f"Extracted {len(self.edges)} unique edges and {len(self.simplices)} valid visualization triangles.")
        
        return self.height_points, self.edges
