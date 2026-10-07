"""Wide fuzz: port vs C++ over ranges far past the differential's, hunting for any
remaining input the port rejects (or gets wrong) where the C++ computes.

Failure classes:
  * port raised ZeroDivisionError/OverflowError -> MISSED SITE (bad)
  * port raised ValueError -> documented deviation (fine, C++ returns an error code)
  * value/warning mismatch -> DIVERGENCE (bad)
"""
import ctypes
import math
import random
import sys
import traceback

import numpy as np

from pyitm_ng import (Climate, Polarization, SitingCriteria, TerrainProfile,
                      predict_area, predict_p2p)
from pyitm_ng._constants import PYITM_ONLY_WARNINGS

lib = ctypes.CDLL("build/itm-reference/libitm.so")
D, N, L = ctypes.c_double, ctypes.c_int, ctypes.c_long
PD, PL = ctypes.POINTER(D), ctypes.POINTER(L)
lib.ITM_AREA_TLS.argtypes = [D, D, N, N, D, D, N, D, D, N, D, D, N, D, D, D, PD, PL]
lib.ITM_P2P_TLS.argtypes = [D, D, PD, N, D, D, N, D, D, N, D, D, D, PD, PL]

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
N_CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
rng = random.Random(261007 + SEED)
MDVARS = [0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 30, 31, 32, 33]

missed, diverged, documented, ok = [], [], 0, 0


def logu(lo, hi):
    return math.exp(rng.uniform(math.log(lo), math.log(hi)))


def height():
    return rng.choice([0.5, 1.0, 3000.0, 0.5, 1.0]) if rng.random() < 0.3 else logu(0.5, 3000.0)


def common():
    return dict(
        climate=rng.randint(1, 7),
        N_0=rng.choice([250.0, 301.0, 400.0]) if rng.random() < 0.3 else rng.uniform(250.0, 400.0),
        f__mhz=rng.choice([20.0, 20000.0]) if rng.random() < 0.3 else logu(20.0, 20000.0),
        pol=rng.randint(0, 1),
        epsilon=rng.choice([1.0, 1.0 + 2.0**-52]) if rng.random() < 0.3 else logu(1.0, 1e6),
        sigma=rng.choice([5e-324, 1e-300, 10.0]) if rng.random() < 0.3 else logu(1e-300, 10.0),
        mdvar=rng.choice(MDVARS),
        time=rng.choice([0.001, 99.999]) if rng.random() < 0.3 else rng.uniform(0.001, 99.999),
        location=rng.choice([0.001, 99.999]) if rng.random() < 0.3 else rng.uniform(0.001, 99.999),
        situation=rng.choice([0.001, 99.999]) if rng.random() < 0.3 else rng.uniform(0.001, 99.999),
    )


def check(label, cpp, py_fn, py_kw):
    global documented, ok
    rc, cpp_db, cpp_warn = cpp
    try:
        r = py_fn(**py_kw)
    except ValueError:
        documented += 1
        if rc in (0, 1):
            diverged.append(f"{label}: C++ rc={rc} A={cpp_db!r} but Python raised ValueError")
        return
    except Exception as e:  # noqa: BLE001
        tb = traceback.extract_tb(e.__traceback__)[-1]
        missed.append(f"{label}: {type(e).__name__} @ {tb.filename.split('/')[-1]}:{tb.lineno}"
                      f" :: {tb.line}")
        return
    ok += 1
    if rc not in (0, 1):
        diverged.append(f"{label}: C++ rc={rc}, Python returned {r.A__db!r}")
        return
    if math.isnan(cpp_db) and math.isnan(r.A__db):
        pass
    elif cpp_db != r.A__db:
        diverged.append(f"{label}: C++ {cpp_db!r} dB, Python {r.A__db!r} dB")
    elif cpp_warn != int(r.warnings) & ~PYITM_ONLY_WARNINGS:
        diverged.append(f"{label}: C++ warnings {cpp_warn:#x}, Python {int(r.warnings):#x}")


for k in range(N_CASES):
    c = common()
    if rng.random() < 0.5:
        # area
        d__km = rng.choice([0.001, 2000.0]) if rng.random() < 0.3 else logu(1e-3, 1e9)
        dh = rng.choice([0.0, 1e-6, 3000.0]) if rng.random() < 0.3 else logu(1e-6, 1e300)
        tx, rx = rng.randint(0, 2), rng.randint(0, 2)
        h_tx, h_rx = height(), height()
        A, w = ctypes.c_double(), ctypes.c_long()
        rc = lib.ITM_AREA_TLS(h_tx, h_rx, tx, rx, d__km, dh, c["climate"], c["N_0"], c["f__mhz"],
                              c["pol"], c["epsilon"], c["sigma"], c["mdvar"], c["time"],
                              c["location"], c["situation"], ctypes.byref(A), ctypes.byref(w))
        check(f"area k={k} d={d__km:g} dh={dh:g} h={h_tx:g}/{h_rx:g} sit={tx}/{rx}",
              (rc, A.value, w.value), predict_area,
              dict(h_tx__meter=h_tx, h_rx__meter=h_rx, tx_siting=SitingCriteria(tx),
                   rx_siting=SitingCriteria(rx), d__km=d__km, delta_h__meter=dh,
                   climate=Climate(c["climate"]), **{kk: c[kk] for kk in
                   ("N_0", "f__mhz", "pol", "epsilon", "sigma", "mdvar", "time", "location",
                    "situation")}))
    else:
        # p2p
        n = rng.choice([1, 2, 3, 10]) if rng.random() < 0.3 else rng.randint(1, 600)
        res = rng.choice([1.0, 2000.0]) if rng.random() < 0.3 else logu(1e-3, 1e300)
        res = min(res, 1e305 / n)
        if n * res == float("inf"):
            continue
        style = rng.random()
        if style < 0.25:
            elevs = np.zeros(n + 1)
        elif style < 0.5:
            elevs = np.full(n + 1, rng.choice([-1e7, -3013.0, 1e6, 1e300, -1e300, 0.0]))
        elif style < 0.75:
            elevs = np.cumsum(np.random.default_rng(k).normal(0.0, rng.choice([0.5, 60.0, 5000.0]), n + 1))
            elevs += rng.choice([-50.0, 3000.0, -1e5, 1e5])
        else:
            elevs = np.full(n + 1, rng.uniform(-1e6, 1e6))
        pfl = [float(n), res] + elevs.tolist()
        h_tx, h_rx = height(), height()
        A, w = ctypes.c_double(), ctypes.c_long()
        rc = lib.ITM_P2P_TLS(h_tx, h_rx, (ctypes.c_double * len(pfl))(*pfl), c["climate"],
                             c["N_0"], c["f__mhz"], c["pol"], c["epsilon"], c["sigma"],
                             c["mdvar"], c["time"], c["location"], c["situation"],
                             ctypes.byref(A), ctypes.byref(w))
        check(f"p2p k={k} n={n} res={res:g} elev0={pfl[2]:g} h={h_tx:g}/{h_rx:g}",
              (rc, A.value, w.value), predict_p2p,
              dict(h_tx__meter=h_tx, h_rx__meter=h_rx, terrain=TerrainProfile.from_pfl(pfl),
                   climate=Climate(c["climate"]), **{kk: c[kk] for kk in
                   ("N_0", "f__mhz", "pol", "epsilon", "sigma", "mdvar", "time", "location",
                    "situation")}))
    if k % 1000 == 0:
        print(f"  {k}/{N_CASES}  ok={ok} documented={documented} missed={len(missed)} "
              f"diverged={len(diverged)}", flush=True)

print(f"\nseed {SEED}: {N_CASES} cases | ok={ok} documented-ValueError={documented} "
      f"| MISSED SITES={len(missed)} | divergences={len(diverged)}")
for m in missed[:15]:
    print("  MISSED:", m)
for d in diverged[:15]:
    print("  DIVERGED:", d)
