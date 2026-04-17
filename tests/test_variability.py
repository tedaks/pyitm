# tests/test_variability.py
import math
import pytest
import numpy as np
from itm._constants import WARN__EXTREME_VARIABILITIES
from itm.models import Climate, MDVar
from itm.variability import (
    iccdf,
    terrain_roughness,
    sigma_h_function,
    linear_least_squares_fit,
    curve,
    variability,
)


def test_iccdf_symmetry():
    assert math.isclose(iccdf(0.1), -iccdf(0.9), rel_tol=1e-6)


def test_iccdf_midpoint():
    assert math.isclose(iccdf(0.5), 0.0, abs_tol=1e-6)


def test_iccdf_domain_error():
    with pytest.raises(ValueError, match="iccdf requires"):
        iccdf(0.0)
    with pytest.raises(ValueError, match="iccdf requires"):
        iccdf(1.0)


def test_iccdf_known_values():
    # Q^-1(0.5) = 0.0 (median)
    assert math.isclose(iccdf(0.5), 0.0, abs_tol=1e-5)
    # Q^-1(0.1) ≈ 1.2816
    assert math.isclose(iccdf(0.1), 1.2816, abs_tol=1e-3)
    # Q^-1(0.9) ≈ -1.2816 (symmetric)
    assert math.isclose(iccdf(0.9), -1.2816, abs_tol=1e-3)


def test_terrain_roughness_zero_distance():
    # At d=0, factor = 1 - 0.8*exp(0) = 0.2
    assert math.isclose(terrain_roughness(0.0, 50.0), 50.0 * 0.2, rel_tol=1e-9)


def test_terrain_roughness_large_distance():
    # At large distance, approaches delta_h (factor → 1.0)
    assert math.isclose(terrain_roughness(1e9, 50.0), 50.0, rel_tol=1e-6)


def test_sigma_h_function():
    # sigma_h = 0.78 * delta_h * exp(-0.5 * delta_h^0.25)
    dh = 20.0
    expected = 0.78 * dh * math.exp(-0.5 * dh**0.25)
    assert math.isclose(sigma_h_function(dh), expected, rel_tol=1e-9)


def test_linear_least_squares_fit_flat():
    # Flat terrain: fit should return same value at both ends
    elevs = np.full(11, 100.0)  # 11 points, all at 100m
    fit_y1, fit_y2 = linear_least_squares_fit(elevs, 100.0, 0.0, 1000.0)
    assert math.isclose(fit_y1, 100.0, rel_tol=1e-6)
    assert math.isclose(fit_y2, 100.0, rel_tol=1e-6)


def test_linear_least_squares_fit_ramp():
    # Linear ramp from 0 to 1000m over 11 points, resolution=100
    elevs = np.linspace(0.0, 1000.0, 11)
    fit_y1, fit_y2 = linear_least_squares_fit(elevs, 100.0, 0.0, 1000.0)
    assert math.isclose(fit_y1, 0.0, abs_tol=1e-6)
    assert math.isclose(fit_y2, 1000.0, abs_tol=1e-6)


def test_curve_zero_distance():
    # At d_e=0, the factor d_e^2/(1+d_e^2) -> 0, so curve -> 0
    assert math.isclose(curve(1.0, 2.0, 100e3, 50e3, 30e3, 0.0), 0.0, abs_tol=1e-10)


def test_variability_returns_float_and_warnings():
    # Sanity check: result is a float, warnings is an int
    result, warns = variability(
        time=50.0,
        location=50.0,
        situation=50.0,
        h_e__meter=[10.0, 10.0],
        delta_h__meter=0.0,
        f__mhz=100.0,
        d__meter=50e3,
        A_ref__db=80.0,
        climate=Climate.CONTINENTAL_TEMPERATE,
        mdvar=MDVar.BROADCAST,
    )
    assert isinstance(result, float)
    assert isinstance(warns, int)


def test_variability_extreme_warns():
    # time=0.09 → z_T ≈ 3.12, just above limit → should trigger WARN__EXTREME_VARIABILITIES
    _, warns = variability(
        time=0.09,
        location=50.0,
        situation=50.0,
        h_e__meter=[10.0, 10.0],
        delta_h__meter=0.0,
        f__mhz=100.0,
        d__meter=50e3,
        A_ref__db=80.0,
        climate=Climate.CONTINENTAL_TEMPERATE,
        mdvar=MDVar.BROADCAST,
    )
    assert warns & WARN__EXTREME_VARIABILITIES
