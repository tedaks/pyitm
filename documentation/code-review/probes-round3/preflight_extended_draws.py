"""Pre-flight: run the *extended* differential draws through the C++ reference only.

The reference casts distances to int internally (LinearLeastSquaresFit), so a draw that
overflows its int range would SIGSEGV this process. Run standalone: a crash shows up as
a non-zero exit instead of taking the test suite down with it.
"""
import ctypes
import math
import random
import sys

import numpy as np

lib = ctypes.CDLL("build/itm-reference/libitm.so")
D, N, L = ctypes.c_double, ctypes.c_int, ctypes.c_long
PD, PL = ctypes.POINTER(D), ctypes.POINTER(L)
lib.ITM_P2P_TLS.argtypes = [D, D, PD, N, D, D, N, D, D, N, D, D, D, PD, PL]
lib.ITM_AREA_TLS.argtypes = [D, D, N, N, D, D, N, D, D, N, D, D, N, D, D, D, PD, PL]

N_CASES = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
SEED = 0
MDVARS = [0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 30, 31, 32, 33]


def _pick(rng, lo, hi, edges, log=False, p_edge=0.15):
    if rng.random() < p_edge:
        return rng.choice(edges)
    if log:
        return math.exp(rng.uniform(math.log(lo), math.log(hi)))
    return rng.uniform(lo, hi)


def _height(rng):
    return _pick(rng, 0.5, 3000.0, [0.5, 1.0, 1000.0, 2999.0, 3000.0], log=True)


def _percent(rng):
    return _pick(rng, 0.001, 99.999,
                 [0.001, 0.01, 0.1, 1.0, 50.0, 99.0, 99.9, 99.99, 99.999], p_edge=0.25)


def _common(rng):
    return [
        rng.randint(1, 7),
        _pick(rng, 250.0, 400.0, [250.0, 301.0, 400.0]),
        _pick(rng, 20.0, 20000.0, [20.0, 40.0, 10000.0, 20000.0], log=True),
        rng.randint(0, 1),
        _pick(rng, 1.0, 100.0, [1.0, 80.0], log=True),
        _pick(rng, 1e-5, 10.0, [1e-5, 5.0], log=True),
        rng.choice(MDVARS),
        _percent(rng), _percent(rng), _percent(rng),
    ]


def _p2p_cases():
    rng = random.Random(20261006 + SEED)
    for k in range(N_CASES):
        if rng.random() < 0.2:
            n = rng.choice([1, 1, 2, 3, 5, 10])
        else:
            n = rng.randint(1, 600)
        resolution = _pick(rng, 1.0, 2000.0, [1.0, 10.0, 1000.0], log=True)
        if k % 4 == 0:  # extended draw
            resolution = _pick(rng, 1e-3, 1e300,
                               [1.0, 10.0, 1000.0, 2000.0, 1e6, 1e9, 1e12, 1e30, 1e300], log=True)
        step_sd = rng.choice([0.5, 3.0, 15.0, 60.0])
        elevs = np.cumsum(np.random.default_rng(k + 1_000_003 * SEED).normal(0.0, step_sd, n + 1))
        elevs += rng.uniform(-50.0, 3000.0)
        pfl = [float(n), resolution] + elevs.tolist()
        yield k, pfl, [_height(rng), _height(rng)] + _common(rng)


def _area_cases():
    rng = random.Random(20261007 + SEED)
    for k in range(N_CASES):
        dh = _pick(rng, 0.0, 3000.0, [0.0, 0.001, 3000.0])
        if k % 4 == 0:  # extended draw
            dh = _pick(rng, 1e-3, 1e12,
                       [0.0, 0.001, 3000.0, 1.476824467e8, 5.6655e8, 1e9, 1e12], log=True)
        yield k, [
            _height(rng), _height(rng), rng.randint(0, 2), rng.randint(0, 2),
            _pick(rng, 0.001, 2000.0, [0.001, 1.0, 1000.0, 2000.0], log=True),
            dh,
        ] + _common(rng)


n_p2p = n_area = 0
rc_counts = {}
max_d = 0.0
for k, pfl, a in _p2p_cases():
    h_tx, h_rx, climate, N_0, f, pol, eps, sigma, mdvar, t, loc, sit = a
    d = pfl[0] * pfl[1]
    max_d = max(max_d, d)
    if math.isinf(d):
        print(f"INF distance at case {k}: n={pfl[0]} res={pfl[1]!r} -> would segfault")
        sys.exit(2)
    A, w = ctypes.c_double(), ctypes.c_long()
    rc = lib.ITM_P2P_TLS(h_tx, h_rx, (ctypes.c_double * len(pfl))(*pfl), climate, N_0, f, pol,
                         eps, sigma, mdvar, t, loc, sit, ctypes.byref(A), ctypes.byref(w))
    rc_counts[rc] = rc_counts.get(rc, 0) + 1
    n_p2p += 1
    if k % 1000 == 0:
        print(f"p2p {k}/{N_CASES} rc={rc} A={A.value} d={d:g}", flush=True)

for k, a in _area_cases():
    h_tx, h_rx, tx_site, rx_site, d, dh, climate, N_0, f, pol, eps, sigma, mdvar, t, loc, sit = a
    A, w = ctypes.c_double(), ctypes.c_long()
    rc = lib.ITM_AREA_TLS(h_tx, h_rx, tx_site, rx_site, d, dh, climate, N_0, f, pol, eps,
                          sigma, mdvar, t, loc, sit, ctypes.byref(A), ctypes.byref(w))
    rc_counts[rc] = rc_counts.get(rc, 0) + 1
    n_area += 1
    if k % 1000 == 0:
        print(f"area {k}/{N_CASES} rc={rc} A={A.value} dh={dh:g}", flush=True)

print(f"\nOK: {n_p2p} p2p + {n_area} area cases, no crash. max implied distance {max_d:g} m")
print("rc histogram:", dict(sorted(rc_counts.items())))
