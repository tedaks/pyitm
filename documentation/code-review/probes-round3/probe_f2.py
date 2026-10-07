"""Probe: F2 corrected (proper PFL header) — C++ vs Python on the absurd profile."""
import ctypes

import numpy as np

from pyitm_ng import TerrainProfile, predict_p2p

lib = ctypes.CDLL("build/itm-reference/libitm.so")
D, N, L = ctypes.c_double, ctypes.c_int, ctypes.c_long
PD, PL = ctypes.POINTER(D), ctypes.POINTER(L)
lib.ITM_P2P_TLS.argtypes = [D, D, PD, N, D, D, N, D, D, N, D, D, D, PD, PL]

COMMON = (3, 301.0, 230.0, 1, 15.0, 0.008, 12, 50.0, 50.0, 50.0)

for res, npts in ((3e9, 10), (3e9, 2), (2000.0, 10), (1.0e7, 600)):
    np_ = npts - 1
    pfl = (ctypes.c_double * (npts + 2))(float(np_), res, *([0.0] * npts))
    A, warn = ctypes.c_double(), ctypes.c_long()
    rc = lib.ITM_P2P_TLS(10.0, 2.0, pfl, *COMMON, ctypes.byref(A), ctypes.byref(warn))
    t = TerrainProfile(elevations=np.zeros(npts), resolution=res)
    r = predict_p2p(h_tx__meter=10.0, h_rx__meter=2.0, terrain=t, climate=3, N_0=301.0,
                    f__mhz=230.0, pol=1, epsilon=15.0, sigma=0.008, mdvar=12,
                    time=50.0, location=50.0, situation=50.0)
    d = (npts - 1) * res
    print(f"n={npts} res={res:.3g} d={d:.4g} m  C++: rc={rc} A={A.value!r} w={warn.value:#x}"
          f"  |  py: A={r.A__db!r} w={int(r.warnings):#x}  |  equal={A.value == r.A__db}")
