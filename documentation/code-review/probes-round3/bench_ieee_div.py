"""Timing check: does routing divisions through ieee_div cost anything measurable?

Medians of 7 x 400-call repeats, run in the same interpreter state for one checkout.
"""
import gc
import statistics
import timeit

import numpy as np

from pyitm_ng import TerrainProfile, predict_area, predict_p2p

P2P_KW = dict(h_tx__meter=10.0, h_rx__meter=2.0, climate=3, N_0=301.0, f__mhz=230.0, pol=1,
              epsilon=15.0, sigma=0.008, mdvar=12, time=50.0, location=50.0, situation=50.0)
AREA_KW = dict(h_tx__meter=10.0, h_rx__meter=2.0, tx_siting=0, rx_siting=0, d__km=50.0,
               delta_h__meter=90.0, climate=3, N_0=301.0, f__mhz=230.0, pol=1, epsilon=15.0,
               sigma=0.008, mdvar=12, time=50.0, location=50.0, situation=50.0)

rng = np.random.default_rng(3)
short = TerrainProfile(elevations=np.cumsum(rng.normal(0.0, 5.0, 51)) + 100.0, resolution=30.0)
long_ = TerrainProfile(elevations=np.cumsum(rng.normal(0.0, 15.0, 601)) + 500.0, resolution=30.0)

CASES = [
    ("p2p 50 pts (p2p, troposcatter-ish)", lambda: predict_p2p(terrain=short, **P2P_KW), 400),
    ("p2p 600 pts", lambda: predict_p2p(terrain=long_, **P2P_KW), 400),
    ("area", lambda: predict_area(**AREA_KW), 400),
]


def bench(fn, n):
    fn()
    gc.disable()
    try:
        return min(statistics.median(timeit.repeat(fn, number=n, repeat=7)) / n * 1e6 for _ in [0])
    finally:
        gc.enable()


for label, fn, n in CASES:
    print(f"{label:38s} {bench(fn, n):9.2f} us/call")
