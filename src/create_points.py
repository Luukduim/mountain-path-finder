import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import qmc
from scipy.spatial import Delaunay
from numba import njit
from src.config import (
    DEFAULT_MIN_DEPTH,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_RADIUS,
    DEFAULT_MIN_RADIUS,
    POISSON_BASE_SEED,
    BRIDSON_K_CANDIDATES,
    CELL_SIZE_FACTOR,
    PACKING_DENSITY_ESTIMATE_FACTOR,
    BRIDSON_MAX_PTS_BUFFER,
    GRID_NEIGHBOR_RADIUS,
    SPATIAL_DIMENSIONS,
    POISSON_SEED_Y_MULTIPLIER,
    POISSON_SEED_MODULO_32BIT,
    POISSON_SEED_MODULO_31BIT,
    DEFAULT_FIGSIZE,
    LINEWIDTH_2D_DELAUNAY,
    ALPHA_2D_DELAUNAY,
    MARKERSIZE_2D_NODES,
    LINEWIDTH_2D_PATH,
    PYVISTA_Z_FIGHTING_OFFSET,
    PYVISTA_POINT_SIZE,
    PYVISTA_PATH_LINE_WIDTH_CLOUD,
    PYVISTA_PATH_LINE_WIDTH_SURFACE,
    WATER_BODY_ELEVATION
)

# =====================================================================
# 1. Point Sampling (SciPy & Numba Implementations)
# =====================================================================

def sample_poisson_disk_points(regions, min_depth=DEFAULT_MIN_DEPTH, max_depth=DEFAULT_MAX_DEPTH, max_radius=DEFAULT_MAX_RADIUS, min_radius=DEFAULT_MIN_RADIUS):
    """
    Standard SciPy-based Poisson-disk sampling.
    Samples points inside each leaf region of the quadtree using scipy.stats.qmc.
    """
    all_px = []
    all_py = []

    for reg in regions:
        x, y, w, h = reg['x'], reg['y'], reg['w'], reg['h']
        depth = reg['depth']

        # Determine sampling radius based on depth (deeper = smaller radius = denser sampling)
        clamped_depth = max(min_depth, min(max_depth, depth))
        depth_fraction = (clamped_depth - min_depth) / (max_depth - min_depth)
        r_pixel = max_radius - depth_fraction * (max_radius - min_radius)

        # Generate a unique reproducible seed based on the region's coordinates
        base_seed = POISSON_BASE_SEED
        seed = (base_seed + y * POISSON_SEED_Y_MULTIPLIER + x) % POISSON_SEED_MODULO_32BIT

        engine = qmc.PoissonDisk(
            d=SPATIAL_DIMENSIONS, radius=r_pixel, l_bounds=[x, y], u_bounds=[x + w, y + h], seed=seed
        )

        try:
            sample = engine.fill_space()
            if len(sample) > 0:
                all_px.extend(sample[:, 0])
                all_py.extend(sample[:, 1])
        except Exception:
            continue

    if len(all_px) == 0:
        return np.empty((0, 2), dtype=float)

    return np.column_stack((all_px, all_py))


@njit
def bridson_sample(x_start, y_start, w, h, r, k=BRIDSON_K_CANDIDATES, seed_val=POISSON_BASE_SEED):
    """
    Core 2D Poisson-disc sampling using Bridson's O(N) algorithm compiled with Numba.
    Uses a background grid for fast neighborhood distance checks.
    """
    np.random.seed(seed_val)
    
    cell_size = r / CELL_SIZE_FACTOR  # r / sqrt(2) to ensure at most 1 point per cell
    grid_w = int(np.ceil(w / cell_size))
    grid_h = int(np.ceil(h / cell_size))
    
    grid = np.full((grid_w, grid_h), -1, dtype=np.int32)
    max_pts = int(np.ceil((w * h) / (PACKING_DENSITY_ESTIMATE_FACTOR * np.pi * r * r))) + BRIDSON_MAX_PTS_BUFFER
    points = np.zeros((max_pts, 2), dtype=np.float64)
    num_points = 0
    
    # Track points that are still active (can spawn candidates)
    active = np.zeros(max_pts, dtype=np.int32)
    active_size = 0
    
    # Initialize first seed point
    first_x = x_start + np.random.random() * w
    first_y = y_start + np.random.random() * h
    points[0, 0], points[0, 1] = first_x, first_y
    num_points = 1
    
    active[0] = 0
    active_size = 1
    
    g_x = int((first_x - x_start) / cell_size)
    g_y = int((first_y - y_start) / cell_size)
    if 0 <= g_x < grid_w and 0 <= g_y < grid_h:
        grid[g_x, g_y] = 0
        
    while active_size > 0:
        active_idx = np.random.randint(0, active_size)
        pt_idx = active[active_idx]
        pt_x, pt_y = points[pt_idx, 0], points[pt_idx, 1]
        
        found = False
        for _ in range(k):
            # Generate candidate point in an annulus [r, 2r] around current active point
            angle = np.random.random() * 2.0 * np.pi
            radius = r * (1.0 + np.random.random())
            cand_x = pt_x + radius * np.cos(angle)
            cand_y = pt_y + radius * np.sin(angle)
            
            # Check region boundaries
            if x_start <= cand_x <= x_start + w and y_start <= cand_y <= y_start + h:
                cg_x = int((cand_x - x_start) / cell_size)
                cg_y = int((cand_y - y_start) / cell_size)
                
                # Check 5x5 neighborhood cells in background grid
                too_close = False
                min_x, max_x = max(0, cg_x - GRID_NEIGHBOR_RADIUS), min(grid_w - 1, cg_x + GRID_NEIGHBOR_RADIUS)
                min_y, max_y = max(0, cg_y - GRID_NEIGHBOR_RADIUS), min(grid_h - 1, cg_y + GRID_NEIGHBOR_RADIUS)
                
                for nx in range(min_x, max_x + 1):
                    for ny in range(min_y, max_y + 1):
                        neighbor_idx = grid[nx, ny]
                        if neighbor_idx != -1:
                            n_pt = points[neighbor_idx]
                            dist_sq = (cand_x - n_pt[0])**2 + (cand_y - n_pt[1])**2
                            if dist_sq < r * r:
                                too_close = True
                                break
                    if too_close:
                        break
                        
                if not too_close:
                    if num_points < max_pts:
                        points[num_points, 0], points[num_points, 1] = cand_x, cand_y
                        grid[cg_x, cg_y] = num_points
                        active[active_size] = num_points
                        active_size += 1
                        num_points += 1
                        found = True
                        break
                        
        if not found:
            # Remove from active list if all k attempts fail
            active[active_idx] = active[active_size - 1]
            active_size -= 1
            
    return points[:num_points]


@njit
def sample_poisson_numba(x_arr, y_arr, w_arr, h_arr, r_arr, base_seed=POISSON_BASE_SEED):
    """Accumulates Bridson's samples from all quadtree regions sequentially (fast compiled loop)."""
    total_max_pts = 0
    for i in range(len(x_arr)):
        w, h, r = w_arr[i], h_arr[i], r_arr[i]
        max_pts = int(np.ceil((w * h) / (PACKING_DENSITY_ESTIMATE_FACTOR * np.pi * r * r))) + BRIDSON_MAX_PTS_BUFFER
        total_max_pts += max_pts
        
    out_points = np.zeros((total_max_pts, 2), dtype=np.float64)
    out_idx = 0
    
    for i in range(len(x_arr)):
        x, y, w, h, r = x_arr[i], y_arr[i], w_arr[i], h_arr[i], r_arr[i]
        seed_val = (base_seed + int(y) * POISSON_SEED_Y_MULTIPLIER + int(x)) % POISSON_SEED_MODULO_31BIT
        pts = bridson_sample(x, y, w, h, r, BRIDSON_K_CANDIDATES, seed_val)
        
        n_pts = len(pts)
        if out_idx + n_pts <= total_max_pts:
            out_points[out_idx : out_idx + n_pts] = pts
            out_idx += n_pts
            
    return out_points[:out_idx]


def sample_poisson_disk_points_numba(regions, min_depth=DEFAULT_MIN_DEPTH, max_depth=DEFAULT_MAX_DEPTH, max_radius=DEFAULT_MAX_RADIUS, min_radius=DEFAULT_MIN_RADIUS):
    """Numba-accelerated Poisson disk sampler. Complete drop-in replacement for the SciPy version."""
    n_regions = len(regions)
    if n_regions == 0:
        return np.empty((0, 2), dtype=float)
        
    x_arr = np.zeros(n_regions, dtype=np.float64)
    y_arr = np.zeros(n_regions, dtype=np.float64)
    w_arr = np.zeros(n_regions, dtype=np.float64)
    h_arr = np.zeros(n_regions, dtype=np.float64)
    r_arr = np.zeros(n_regions, dtype=np.float64)
    
    for i, reg in enumerate(regions):
        x_arr[i], y_arr[i] = reg['x'], reg['y']
        w_arr[i], h_arr[i] = reg['w'], reg['h']
        
        # Calculate dynamic radius based on tree depth
        depth = reg['depth']
        clamped_depth = max(min_depth, min(max_depth, depth))
        depth_fraction = (clamped_depth - min_depth) / (max_depth - min_depth)
        r_arr[i] = max_radius - depth_fraction * (max_radius - min_radius)
        
    return sample_poisson_numba(x_arr, y_arr, w_arr, h_arr, r_arr)


# =====================================================================
# 2. Geometry & Graph Data Helpers (Optimized Vectorized Operations)
# =====================================================================

def round_and_clamp_points(points, width, height=None):
    """Round coordinates to nearest integers, clamp within image boundaries, and drop duplicates."""
    if points.size == 0:
        return points.reshape((0, 2)).astype(int)

    height = width if height is None else height
    points = np.round(points).astype(int)
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    return np.unique(points, axis=0)


def filter_water_points(points, matrix, wbm_mask=None, water_elevation=None):
    """Filter out points representing water using the mask or elevation value."""
    if points.size == 0:
        return points
    
    if wbm_mask is not None:
        is_water = wbm_mask[points[:, 1], points[:, 0]]
        points = points[is_water != 1]
        
    if water_elevation is not None:
        z = matrix[points[:, 1], points[:, 0]]
        points = points[z != water_elevation]
        
    return points


def build_height_point_cloud(points, matrix):
    """Vectorized: Convert 2D coordinates [x, y] to 3D point cloud [x, y, z] using height values."""
    if points.size == 0:
        return np.empty((0, 3), dtype=float)
    z = matrix[points[:, 1], points[:, 0]]
    return np.column_stack((points, z)).astype(float)


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


def find_nearest_point_index(points, coord):
    """Find index of the point in point cloud closest to given coordinate (x, y)."""
    if len(points) == 0:
        raise ValueError("Cannot find nearest point in an empty array.")
    distances = np.sum((points - np.array(coord)) ** 2, axis=1)
    return np.argmin(distances)


# =====================================================================
# 3. Visualization Utilities (Matplotlib & PyVista)
# =====================================================================

def plot_2d_delaunay(points, path_3d=None):
    """Plot the 2D Delaunay triangulation layout and overlay the path if provided."""
    if points.shape[0] < 3:
        return

    tri = Delaunay(points)
    plt.figure(figsize=(DEFAULT_FIGSIZE[0] * 1.5, DEFAULT_FIGSIZE[1] * 1.5))
    # Emphasize the network: use a slightly thicker steelblue line and fade the background nodes
    plt.triplot(points[:, 0], points[:, 1], tri.simplices, color='steelblue', linewidth=LINEWIDTH_2D_DELAUNAY * 2.5, alpha=0.75)
    plt.plot(points[:, 0], points[:, 1], 'ko', markersize=MARKERSIZE_2D_NODES, alpha=0.15)
    
    if path_3d is not None and len(path_3d) > 0:
        plt.plot(path_3d[:, 0], path_3d[:, 1], 'r-', linewidth=LINEWIDTH_2D_PATH, label='A* Shortest Path')
        plt.legend()
        
    plt.gca().set_xlim(0, points[:, 0].max() + 1)
    plt.gca().set_ylim(0, points[:, 1].max() + 1)
    plt.title('2D Delaunay Triangulation')


def plot_3d_pointcloud_pyvista(height_points, path_3d=None, dx=1.0, dy=1.0, height=None):
    """3D point cloud interactive plot using PyVista (GPU-accelerated)."""
    try:
        import pyvista as pv
    except ImportError:
        print("Error: PyVista is not installed.")
        return

    if height is None and len(height_points) > 0:
        height = int(np.round(height_points[:, 1].max())) + 1

    scaled_points = height_points.copy()
    scaled_points[:, 0] *= dx
    if height is not None:
        scaled_points[:, 1] = (height - 1 - scaled_points[:, 1]) * dy
    else:
        scaled_points[:, 1] *= dy

    point_cloud = pv.PolyData(scaled_points)
    point_cloud["Elevation"] = scaled_points[:, 2]

    plotter = pv.Plotter()
    plotter.add_mesh(
        point_cloud, scalars="Elevation", cmap="terrain", point_size=PYVISTA_POINT_SIZE,
        render_points_as_spheres=True, label="Sampled Points (3D)",
        scalar_bar_args={"fmt": "%.0f", "title": "Elevation (m)"}
    )

    if path_3d is not None and len(path_3d) > 0:
        scaled_path = path_3d.copy()
        scaled_path[:, 0] *= dx
        if height is not None:
            scaled_path[:, 1] = (height - 1 - scaled_path[:, 1]) * dy
        else:
            scaled_path[:, 1] *= dy
        scaled_path[:, 2] += PYVISTA_Z_FIGHTING_OFFSET  # Floating offset to avoid overlay z-fighting

        num_points = len(scaled_path)
        cells = np.hstack(([num_points], np.arange(num_points)))

        path_mesh = pv.PolyData(scaled_path)
        path_mesh.lines = cells
        plotter.add_mesh(
            path_mesh, color="red", line_width=PYVISTA_PATH_LINE_WIDTH_CLOUD, render_lines_as_tubes=True, label="A* Route"
        )

    plotter.add_legend()
    plotter.show_axes()
    plotter.show()


def plot_terrain_surface_pyvista(terrain_matrix, dx=1.0, dy=1.0, path_3d=None):
    """Plot the warped 3D terrain surface mesh using PyVista (GPU-accelerated)."""
    try:
        import pyvista as pv
    except ImportError:
        print("Error: PyVista is not installed.")
        return

    height, width = terrain_matrix.shape
    x = np.arange(width) * dx
    y = np.arange(height) * dy
    x_grid, y_grid = np.meshgrid(x, y)

    # Flip the terrain vertically so that row 0 (North) is at the top of the Y axis
    grid = pv.StructuredGrid(x_grid, y_grid, np.flipud(terrain_matrix))
    grid["Elevation"] = grid.points[:, 2]

    # Filter out water body cells (which are set to WATER_BODY_ELEVATION)
    # to avoid vertical drop-off cliffs at the shorelines.
    try:
        land_grid = grid.threshold(value=WATER_BODY_ELEVATION + 0.5, scalars="Elevation")
    except Exception:
        land_grid = grid

    plotter = pv.Plotter()
    plotter.add_mesh(
        land_grid, scalars="Elevation", cmap="terrain", show_edges=False, label="3D Terrain",
        scalar_bar_args={"fmt": "%.0f", "title": "Elevation (m)"}
    )

    if path_3d is not None and len(path_3d) > 0:
        scaled_path = path_3d.copy()
        scaled_path[:, 0] *= dx
        scaled_path[:, 1] = (height - 1 - scaled_path[:, 1]) * dy
        scaled_path[:, 2] += PYVISTA_Z_FIGHTING_OFFSET  # Floating offset to avoid z-fighting

        num_points = len(scaled_path)
        cells = np.hstack(([num_points], np.arange(num_points)))

        path_mesh = pv.PolyData(scaled_path)
        path_mesh.lines = cells
        plotter.add_mesh(
            path_mesh, color="red", line_width=PYVISTA_PATH_LINE_WIDTH_SURFACE, render_lines_as_tubes=True, label="A* Route"
        )

    plotter.add_legend()
    plotter.show_axes()
    plotter.show()
