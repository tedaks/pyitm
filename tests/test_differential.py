# tests/test_differential.py
"""
Differential test: predict_p2p / predict_area against the NTIA/itm C++ reference
on randomly generated inputs. The reference CSVs only cover a handful of paths;
this catches numeric divergences (e.g. rounding that flips an int() truncation)
that they miss.

Skipped unless ITM_REFERENCE_LIB points at a libitm.so built by
tools/build_itm_reference.sh. ITM_DIFF_CASES sets the case count (default 1000).
Tolerance: 0.01 dB; warning bitmasks and error/no-error must match exactly.
"""

import ctypes
import os
import random

import numpy as np
import pytest

from itm import (
    Climate,
    Polarization,
    SitingCriteria,
    TerrainProfile,
    predict_area,
    predict_p2p,
)

LIB_PATH = os.environ.get("ITM_REFERENCE_LIB")
N_CASES = int(os.environ.get("ITM_DIFF_CASES", "1000"))
TOL__DB = 0.01

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
    return lib


def _common(rng):
    # climate, N_0, f__mhz, pol, epsilon, sigma, mdvar, time, location, situation
    return [
        rng.randint(1, 7),
        rng.uniform(250.0, 400.0),
        rng.uniform(20.0, 20000.0),
        rng.randint(0, 1),
        rng.uniform(1.0, 80.0),
        rng.uniform(1e-4, 5.0),
        rng.choice(MDVARS),
        rng.uniform(1.0, 99.0),
        rng.uniform(1.0, 99.0),
        rng.uniform(1.0, 99.0),
    ]


def _p2p_cases():
    rng = random.Random(20261006)
    for k in range(N_CASES):
        n = rng.randint(10, 600)
        resolution = rng.uniform(10.0, 1000.0)
        step_sd = rng.choice([0.5, 3.0, 15.0])
        elevs = np.cumsum(np.random.default_rng(k).normal(0.0, step_sd, n + 1))
        elevs += rng.uniform(0.0, 500.0)
        pfl = [float(n), resolution] + elevs.tolist()
        yield k, pfl, [rng.uniform(0.5, 300.0), rng.uniform(0.5, 300.0)] + _common(rng)


def _area_cases():
    rng = random.Random(20261007)
    for k in range(N_CASES):
        yield k, [
            rng.uniform(0.5, 300.0),
            rng.uniform(0.5, 300.0),
            rng.randint(0, 2),
            rng.randint(0, 2),
            rng.uniform(1.0, 2000.0),
            rng.uniform(0.0, 500.0),
        ] + _common(rng)


def _compare(cpp, py, label, mismatches):
    rc, cpp_db, cpp_warn = cpp
    cpp_err = rc not in (0, 1)
    py_err = isinstance(py, Exception)
    if cpp_err or py_err:
        if cpp_err != py_err:
            mismatches.append(f"{label}: C++ rc={rc}, Python {py!r}")
        return
    if abs(cpp_db - py.A__db) > TOL__DB:
        mismatches.append(f"{label}: C++ {cpp_db:.4f} dB, Python {py.A__db:.4f} dB")
    elif cpp_warn != py.warnings:
        mismatches.append(f"{label}: C++ warnings {cpp_warn:#x}, Python {py.warnings:#x}")


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
