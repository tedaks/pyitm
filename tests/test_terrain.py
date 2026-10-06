# tests/test_terrain.py
import math
import pytest
import numpy as np
from pyitm_ng.terrain import find_horizons, compute_delta_h, quick_pfl
from pyitm_ng.models import TerrainProfile


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


def test_find_horizons_distances_match_cpp_accumulation():
    # The C++ reference builds horizon distances as d_tx += xi / d_rx -= xi, which
    # differs in the last bit from i * xi. Distances must match it exactly.
    np_ = 11
    xi = 146.1
    elevs = np.array([377.0, 206.0, 139.0, 211.0, 329.0, 141.0, 298.0, 175.0, 156.0, 147.0, 375.0, 72.0])
    theta_hzn, d_hzn__meter = find_horizons(elevs, xi, (50.0, 1.0), 8.5e6)
    d_tx, d_rx = 0.0, np_ * xi
    tx_steps, rx_steps = [], []
    for _ in range(1, np_):
        d_tx += xi
        d_rx -= xi
        tx_steps.append(d_tx)
        rx_steps.append(d_rx)
    assert d_hzn__meter[0] in tx_steps + [np_ * xi]
    assert d_hzn__meter[1] in rx_steps + [np_ * xi]
