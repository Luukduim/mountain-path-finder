import numpy as np
from src.terrain import compute_metric_resolution


def test_compute_metric_resolution_geographic_degrees():
    res_x = 0.0002777777777777778
    res_y = 0.0002777777777777778
    bounds = (5.0, 60.0, 6.0, 60.0)  # Latitude = 60 degrees

    dx, dy = compute_metric_resolution(res_x, res_y, bounds)
    assert dx > 0 and dy > 0
    # At latitude 60 deg, cos(60 deg) = 0.5, so dx should be half of dy
    assert np.isclose(dx, dy * 0.5, rtol=1e-3)


def test_compute_metric_resolution_projected_meters():
    res_x, res_y = 30.0, 30.0
    bounds = (0, 0, 1000, 1000)

    dx, dy = compute_metric_resolution(res_x, res_y, bounds)
    assert dx == 30.0
    assert dy == 30.0


def test_compute_metric_resolution_none_default():
    dx, dy = compute_metric_resolution(None, None, None, default_res=2.5)
    assert dx == 2.5
    assert dy == 2.5
