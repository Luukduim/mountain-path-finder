import numpy as np
from scipy.stats import qmc
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
    POISSON_SEED_MODULO_31BIT
)


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
    z = matrix[np.round(points[:, 1]).astype(int), np.round(points[:, 0]).astype(int)]
    return np.column_stack((points, z)).astype(float)


def find_nearest_point_index(points, coord):
    """Find index of the point in point cloud closest to given coordinate (x, y)."""
    if len(points) == 0:
        raise ValueError("Cannot find nearest point in an empty array.")
    distances = np.sum((points - np.array(coord)) ** 2, axis=1)
    return np.argmin(distances)


def inject_exact_endpoints(points, endpoints, min_dist=0.1):
    """
    Injects exact start and end coordinates into the 2D point cloud while preventing
    degenerate 'sliver' triangles by removing any existing Poisson points that are too close.
    
    Parameters:
        points (np.ndarray): Array of shape (N, 2) representing 2D coordinates.
        endpoints (list): Sequence of optional coordinate tuples/arrays [(x1, y1), (x2, y2), ...].
        min_dist (float): Minimum Euclidean distance required between an endpoint and existing points.
        
    Returns:
        tuple: (updated_points, injected_indices) where updated_points is the modified point cloud
               and injected_indices is a list of the exact array indices corresponding to each non-None endpoint.
    """
    if len(points) == 0:
        valid_pts = [np.array(pt) for pt in endpoints if pt is not None]
        if not valid_pts:
            return points, [None for _ in endpoints]
        out_pts = np.array(valid_pts, dtype=points.dtype if points.dtype != object else float)
        return out_pts, list(range(len(out_pts)))

    pts = np.copy(points)
    to_remove = set()
    
    for pt in endpoints:
        if pt is None:
            continue
        pt_arr = np.array(pt)
        dists = np.sqrt(np.sum((pts - pt_arr) ** 2, axis=1))
        close_indices = np.where(dists < min_dist)[0]
        for idx in close_indices:
            to_remove.add(idx)
            
    if to_remove:
        pts = np.delete(pts, sorted(list(to_remove)), axis=0)
        
    injected_indices = []
    for pt in endpoints:
        if pt is None:
            injected_indices.append(None)
            continue
        pt_arr = np.array(pt, dtype=pts.dtype)
        pts = np.vstack((pts, pt_arr))
        injected_indices.append(len(pts) - 1)
        
    return pts, injected_indices

