# tests/test_differential.py
"""
Differential test: predict_p2p / predict_area against the NTIA/itm C++ reference
on randomly generated inputs. The reference CSVs only cover a handful of paths;
this catches numeric divergences (e.g. rounding that flips an int() truncation)
that they miss.

Skipped unless ITM_REFERENCE_LIB points at a libitm.so built by
tools/build_itm_reference.sh. ITM_DIFF_CASES sets the case count (default 1000), ITM_DIFF_SEED the draw (default 0).
Inputs cover the full documented ranges, with boundary values over-sampled, and every
fourth case draws delta_h (area) or the profile resolution (p2p) from the decades past
the documented range -- places where the C++ divides by zero in IEEE and carries the
result on, so the port must not raise either.
Tolerance: 0.01 dB; warning bitmasks and error/no-error must match exactly.
ITM_DIFF_EXACT=1 tightens the tolerance to bit-identical A__db, which is what the
fidelity policy in CLAUDE.md requires (a reordered reduction stays well inside
0.01 dB, so only exact mode can catch it).
"""

import ctypes
import math
import os
import random

import numpy as np
import pytest

from pyitm_ng._constants import PYITM_ONLY_WARNINGS
from pyitm_ng import (
    Climate,
    Polarization,
    SitingCriteria,
    TerrainProfile,
    predict_area,
    predict_area_cr,
    predict_p2p,
    predict_p2p_cr,
)

LIB_PATH = os.environ.get("ITM_REFERENCE_LIB")
N_CASES = int(os.environ.get("ITM_DIFF_CASES", "1000"))
TOL__DB = 0.01
EXACT = os.environ.get("ITM_DIFF_EXACT", "") not in ("", "0")

pytestmark = pytest.mark.skipif(
    not LIB_PATH, reason="ITM_REFERENCE_LIB not set (see tools/build_itm_reference.sh)"
)

MDVARS = [0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 30, 31, 32, 33]


@pytest.fixture(scope="module")
def lib():
    D, N, L = ctypes.c_double, ctypes.c_int, ctypes.c_long
    PD, PL = ctypes.POINTER(D), ctypes.POINTER(L)
    lib = ctypes.CDLL(LIB_PATH)
    lib.ITM_P2P_TLS.argtypes = [D, D, PD, N, D, D, N, D, D, N, D, D, D, PD, PL]
    lib.ITM_AREA_TLS.argtypes = [D, D, N, N, D, D, N, D, D, N, D, D, N, D, D, D, PD, PL]
    lib.ITM_P2P_CR.argtypes = [D, D, PD, N, D, D, N, D, D, N, D, D, PD, PL]
    lib.ITM_AREA_CR.argtypes = [D, D, N, N, D, D, N, D, D, N, D, D, N, D, D, PD, PL]
    return lib


# The whole documented input space, not a comfortable sub-range: every bug found by
# widening this (2-point profiles, h_tx near 3000 m, epsilon == 1, NaN swallowed by
# MAX/MIN at extreme percentiles) sat outside the old 0.5-300 m / 1-99 % / 10-600 point
# ranges. A share of draws is pinned to the boundary values themselves.
SEED = int(os.environ.get("ITM_DIFF_SEED", "0"))


def _pick(rng, lo, hi, edges, log=False, p_edge=0.15):
    if rng.random() < p_edge:
        return rng.choice(edges)
    if log:
        return math.exp(rng.uniform(math.log(lo), math.log(hi)))
    return rng.uniform(lo, hi)


def _height(rng):  # valid: [0.5, 3000] m
    return _pick(rng, 0.5, 3000.0, [0.5, 1.0, 1000.0, 2999.0, 3000.0], log=True)


def _percent(rng):  # valid: (0, 100)
    return _pick(rng, 0.001, 99.999, [0.001, 0.01, 0.1, 1.0, 50.0, 99.0, 99.9, 99.99, 99.999], p_edge=0.25)


# delta_h has no documented upper bound and the C++ accepts any value >= 0. Past
# ~1.5e8 m Vogler's third radius underflows to 0.0 (a__meter[2]), and past ~5.7e8 m the
# horizon distance d_hzn itself does, so the C++ divides by zero there -- IEEE gives
# +-inf/nan and it carries the result on. Every fourth case draws from the decades above
# that instead of only the comfortable [0, 3000] m band: the port used to raise
# ZeroDivisionError where the C++ returned a value (audit round 3, F1).
_DELTA_H = [0.0, 0.001, 3000.0, 1.476824467e8, 5.6655e8, 1e9, 1e12]


def _delta_h(rng, extended):
    if not extended:
        return _pick(rng, 0.0, 3000.0, [0.0, 0.001, 3000.0])
    return _pick(rng, 1e-3, 1e12, _DELTA_H, log=True)


# resolution is a TerrainProfile argument with no upper bound either (finite and > 0 is
# all that is validated), so a 600-point profile can span 6e302 m. The C++ divides path
# distances there too -- d_4 - d_3 rounds to 0.0 once d is large enough, and both
# a__meter[0] and Vogler's radii can be 0. Kept finite on purpose: d__meter == inf
# overflows the reference's internal (int) casts and SIGSEGVs it.
_RESOLUTION = [1.0, 10.0, 1000.0, 2000.0, 1e6, 1e9, 1e12, 1e30, 1e300]


def _resolution(rng, n_intervals, extended):
    if not extended:
        return _pick(rng, 1.0, 2000.0, [1.0, 10.0, 1000.0], log=True)
    return min(_pick(rng, 1e-3, 1e300, _RESOLUTION, log=True), 1e305 / n_intervals)


def _common(rng):
    # climate, N_0, f__mhz, pol, epsilon, sigma, mdvar, time, location, situation
    return [
        rng.randint(1, 7),
        _pick(rng, 250.0, 400.0, [250.0, 301.0, 400.0]),
        _pick(rng, 20.0, 20000.0, [20.0, 40.0, 10000.0, 20000.0], log=True),
        rng.randint(0, 1),
        _pick(rng, 1.0, 100.0, [1.0, 80.0], log=True),
        _pick(rng, 1e-5, 10.0, [1e-5, 5.0], log=True),
        rng.choice(MDVARS),
        _percent(rng),
        _percent(rng),
        _percent(rng),
    ]


def _p2p_cases():
    rng = random.Random(20261006 + SEED)
    for k in range(N_CASES):
        if rng.random() < 0.2:
            n = rng.choice([1, 1, 2, 3, 5, 10])  # 1 interval = 2 points, the minimum
        else:
            n = rng.randint(1, 600)
        resolution = _resolution(rng, n, extended=k % 4 == 0)
        step_sd = rng.choice([0.5, 3.0, 15.0, 60.0])
        elevs = np.cumsum(np.random.default_rng(k + 1_000_003 * SEED).normal(0.0, step_sd, n + 1))
        elevs += rng.uniform(-50.0, 3000.0)
        pfl = [float(n), resolution] + elevs.tolist()
        yield k, pfl, [_height(rng), _height(rng)] + _common(rng)


def _area_cases():
    rng = random.Random(20261007 + SEED)
    for k in range(N_CASES):
        yield k, [
            _height(rng),
            _height(rng),
            rng.randint(0, 2),
            rng.randint(0, 2),
            _pick(rng, 0.001, 2000.0, [0.001, 1.0, 1000.0, 2000.0], log=True),
            _delta_h(rng, extended=k % 4 == 0),
        ] + _common(rng)


def _compare(cpp, py, label, mismatches):
    rc, cpp_db, cpp_warn = cpp
    cpp_err = rc not in (0, 1)
    py_err = isinstance(py, Exception)
    if cpp_err or py_err:
        if cpp_err != py_err:
            mismatches.append(f"{label}: C++ rc={rc}, Python {py!r}")
        return
    if math.isnan(cpp_db) and math.isnan(py.A__db):
        pass  # both nan: same IEEE outcome (e.g. iccdf(0) propagated)
    elif EXACT and cpp_db != py.A__db:
        mismatches.append(f"{label}: C++ {cpp_db!r} dB, Python {py.A__db!r} dB (not bit-identical)")
    elif abs(cpp_db - py.A__db) > TOL__DB:
        mismatches.append(f"{label}: C++ {cpp_db:.4f} dB, Python {py.A__db:.4f} dB")
    elif cpp_warn != py.warnings & ~PYITM_ONLY_WARNINGS:
        mismatches.append(f"{label}: C++ warnings {cpp_warn:#x}, Python {int(py.warnings):#x}")


def test_p2p_matches_cpp_reference(lib):
    mismatches = []
    for k, pfl, a in _p2p_cases():
        h_tx, h_rx, climate, N_0, f, pol, eps, sigma, mdvar, t, loc, sit = a
        A, warn = ctypes.c_double(), ctypes.c_long()
        rc = lib.ITM_P2P_TLS(
            h_tx, h_rx, (ctypes.c_double * len(pfl))(*pfl), climate, N_0, f, pol, eps,
            sigma, mdvar, t, loc, sit, ctypes.byref(A), ctypes.byref(warn),
        )
        try:
            py = predict_p2p(
                h_tx__meter=h_tx, h_rx__meter=h_rx, terrain=TerrainProfile.from_pfl(pfl),
                climate=Climate(climate), N_0=N_0, f__mhz=f, pol=Polarization(pol),
                epsilon=eps, sigma=sigma, mdvar=mdvar, time=t, location=loc, situation=sit,
            )
        except ValueError as e:
            py = e
        _compare((rc, A.value, warn.value), py, f"p2p case {k}", mismatches)
    assert not mismatches, f"{len(mismatches)}/{N_CASES} mismatches:\n" + "\n".join(mismatches[:20])


def test_area_matches_cpp_reference(lib):
    mismatches = []
    for k, a in _area_cases():
        h_tx, h_rx, tx_site, rx_site, d, dh, climate, N_0, f, pol, eps, sigma, mdvar, t, loc, sit = a
        A, warn = ctypes.c_double(), ctypes.c_long()
        rc = lib.ITM_AREA_TLS(
            h_tx, h_rx, tx_site, rx_site, d, dh, climate, N_0, f, pol, eps, sigma, mdvar,
            t, loc, sit, ctypes.byref(A), ctypes.byref(warn),
        )
        try:
            py = predict_area(
                h_tx__meter=h_tx, h_rx__meter=h_rx, tx_siting=SitingCriteria(tx_site),
                rx_siting=SitingCriteria(rx_site), d__km=d, delta_h__meter=dh,
                climate=Climate(climate), N_0=N_0, f__mhz=f, pol=Polarization(pol),
                epsilon=eps, sigma=sigma, mdvar=mdvar, time=t, location=loc, situation=sit,
            )
        except ValueError as e:
            py = e
        _compare((rc, A.value, warn.value), py, f"area case {k}", mismatches)
    assert not mismatches, f"{len(mismatches)}/{N_CASES} mismatches:\n" + "\n".join(mismatches[:20])


def _run_p2p(lib, pfl, a):
    h_tx, h_rx, climate, N_0, f, pol, eps, sigma, mdvar, t, loc, sit = a
    A, warn = ctypes.c_double(), ctypes.c_long()
    rc = lib.ITM_P2P_TLS(
        h_tx, h_rx, (ctypes.c_double * len(pfl))(*pfl), climate, N_0, f, pol, eps,
        sigma, mdvar, t, loc, sit, ctypes.byref(A), ctypes.byref(warn),
    )
    try:
        py = predict_p2p(
            h_tx__meter=h_tx, h_rx__meter=h_rx, terrain=TerrainProfile.from_pfl(pfl),
            climate=Climate(climate), N_0=N_0, f__mhz=f, pol=Polarization(pol),
            epsilon=eps, sigma=sigma, mdvar=mdvar, time=t, location=loc, situation=sit,
        )
    except ValueError as e:
        py = e
    return (rc, A.value, warn.value), py


def test_underflowing_percentiles_match_cpp(lib):
    """time/location/situation so small that x / 100 underflows to 0: the C++ has no
    domain check, iccdf(0) is nan, and Variability either discards it (mdvar picks
    another percentile) or propagates it. Python must do exactly the same, not raise."""
    mismatches = []
    pfl = [10.0, 100.0] + [float(10 * i % 37) for i in range(11)]
    for mdvar in MDVARS:
        for t, loc, sit in [(5e-324, 50.0, 50.0), (50.0, 5e-324, 50.0), (50.0, 50.0, 5e-324)]:
            a = [10.0, 10.0, 5, 301.0, 3000.0, 1, 15.0, 0.005, mdvar, t, loc, sit]
            cpp, py = _run_p2p(lib, pfl, a)
            _compare(cpp, py, f"p2p mdvar={mdvar} t={t} l={loc} s={sit}", mismatches)
    assert not mismatches, "\n".join(mismatches)


# Ground-impedance extremes: the smallest sigma > 0 (ep_r imaginary part underflows to 0),
# epsilon at its floor, both polarizations (pol=1 divides Z_g by ep_r), the frequency
# range ends, and a short line-of-sight path so LineOfSightLoss's (sin_psi + Z_g)
# denominator is exercised. The C++ returns a result or an error code here; Python must
# do the same and never raise ZeroDivisionError.
GROUND_EXTREMES = [
    (pol, eps, sigma, f)
    for pol in (0, 1)
    for eps in (1.0, 1.0 + 2.0**-52, 100.0)
    for sigma in (5e-324, 1e-300, 1e-5, 10.0)
    for f in (20.0, 20000.0)
]


def test_ground_impedance_extremes_match_cpp(lib):
    mismatches = []
    for pfl in ([10.0, 10.0] + [100.0] * 11, [100.0, 500.0] + [float(i % 7) for i in range(101)]):
        for pol, eps, sigma, f in GROUND_EXTREMES:
            a = [30.0, 30.0, 5, 301.0, f, pol, eps, sigma, 12, 50.0, 50.0, 50.0]
            cpp, py = _run_p2p(lib, pfl, a)
            _compare(cpp, py, f"p2p pol={pol} eps={eps!r} sigma={sigma!r} f={f} np={pfl[0]}", mismatches)
    assert not mismatches, "\n".join(mismatches)


def test_p2p_cr_matches_cpp_reference(lib):
    """Confidence/reliability entry point; the random location percentile is used as
    reliability and the situation percentile as confidence."""
    mismatches = []
    for k, pfl, a in _p2p_cases():
        h_tx, h_rx, climate, N_0, f, pol, eps, sigma, mdvar, _t, rel, conf = a
        A, warn = ctypes.c_double(), ctypes.c_long()
        rc = lib.ITM_P2P_CR(
            h_tx, h_rx, (ctypes.c_double * len(pfl))(*pfl), climate, N_0, f, pol, eps,
            sigma, mdvar, conf, rel, ctypes.byref(A), ctypes.byref(warn),
        )
        try:
            py = predict_p2p_cr(
                h_tx__meter=h_tx, h_rx__meter=h_rx, terrain=TerrainProfile.from_pfl(pfl),
                climate=Climate(climate), N_0=N_0, f__mhz=f, pol=Polarization(pol),
                epsilon=eps, sigma=sigma, mdvar=mdvar, confidence=conf, reliability=rel,
            )
        except ValueError as e:
            py = e
        _compare((rc, A.value, warn.value), py, f"p2p_cr case {k}", mismatches)
    assert not mismatches, f"{len(mismatches)}/{N_CASES} mismatches:\n" + "\n".join(mismatches[:20])


def test_area_cr_matches_cpp_reference(lib):
    mismatches = []
    for k, a in _area_cases():
        h_tx, h_rx, tx_site, rx_site, d, dh, climate, N_0, f, pol, eps, sigma, mdvar, _t, rel, conf = a
        A, warn = ctypes.c_double(), ctypes.c_long()
        rc = lib.ITM_AREA_CR(
            h_tx, h_rx, tx_site, rx_site, d, dh, climate, N_0, f, pol, eps, sigma, mdvar,
            conf, rel, ctypes.byref(A), ctypes.byref(warn),
        )
        try:
            py = predict_area_cr(
                h_tx__meter=h_tx, h_rx__meter=h_rx, tx_siting=SitingCriteria(tx_site),
                rx_siting=SitingCriteria(rx_site), d__km=d, delta_h__meter=dh,
                climate=Climate(climate), N_0=N_0, f__mhz=f, pol=Polarization(pol),
                epsilon=eps, sigma=sigma, mdvar=mdvar, confidence=conf, reliability=rel,
            )
        except ValueError as e:
            py = e
        _compare((rc, A.value, warn.value), py, f"area_cr case {k}", mismatches)
    assert not mismatches, f"{len(mismatches)}/{N_CASES} mismatches:\n" + "\n".join(mismatches[:20])


# The audit that found F1 measured these boundaries: Vogler's third radius a__meter[2]
# underflows to 0.0 at delta_h ~ 1.4768e8 m (h_e <= 5), and d_hzn itself reaches 0.0 at
# ~5.6655e8 m; d_4 - d_3 rounds to 0.0 for a large enough path distance. All of them are
# plain IEEE division by zero in the C++.
EXTREME_DELTA_H = [1.0e8, 1.4768244667e8, 1.4768244668e8, 5.6655e8, 6.0e8, 1e9, 1e12, 1e300]
EXTREME_RESOLUTION = [1e-3, 1.0, 2000.0, 1e6, 1e9, 1e12, 1e30, 1e100]


def test_extreme_delta_h_matches_cpp(lib):
    """Area mode with delta_h past both underflow thresholds (see _DELTA_H)."""
    mismatches = []
    for dh in EXTREME_DELTA_H:
        for h_rx in (0.5, 2.0, 5.0, 10.0, 3000.0):
            for tx_site, rx_site in ((0, 0), (2, 2)):
                a = [10.0, h_rx, tx_site, rx_site, 50.0, dh] + [3, 301.0, 230.0, 1, 15.0,
                                                               0.008, 12, 50.0, 50.0, 50.0]
                A, warn = ctypes.c_double(), ctypes.c_long()
                rc = lib.ITM_AREA_TLS(
                    a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9], a[10], a[11],
                    a[12], a[13], a[14], a[15], ctypes.byref(A), ctypes.byref(warn),
                )
                try:
                    py = predict_area(
                        h_tx__meter=a[0], h_rx__meter=a[1], tx_siting=SitingCriteria(a[2]),
                        rx_siting=SitingCriteria(a[3]), d__km=a[4], delta_h__meter=a[5],
                        climate=Climate(a[6]), N_0=a[7], f__mhz=a[8], pol=Polarization(a[9]),
                        epsilon=a[10], sigma=a[11], mdvar=a[12], time=a[13], location=a[14],
                        situation=a[15],
                    )
                except ValueError as e:
                    py = e
                _compare((rc, A.value, warn.value), py,
                         f"area delta_h={dh!r} h_rx={h_rx} siting={tx_site}/{rx_site}", mismatches)
    assert not mismatches, f"{len(mismatches)} mismatches:\n" + "\n".join(mismatches[:20])


def test_extreme_resolution_matches_cpp(lib):
    """Profiles whose implied path length is far past the model's range."""
    mismatches = []
    for resolution in EXTREME_RESOLUTION:
        for n in (2, 3, 10, 600):
            if n * resolution == float("inf"):
                continue
            pfl = [float(n - 1), resolution] + [0.0] * n
            a = [10.0, 2.0] + [3, 301.0, 230.0, 1, 15.0, 0.008, 12, 50.0, 50.0, 50.0]
            cpp, py = _run_p2p(lib, pfl, a)
            _compare(cpp, py, f"p2p resolution={resolution!r} n={n}", mismatches)
    assert not mismatches, f"{len(mismatches)} mismatches:\n" + "\n".join(mismatches[:20])


def test_long_profiles_match_cpp_reference(lib):
    """1,000-10,000 point profiles: the random cases stop at 600 points, but
    compute_delta_h's resampling skips many points per step only on long paths."""
    mismatches = []
    rng = random.Random(20261008)
    n_cases = max(50, N_CASES // 25)
    for k in range(n_cases):
        n = rng.randint(1000, 10000)
        elevs = np.cumsum(np.random.default_rng(10_000_000 + k).normal(0.0, rng.choice([0.5, 3.0, 15.0]), n + 1))
        pfl = [float(n), rng.uniform(10.0, 200.0)] + (elevs + rng.uniform(0.0, 500.0)).tolist()
        a = [rng.uniform(0.5, 300.0), rng.uniform(0.5, 300.0)] + _common(rng)
        cpp, py = _run_p2p(lib, pfl, a)
        _compare(cpp, py, f"long p2p case {k} (n={n})", mismatches)
    assert not mismatches, f"{len(mismatches)}/{n_cases} mismatches:\n" + "\n".join(mismatches[:20])
