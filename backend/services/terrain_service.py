from src.terrain import load_dem_from_stac, load_terrain, compute_metric_resolution
from src.config import WATER_BODY_ELEVATION

class TerrainManager:
    """
    Manages elevation data, including loading from STAC APIs or local files,
    handling spatial resolution, and applying water body masks.
    Acts as a stateful wrapper around src.terrain functions.
    """
    def __init__(self, water_elevation=WATER_BODY_ELEVATION):
        self.matrix = None
        self.res_x = None
        self.res_y = None
        self.bounds = None
        self.wbm_mask = None
        self.dx = 1.0
        self.dy = 1.0
        self.water_elevation = water_elevation

    def load_from_file(self, file_path):
        """Loads a single-band GeoTIFF heightmap file."""
        self.matrix = load_terrain(file_path)
        # Note: The original load_terrain doesn't return res_x/res_y, but we can compute dx/dy if needed
        self.dx, self.dy = compute_metric_resolution(self.res_x, self.res_y, self.bounds)

    def load_from_stac(self, bbox, apply_wbm=True):
        """
        Queries Microsoft Planetary Computer STAC catalog for DEM tiles covering bbox.
        """
        self.matrix, self.res_x, self.res_y, self.bounds, self.wbm_mask = load_dem_from_stac(
            bbox, apply_wbm=apply_wbm, water_elevation=self.water_elevation
        )
        self.dx, self.dy = compute_metric_resolution(self.res_x, self.res_y, self.bounds)

    @property
    def width(self):
        return self.matrix.shape[1] if self.matrix is not None else 0

    @property
    def height(self):
        return self.matrix.shape[0] if self.matrix is not None else 0
