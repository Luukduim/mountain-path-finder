import numpy as np
from src.sampling import (
    round_and_clamp_points,
    filter_water_points,
    build_height_point_cloud,
    find_nearest_point_index
)


def test_round_and_clamp_points():
    points = np.array([
        [-5.3, 10.8],
        [49.9, -1.2],
        [25.4, 25.6]
    ])
    clamped = round_and_clamp_points(points, width=50, height=50)
    
    assert clamped.shape == points.shape
    # np.unique sorts rows lexicographically by x coordinate:
    # row 0: [-5.3, 10.8] -> [0, 11]
    assert clamped[0, 0] == 0 and clamped[0, 1] == 11
    # row 1: [25.4, 25.6] -> [25, 26]
    assert clamped[1, 0] == 25 and clamped[1, 1] == 26
    # row 2: [49.9, -1.2] -> [49, 0]
    assert clamped[2, 0] == 49 and clamped[2, 1] == 0


def test_filter_water_points():
    points = np.array([
        [5, 5],
        [10, 10],
        [15, 15]
    ])
    # Create terrain where [10, 10] is at sea level (0.0) and others are positive
    terrain = np.ones((20, 20)) * 50.0
    terrain[10, 10] = 0.0
    
    land_points = filter_water_points(points, terrain, water_elevation=0.0)
    assert len(land_points) == 2
    assert not np.any(np.all(land_points == [10, 10], axis=1)), "Point at sea level (0.0) should be filtered out as water"


def test_filter_water_points_with_mask():
    points = np.array([
        [2, 2],
        [8, 8]
    ])
    terrain = np.ones((20, 20)) * 100.0
    wbm_mask = np.zeros((20, 20), dtype=np.uint8)
    wbm_mask[8, 8] = 1  # Masked water body
    
    land_points = filter_water_points(points, terrain, wbm_mask=wbm_mask)
    assert len(land_points) == 1
    assert np.all(land_points[0] == [2, 2])


def test_build_height_point_cloud():
    points = np.array([
        [0, 0],
        [1, 2]
    ])
    terrain = np.array([
        [10.0, 20.0, 30.0],
        [40.0, 50.0, 60.0],
        [70.0, 80.0, 90.0]
    ])
    cloud = build_height_point_cloud(points, terrain)
    assert cloud.shape == (2, 3)
    assert cloud[0, 2] == terrain[0, 0] == 10.0
    assert cloud[1, 2] == terrain[2, 1] == 80.0


def test_find_nearest_point_index():
    points = np.array([
        [0.0, 0.0],
        [10.0, 10.0],
        [100.0, 100.0]
    ])
    idx = find_nearest_point_index(points, (11.0, 9.0))
    assert idx == 1
