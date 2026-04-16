# PyITM — Usage Guide

## Installation

```bash
cd /home/bortre/02-lab/sources/pyitm
pip install -e ".[dev]"
```

---

## Point-to-Point Mode

Use when you have an explicit terrain elevation profile between TX and RX.

```python
import numpy as np
from itm import predict_p2p, Climate, Polarization, TerrainProfile

# Build terrain profile manually
elevations = np.zeros(101)          # 101 elevation points (100 intervals)
terrain = TerrainProfile(elevations=elevations, resolution=100.0)  # 100 m spacing → 10 km path

# Or parse from C-style PFL format: [n_intervals, resolution, elev0, elev1, ...]
terrain = TerrainProfile.from_pfl([100, 100.0, 0.0, 5.0, 10.0, ...])

result = predict_p2p(
    h_tx__meter=10.0,
    h_rx__meter=1.0,
    terrain=terrain,
    climate=Climate.CONTINENTAL_TEMPERATE,  # or Climate(5)
    N_0=301.0,           # surface refractivity, N-Units [250–400]
    f__mhz=230.0,        # frequency [20–20000 MHz]
    pol=Polarization.VERTICAL,
    epsilon=15.0,        # ground relative permittivity
    sigma=0.008,         # ground conductivity, S/m
    mdvar=3,             # variability mode (see mdvar reference below)
    time=50.0,           # % of time signal exceeds result
    location=50.0,       # % of locations
    situation=50.0,      # % of situations
)

print(result.A__db)      # basic transmission loss in dB
print(result.warnings)   # bitmask; 0 = no warnings
```

---

## Area Mode

Use when you don't have a terrain profile — just distance and an empirical terrain roughness value.

```python
from itm import predict_area, Climate, Polarization, SitingCriteria

result = predict_area(
    h_tx__meter=100.0,
    h_rx__meter=10.0,
    tx_siting=SitingCriteria.CAREFUL,    # 0=Random, 1=Careful, 2=Very Careful
    rx_siting=SitingCriteria.RANDOM,
    d__km=50.0,                           # path distance in km
    delta_h__meter=90.0,                  # terrain irregularity parameter
    climate=Climate.CONTINENTAL_TEMPERATE,
    N_0=301.0,
    f__mhz=915.0,
    pol=Polarization.VERTICAL,
    epsilon=15.0,
    sigma=0.005,
    mdvar=3,             # Broadcast mode
    time=50.0,
    location=50.0,
    situation=50.0,
)

print(result.A__db)
```

---

## Intermediate Values

Add `return_intermediate=True` to either call to get internal computed values:

```python
result = predict_p2p(..., return_intermediate=True)

iv = result.intermediate
print(iv.d__km)           # path distance
print(iv.A_fs__db)        # free-space loss
print(iv.A_ref__db)       # reference attenuation (before variability)
print(iv.delta_h__meter)  # terrain irregularity
print(iv.h_e__meter)      # effective heights (TX, RX)
print(iv.d_hzn__meter)    # horizon distances (TX, RX)
print(iv.theta_hzn)       # horizon angles (TX, RX), radians
print(iv.N_s)             # surface refractivity
print(iv.mode)            # PropMode.LINE_OF_SIGHT / DIFFRACTION / TROPOSCATTER
```

---

## Checking Warnings

```python
from itm._constants import (
    WARN__TX_TERMINAL_HEIGHT,
    WARN__RX_TERMINAL_HEIGHT,
    WARN__FREQUENCY,
    WARN__EXTREME_VARIABILITIES,
    WARN__SURFACE_REFRACTIVITY,
)

if result.warnings & WARN__FREQUENCY:
    print("Frequency outside validated range [40–10000 MHz]")

if result.warnings & WARN__EXTREME_VARIABILITIES:
    print("Variability percentile beyond 3.1 sigma")
```

---

## mdvar Reference

| Value | Meaning |
|---|---|
| `0` | Single Message — all variability uses situation z-score |
| `1` | Accidental — location uses situation z-score |
| `2` | Mobile — location uses time z-score |
| `3` | Broadcast — independent time, location, situation |
| `+10` | Skip location variability |
| `+20` | Skip situation variability |

Example: `mdvar=13` = Broadcast + no location variability.

---

## Climate Values

| Value | Climate |
|---|---|
| `Climate(1)` | Equatorial |
| `Climate(2)` | Continental Subtropical |
| `Climate(3)` | Maritime Subtropical |
| `Climate(4)` | Desert |
| `Climate(5)` | Continental Temperate |
| `Climate(6)` | Maritime Temperate Over Land |
| `Climate(7)` | Maritime Temperate Over Sea |
