"""Probe: what the C++ reference does on the F1/F2 inputs (ctypes, no exceptions)."""
import ctypes

lib = ctypes.CDLL("build/itm-reference/libitm.so")
D, N, L = ctypes.c_double, ctypes.c_int, ctypes.c_long
PD, PL = ctypes.POINTER(D), ctypes.POINTER(L)
lib.ITM_AREA_TLS.argtypes = [D, D, N, N, D, D, N, D, D, N, D, D, N, D, D, D, PD, PL]
lib.ITM_P2P_TLS.argtypes = [D, D, PD, N, D, D, N, D, D, N, D, D, D, PD, PL]

BASE = (10.0, 2.0, 0, 0, 50.0)          # h_tx, h_rx, tx_site, rx_site, d__km
COMMON = (3, 301.0, 230.0, 1, 15.0, 0.008, 12, 50.0, 50.0, 50.0)


def call_area(delta_h):
    A, warn = ctypes.c_double(), ctypes.c_long()
    rc = lib.ITM_AREA_TLS(*BASE, delta_h, *COMMON, ctypes.byref(A), ctypes.byref(warn))
    return rc, A.value, warn.value


print("== C++ ITM_AREA_TLS vs delta_h__meter (same args as the Python reproducer) ==")
for dh in (0.0, 50.0, 3000.0, 1e6, 1.4768244667e8, 1.4768244668e8, 5.6655e8, 1e9, 1e12, 1e300):
    try:
        rc, A, w = call_area(dh)
        print(f"delta_h={dh:<14g} rc={rc}  A__db={A!r}  warnings={w:#x}")
    except Exception as e:  # noqa: BLE001
        print(f"delta_h={dh:<14g} probe failed: {e}")

print("\n== the same, but the Python port ==")
import numpy as np  # noqa: E402

from pyitm_ng import predict_area  # noqa: E402

PY = dict(h_tx__meter=10.0, h_rx__meter=2.0, tx_siting=0, rx_siting=0, d__km=50.0,
          climate=3, N_0=301.0, f__mhz=230.0, pol=1, epsilon=15.0, sigma=0.008,
          mdvar=12, time=50.0, location=50.0, situation=50.0)
for dh in (0.0, 50.0, 3000.0, 1e6, 1.4768244667e8, 1.4768244668e8, 5.6655e8, 1e9):
    try:
        r = predict_area(delta_h__meter=dh, **PY)
        print(f"delta_h={dh:<14g} A__db={r.A__db!r}  warnings={int(r.warnings):#x}")
    except Exception as e:  # noqa: BLE001
        print(f"delta_h={dh:<14g} {type(e).__name__}: {e}")

print("\n== F2: C++ ITM_P2P_TLS with the absurd profile (10 points, resolution 3e9 m) ==")
elevs = [0.0] * 10
pfl = (ctypes.c_double * 12)(10.0, 3e9, *elevs)
A, warn = ctypes.c_double(), ctypes.c_long()
rc = lib.ITM_P2P_TLS(10.0, 2.0, pfl, *COMMON, ctypes.byref(A), ctypes.byref(warn))
print("rc =", rc, " A__db =", A.value, f" warnings={warn.value:#x}")
print("implied d__meter =", 9 * 3e9)
