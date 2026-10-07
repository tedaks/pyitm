"""Probe: the F1 defect class reached through p2p (huge but finite resolution).

Runs against whichever pyitm_ng is first on sys.path (so it can be pointed at the
ieee_div-patched copy).
"""
import ctypes
import traceback

import numpy as np

import pyitm_ng
from pyitm_ng import TerrainProfile, predict_p2p

print("module:", pyitm_ng.__file__)

lib = ctypes.CDLL("build/itm-reference/libitm.so")
D, N, L = ctypes.c_double, ctypes.c_int, ctypes.c_long
PD, PL = ctypes.POINTER(D), ctypes.POINTER(L)
lib.ITM_P2P_TLS.argtypes = [D, D, PD, N, D, D, N, D, D, N, D, D, D, PD, PL]
COMMON = (3, 301.0, 230.0, 1, 15.0, 0.008, 12, 50.0, 50.0, 50.0)


def cpp(npts, res):
    pfl = (ctypes.c_double * (npts + 2))(float(npts - 1), res, *([0.0] * npts))
    A, w = ctypes.c_double(), ctypes.c_long()
    rc = lib.ITM_P2P_TLS(10.0, 2.0, pfl, *COMMON, ctypes.byref(A), ctypes.byref(w))
    return rc, A.value, w.value


def py(npts, res):
    try:
        t = TerrainProfile(elevations=np.zeros(npts), resolution=res)
        r = predict_p2p(h_tx__meter=10.0, h_rx__meter=2.0, terrain=t, climate=3, N_0=301.0,
                        f__mhz=230.0, pol=1, epsilon=15.0, sigma=0.008, mdvar=12,
                        time=50.0, location=50.0, situation=50.0)
        return f"A={r.A__db!r} w={int(r.warnings):#x}"
    except Exception as e:  # noqa: BLE001
        tb = traceback.extract_tb(e.__traceback__)[-1]
        return f"{type(e).__name__}@{tb.filename.split('/')[-1]}:{tb.lineno} :: {tb.line}"


print(f"{'npts':>5} {'resolution':>10} {'d__m':>12} | C++ rc  A__db (warn)  | Python")
for npts, res in ((10, 3e9), (10, 1e30), (10, 1e100), (3, 1e308), (600, 1e300),
                  (600, 1e12), (10, 1e12), (2, 1e308), (10, 2000.0)):
    d = (npts - 1) * res
    if d in (float("inf"), float("-inf")):
        # d__meter overflows to inf: the C++ reference SIGSEGVs here (probed separately),
        # so there is no reference result to compare against.
        print(f"{npts:>5} {res:>10.4g} {d:>12.6g} | C++ SIGSEGV (d inf)  | {py(npts, res)}")
        continue
    try:
        rc, A, w = cpp(npts, res)
        c = f"{rc:>7} {A:>14.6g} ({w:#x})"
    except Exception as e:  # noqa: BLE001
        c = f"raised {e}"
    print(f"{npts:>5} {res:>10.4g} {d:>12.6g} | {c}  | {py(npts, res)}")
