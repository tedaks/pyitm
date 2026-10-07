"""Battery: hostile-but-accepted inputs -> does the port raise? reports the site.

No C++ calls here (some of these inputs segfault the reference), so this can be run
freely. The C++ comparison for the same inputs lives in verify_matches_cpp.py.
"""
import traceback

import numpy as np

from pyitm_ng import TerrainProfile, predict_area, predict_area_cr, predict_p2p, predict_p2p_cr

COMMON = dict(climate=3, N_0=301.0, f__mhz=230.0, pol=1, epsilon=15.0, sigma=0.008, mdvar=12,
              time=50.0, location=50.0, situation=50.0)
AREA = dict(h_tx__meter=10.0, h_rx__meter=2.0, tx_siting=0, rx_siting=0, d__km=50.0,
            delta_h__meter=50.0, **COMMON)

sites = {}
n_ok = 0


def run(label, fn):
    global n_ok
    try:
        r = fn()
    except ValueError as e:
        # Documented deviation: the port raises where the C++ returns an error code.
        n_ok += 1
        return None
    except Exception as e:  # noqa: BLE001
        tb = traceback.extract_tb(e.__traceback__)[-1]
        sid = f"{tb.filename.split('/')[-1]}:{tb.lineno}"
        sites.setdefault(sid, []).append((label, type(e).__name__, tb.line))
        return None
    n_ok += 1
    return r


def flat(npts, res, elev=0.0):
    return TerrainProfile(elevations=np.full(npts, elev), resolution=res)


# A) area: huge delta_h x heights
for dh in (1.0e8, 1.4768e8, 1.476824467e8, 1.5e8, 5.0e8, 5.6655e8, 6.0e8, 1e9, 1e12, 1e300):
    for h_rx in (0.5, 1.0, 2.0, 5.0, 8.0, 10.0, 3000.0):
        run(f"area dh={dh:g} h_rx={h_rx}", lambda dh=dh, h_rx=h_rx:
            predict_area(**{**AREA, "delta_h__meter": dh, "h_rx__meter": h_rx}))

# B) area: other extremes
for d in (0.001, 1.0, 2000.0, 1e6, 1e9):
    run(f"area d={d:g}", lambda d=d: predict_area(**{**AREA, "d__km": d, "delta_h__meter": 1e9}))
for n0 in (250.0, 400.0):
    run(f"area N_0={n0}", lambda n0=n0: predict_area(**{**AREA, "N_0": n0, "delta_h__meter": 1e9}))
for sit in (1, 2):
    run(f"area siting={sit}", lambda sit=sit:
        predict_area(**{**AREA, "tx_siting": sit, "rx_siting": sit, "delta_h__meter": 1e9}))
for eps in (1.0, 1.0 + 2.0**-52, 1e12):
    run(f"area eps={eps!r}", lambda eps=eps: predict_area(**{**AREA, "epsilon": eps}))
for sig in (5e-324, 1e-300, 1e-5, 10.0):
    run(f"area sigma={sig!r}", lambda sig=sig: predict_area(**{**AREA, "sigma": sig}))
for pct in (0.001, 0.01, 99.99, 99.999):
    run(f"area pct={pct}", lambda pct=pct:
        predict_area(**{**AREA, "time": pct, "location": pct, "situation": pct}))

# C) p2p: resolution / profile length
for res in (1e-6, 1e-3, 1.0, 30.0, 2000.0, 1e6, 1e9, 1e12, 1e30, 1e100, 1e300):
    for npts in (2, 3, 5, 10, 600):
        if (npts - 1) * res == float("inf"):
            continue  # d__meter inf: the C++ segfaults, out of scope
        run(f"p2p res={res:g} n={npts}", lambda res=res, npts=npts:
            predict_p2p(h_tx__meter=10.0, h_rx__meter=2.0, terrain=flat(npts, res), **COMMON))

# D) p2p: absurd elevations (median elevation drives N_s)
for elev in (-7e6, -3013.0, -3000.0, 1e6, 1e300, -1e300):
    run(f"p2p elev={elev:g}", lambda elev=elev:
        predict_p2p(h_tx__meter=10.0, h_rx__meter=2.0, terrain=flat(10, 30.0, elev), **COMMON))
for n0 in (250.0, 400.0):
    for elev in (-3013.0, -3010.0, 3000.0):
        run(f"p2p N_0={n0} elev={elev:g}", lambda n0=n0, elev=elev:
            predict_p2p(h_tx__meter=10.0, h_rx__meter=2.0, terrain=flat(10, 30.0, elev),
                        **{**COMMON, "N_0": n0}))

# E) p2p: heights at the range limits, steep synthetic profiles
rng = np.random.default_rng(7)
for h in (0.5, 1.0, 3000.0):
    run(f"p2p h={h}", lambda h=h:
        predict_p2p(h_tx__meter=h, h_rx__meter=h, terrain=flat(10, 30.0), **COMMON))
    run(f"p2p h={h} steep", lambda h=h:
        predict_p2p(h_tx__meter=h, h_rx__meter=h,
                    terrain=TerrainProfile(elevations=np.cumsum(rng.normal(0, 500.0, 11)), resolution=1000.0),
                    **COMMON))
run("p2p 12km profile 1m res", lambda:
    predict_p2p(h_tx__meter=1.0, h_rx__meter=1.0,
                terrain=TerrainProfile(elevations=np.cumsum(rng.normal(0, 900.0, 12001)), resolution=1.0),
                **{**COMMON, "f__mhz": 20000.0}))

_AREA_CR = {k: v for k, v in AREA.items() if k not in ("time", "location", "situation")}

# F) CR entry points on the hostile inputs
run("area_cr dh=1e9", lambda: predict_area_cr(
    **{**_AREA_CR, "delta_h__meter": 1e9}, confidence=50.0, reliability=50.0))
run("p2p_cr res=1e30", lambda: predict_p2p_cr(
    h_tx__meter=10.0, h_rx__meter=2.0, terrain=flat(10, 1e30),
    **{k: v for k, v in COMMON.items() if k not in ("time", "location", "situation")},
    confidence=50.0, reliability=50.0))

print(f"{n_ok} ran clean, {sum(len(v) for v in sites.values())} raised\n")
for sid, cases in sorted(sites.items()):
    print(f"--- {sid}  ({len(cases)} cases)")
    print(f"    {cases[0][2]}")
    for label, exc, _ in cases[:4]:
        print(f"      {label}  -> {exc}")
    if len(cases) > 4:
        print(f"      ... and {len(cases) - 4} more")
