# tests/test_propagation.py
import math
from itm.propagation import (
    free_space_loss,
    fresnel_integral,
    h0_curve,
    h0_function,
    initialize_point_to_point,
)


def test_free_space_loss():
    # [Algorithm] A_fs = 32.45 + 20*log10(f_mhz) + 20*log10(d_km)
    # d=10000m=10km, f=100MHz: 32.45 + 20*2 + 20*1 = 32.45+40+20 = 92.45
    assert math.isclose(free_space_loss(10000.0, 100.0), 92.45, rel_tol=1e-5)


def test_fresnel_integral_below_threshold():
    # v2=1.0 < 5.76: 6.02 + 9.11*sqrt(1) - 1.27*1 = 6.02 + 9.11 - 1.27 = 13.86
    assert math.isclose(fresnel_integral(1.0), 13.86, rel_tol=1e-4)


def test_fresnel_integral_above_threshold():
    # v2=10.0 > 5.76: 12.953 + 10*log10(10) = 12.953 + 10 = 22.953
    assert math.isclose(fresnel_integral(10.0), 22.953, rel_tol=1e-4)


def test_h0_curve_known():
    # h0_curve(0, r=1.0): 10*log10(1 + 25*1 + 24*1) = 10*log10(50) ≈ 16.99
    assert math.isclose(h0_curve(0, 1.0), 10 * math.log10(50.0), rel_tol=1e-6)


def test_h0_function_clamps_eta():
    # eta_s < 1 should be clamped to 1 -> uses j=0 (i=1, q=0)
    result_low = h0_function(1.0, 0.5)
    result_one = h0_function(1.0, 1.0)
    # With eta_s clamped to 1 in h0_function, both should be equal
    assert math.isclose(result_low, result_one, rel_tol=1e-9)
    # eta_s > 5 should be clamped to 5 -> same result as eta_s=5.0 (q=0, no interpolation)
    assert math.isclose(h0_function(1.0, 6.0), h0_function(1.0, 5.0), rel_tol=1e-9)


def test_initialize_point_to_point_horizontal():
    Z_g, gamma_e, N_s = initialize_point_to_point(
        f__mhz=300.0, h_sys__meter=0.0, N_0=301.0, pol=0, epsilon=15.0, sigma=0.005
    )
    # N_s = N_0 when h_sys=0
    assert math.isclose(N_s, 301.0, rel_tol=1e-9)
    # gamma_e should be close to gamma_a * constant
    assert 1e-8 < gamma_e < 2e-7
    # Z_g should have positive real part
    assert Z_g.real > 0
