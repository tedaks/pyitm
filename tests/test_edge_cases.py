# tests/test_edge_cases.py
"""Edges of the valid input space where the port used to crash or diverge from the
C++ (found by fuzzing the full documented ranges). Expected values come from NTIA/itm
C++ (ITM_P2P_TLS, master 183ad95, built by tools/build_itm_reference.sh)."""

import pickle
import platform

import numpy as np
import pytest

from pyitm_ng import Polarization, TerrainProfile, Warnings, predict_p2p


# Bit-identity with the C++ is claimed (and the values below were computed) on Linux
# with glibc's libm; other math libraries may differ in the last bits.
GLIBC = platform.system() == "Linux" and platform.libc_ver()[0] == "glibc"


def _cpp(value):
    return value if GLIBC else pytest.approx(value, rel=1e-12)


def _p2p(pfl, h_tx, h_rx, f, pol=Polarization.VERTICAL, epsilon=15.0, sigma=0.005):
    return predict_p2p(
        h_tx__meter=h_tx, h_rx__meter=h_rx, terrain=TerrainProfile.from_pfl(pfl), climate=5,
        N_0=301.0, f__mhz=f, pol=pol, epsilon=epsilon, sigma=sigma, mdvar=12,
        time=50.0, location=50.0, situation=50.0,
    )


@pytest.mark.parametrize("pfl, h_tx, h_rx, f, expected", [
    ([1.0, 1000.0, 100.0, 120.0], 10.0, 2.0, 900.0, 94.45647484360744),
    ([1.0, 30000.0, 0.0, 50.0], 30.0, 10.0, 230.0, 134.68045045365963),
])
def test_two_point_profile(pfl, h_tx, h_rx, f, expected):
    # 1 interval, no interior points: FindHorizons' loop runs zero times
    # (np.argmax used to raise on the empty interior)
    assert _p2p(pfl, h_tx, h_rx, f).A__db == _cpp(expected)


def test_reference_attenuation_nan_is_flagged_and_matches_cpp():
    # At h_tx = 1000 m the diffraction step breaks down (Vogler's B_0 < 0 -> log10 of a
    # negative number -> nan). The C++ continues and MAX(A_ref, 0) turns the nan into
    # 0 dB; pyitm-ng returns the same bits and sets REFERENCE_ATTENUATION_NAN.
    r = _p2p([6.0, 10.0, 181.0, 200.0, 8.0, 61.0, 265.0, 294.0, 114.0], 1000.0, 1.0, 100.0)
    assert r.A__db == _cpp(48.013023041676036)
    assert Warnings.REFERENCE_ATTENUATION_NAN in r.warnings
    assert r.warnings & ~Warnings.REFERENCE_ATTENUATION_NAN == 0x7E0  # the C++ warnings


def test_ordinary_path_not_flagged():
    r = _p2p([99.0, 100.0] + [0.0] * 100, 10.0, 2.0, 230.0)
    assert Warnings.REFERENCE_ATTENUATION_NAN not in r.warnings


@pytest.mark.parametrize("sigma, f", [(0.005, 230.0), (0.001, 230.0), (0.002, 230.0), (0.005, 10000.0)])
def test_epsilon_one_horizontal_is_ground_impedance_error(sigma, f):
    # epsilon == 1 makes ep_r - 1 purely imaginary; glibc's csqrt returns equal real
    # and imaginary parts, so the C++ rejects it (ERROR__GROUND_IMPEDANCE, rc 1013).
    # CPython's cmath.sqrt puts the imaginary part 1 ulp lower for the last three
    # (sigma, f) pairs, which let them through as a result.
    with pytest.raises(ValueError, match="Ground impedance"):
        _p2p([99.0, 100.0] + [0.0] * 100, 10.0, 2.0, f, pol=Polarization.HORIZONTAL, epsilon=1.0, sigma=sigma)


def test_epsilon_one_vertical_matches_cpp():
    r = _p2p([99.0, 100.0] + [0.0] * 100, 10.0, 2.0, 230.0, pol=Polarization.VERTICAL, epsilon=1.0)
    assert r.A__db == _cpp(134.7756410495386)


def test_terrain_signed_zero_hash_contract():
    a = TerrainProfile(elevations=np.array([0.0, 5.0, -0.0]), resolution=10.0)
    b = TerrainProfile(elevations=np.array([-0.0, 5.0, 0.0]), resolution=10.0)
    assert a == b
    assert hash(a) == hash(b)


def test_terrain_pickle_round_trip_stays_immutable():
    t = TerrainProfile(elevations=np.arange(10.0), resolution=30.0)
    u = pickle.loads(pickle.dumps(t))
    assert u == t and hash(u) == hash(t)
    with pytest.raises(ValueError, match="read-only"):
        u.elevations[0] = 1.0
