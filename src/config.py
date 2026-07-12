import os
import numpy as np

# =====================================================================
# 1. Path & Dataset Config
# =====================================================================
# Dynamically locate the project root director
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)

DEFAULT_TERRAIN_PATH = os.path.join(PROJECT_ROOT, "terrain", "norway_fjord.tif")
DEFAULT_RASTER_BAND = 1

# =====================================================================
# 2. GIS & Spatial Resolution Config
# =====================================================================
DEFAULT_METRIC_RESOLUTION = 1.0
GEOGRAPHIC_DEGREE_THRESHOLD = 0.1
MAX_BBOX_AREA_KM2 = 10000.0  # Limit the size of STAC DEM query to 500 square kilometers
DEFAULT_BBOX_CANVAS_SIZE = 1000

# Water Body Mask Config
APPLY_WATER_BODY_MASK = True
WATER_BODY_ELEVATION = -1

# =====================================================================
# 3. Quadtree Decomposition Config
# =====================================================================
DEFAULT_QUADTREE_MAX_DEPTH = 6
DEFAULT_QUADTREE_MIN_VARIANCE = 5.0
INITIAL_QUADTREE_MAX_DEPTH = 6
INITIAL_QUADTREE_MIN_VARIANCE = 0.0
FINAL_QUADTREE_MAX_DEPTH = 7
VARIANCE_PERCENTILE_THRESHOLD = 95
MIN_SUBREGION_SIZE = 1

# =====================================================================
# 4. Poisson Disk Sampling Config
# =====================================================================
DEFAULT_MIN_DEPTH = 3
DEFAULT_MAX_DEPTH = 6
DEFAULT_MAX_RADIUS = 8.0
DEFAULT_MIN_RADIUS = 4.0
MAIN_MAX_RADIUS = 5.0
MAIN_MIN_RADIUS = 2.0
POISSON_BASE_SEED = 42

# Bridson algorithm specific constants
BRIDSON_K_CANDIDATES = 30
CELL_SIZE_FACTOR = 1.4142135623730951  # np.sqrt(2)
PACKING_DENSITY_ESTIMATE_FACTOR = 0.25
BRIDSON_MAX_PTS_BUFFER = 100
GRID_NEIGHBOR_RADIUS = 2
SPATIAL_DIMENSIONS = 2

# Seed hashing factors
POISSON_SEED_Y_MULTIPLIER = 100000
POISSON_SEED_MODULO_32BIT = 4294967296       # 2**32
POISSON_SEED_MODULO_31BIT = 2147483647       # 2**31 - 1

# =====================================================================
# 5. Graph and A* Config
# =====================================================================
DEFAULT_SLOPE_PENALTY_ALPHA = 50.0
MAIN_SLOPE_PENALTY_ALPHA = 5000
NETWORKIT_INFINITY_THRESHOLD = 1e300
PENALTY_BASE_SCALE = 1.0
WATER_CROSSING_PENALTY = 250.0

# Path smoothing parameters
SMOOTH_PATH = True
SMOOTH_PATH_LAMBDA = 1000  # Larger values = smoother/straighter, smaller = closer to raw path

# =====================================================================
# 6. Interactive Point Selection Config
# =====================================================================
INTERACTIVE_SELECTION_FALLBACK_START = (132, 1222)
INTERACTIVE_SELECTION_FALLBACK_END = (4716, 330)

# =====================================================================
# 7. Procedural Terrain Generation Config
# =====================================================================
PROC_TERRAIN_SIZE = 1000
PROC_TERRAIN_NUM_HILLS = 80
PROC_TERRAIN_ROUGHNESS = 0.5
PROC_TERRAIN_SEED = 42
PROC_TERRAIN_MAX_ELEVATION = 4000.0

PROC_TERRAIN_MIN_HILL_HEIGHT_SCALE = 0.3
PROC_TERRAIN_MAX_HILL_HEIGHT_SCALE = 1.2
PROC_TERRAIN_MIN_HILL_WIDTH_SCALE = 0.02
PROC_TERRAIN_MAX_HILL_WIDTH_SCALE = 0.12
PROC_TERRAIN_GAUSSIAN_DENOMINATOR_FACTOR = 2.0
PROC_TERRAIN_OCTAVES = 6
PROC_TERRAIN_NOISE_SCALE_FACTOR = 0.25
PROC_TERRAIN_OCTAVE_BASE = 2.0

# =====================================================================
# 8. Visualization & Plotting Styles
# =====================================================================
DEFAULT_FIGSIZE = (8, 8)
COLORBAR_SHRINK = 0.8
MARKER_SIZE_SELECTION = 8
LINEWIDTH_QUADTREE_BORDER = 1.2
LINEWIDTH_2D_DELAUNAY = 0.3
ALPHA_2D_DELAUNAY = 0.5
MARKERSIZE_2D_NODES = 0.1
LINEWIDTH_2D_PATH = 2.5

# PyVista 3D plot configs
PYVISTA_Z_FIGHTING_OFFSET = 30.0
PYVISTA_POINT_SIZE = 3.0
PYVISTA_PATH_LINE_WIDTH_CLOUD = 5
PYVISTA_PATH_LINE_WIDTH_SURFACE = 3
SAVED_PLOT_DPI = 200

# Comparison script constants (generate_plots.py)
COMPARISON_PERCENTILE_95 = 95
COMPARISON_PERCENTILE_55 = 55
COMPARISON_MAX_RADIUS = 20.0
COMPARISON_MIN_RADIUS = 5.0
COMPARISON_SLOPE_PENALTY_ALPHA = 500
COMPARISON_FIGSIZE = (12, 6)

# Point distribution plot constants (point_distribution_plot.py)
DIST_PLOT_FIGSIZE = (8, 6)
DIST_PLOT_ALPHA = 0.7
DIST_PLOT_TEST_RADIUS = 0.05
DIST_PLOT_TEST_SAMPLE_SIZE = 1000
