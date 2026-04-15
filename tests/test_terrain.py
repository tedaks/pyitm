# tests/test_terrain.py
import math
import pytest
import numpy as np
from itm.terrain import find_horizons, compute_delta_h, quick_pfl
from itm.models import TerrainProfile


def test_find_horizons_flat_earth():
    # Flat terrain at 0m, 2 terminals each 10m high, 10 km apart
    # With a_e = actual earth radius 6370e3:
    np_ = 10
    elevs = np.zeros(np_ + 1)
    h = (10.0, 10.0)
    a_e = 6370e3
    theta_hzn, d_hzn__meter = find_horizons(elevs, 1000.0, h, a_e)
    # Both horizons should be at full path distance (LOS condition)
    assert len(theta_hzn) == 2
    assert len(d_hzn__meter) == 2
    assert d_hzn__meter[0] == pytest.approx(10000.0, rel=1e-6)
    assert d_hzn__meter[1] == pytest.approx(10000.0, rel=1e-6)


def test_compute_delta_h_flat():
    # Flat terrain -> delta_h should be 0
    elevs = np.zeros(101)  # 100 intervals, resolution=100m, 10km path
    dh = compute_delta_h(elevs, 100.0, 1000.0, 9000.0)
    assert math.isclose(dh, 0.0, abs_tol=1e-6)


def test_quick_pfl_path_distance():
    # quick_pfl returns correct path distance
    np_ = 100
    elevs = np.zeros(np_ + 1)
    terrain = TerrainProfile(elevations=elevs, resolution=100.0)
    h = (10.0, 10.0)
    gamma_e = 1.0 / 6370e3
    theta_hzn, d_hzn, h_e, delta_h, d = quick_pfl(terrain, gamma_e, h)
    assert math.isclose(d, np_ * 100.0, rel_tol=1e-9)
