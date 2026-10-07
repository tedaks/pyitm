"""Probe: F1 — predict_area with huge delta_h__meter."""
import traceback

from pyitm_ng import predict_area

BASE = dict(
    h_tx__meter=10.0, h_rx__meter=2.0,
    tx_siting=0, rx_siting=0, d__km=50.0,
    climate=3, N_0=301.0, f__mhz=230.0, pol=1, epsilon=15.0, sigma=0.008,
    mdvar=12, time=50.0, location=50.0, situation=50.0,
)

def run(delta_h):
    try:
        r = predict_area(delta_h__meter=delta_h, **BASE)
        return ("ok", r.A__db, int(r.warnings))
    except Exception as e:  # noqa: BLE001
        tb = traceback.extract_tb(e.__traceback__)[-1]
        return ("raise", type(e).__name__, f"{tb.filename}:{tb.lineno}", tb.line)

print("== reported reproducer, delta_h=1e9 ==")
print(run(1e9))

print("\n== reported threshold ==")
print("1.4768244667e8 ->", run(1.4768244667e8))
print("1.4768244668e8 ->", run(1.4768244668e8))

print("\n== bisect the real threshold ==")
lo, hi = 0.0, 1e9
for _ in range(200):
    mid = (lo + hi) / 2
    if run(mid)[0] == "ok":
        lo = mid
    else:
        hi = mid
    if lo == hi:
        break
print("last ok  :", repr(lo), run(lo))
print("first fail:", repr(hi), run(hi))

print("\n== sensitivity: does the threshold move with the other inputs? ==")
for label, override in [
    ("h_tx=30", dict(h_tx__meter=30.0)),
    ("h_rx=10", dict(h_rx__meter=10.0)),
    ("d__km=200", dict(d__km=200.0)),
    ("f__mhz=2000", dict(f__mhz=2000.0)),
    ("tx_siting=2", dict(tx_siting=2)),
    ("d__km=1", dict(d__km=1.0)),
]:
    args = dict(BASE, **override)
    lo, hi = 0.0, 1e12
    for _ in range(200):
        mid = (lo + hi) / 2
        try:
            predict_area(delta_h__meter=mid, **args)
            lo = mid
        except Exception:  # noqa: BLE001
            hi = mid
        if lo == hi:
            break
    print(f"{label:14s} last ok = {lo:.6g}  first fail = {hi:.6g}  exc = {run(0)[0]}")

print("\n== which site underflows, and what the intermediates look like ==")
import pyitm_ng.terrain as T

d = 1.4768244668e8
he, dh, th = T.initialize_area((0, 0), 1.0 / (2.0 * 6370000.0 * 1.3333), d, (10.0, 2.0))
print("h_e   =", he)
print("d_hzn =", dh)
print("theta =", th)
