# PyITM — Functions & Capabilities Reference

## Overview

A pure-Python port of the ITS Irregular Terrain Model (Longley-Rice) for radiowave propagation prediction between 20 MHz and 20 GHz. Models three propagation mechanisms: free-space, diffraction, and troposcatter. Library only — no CLI.

**Python:** ≥ 3.10 | **Dependencies:** NumPy | **Validated:** ±0.01 dB vs. reference FORTRAN 1.2.2

---

## Public API (`itm/`)

### Entry Points — `itm/itm.py`

| Function | Description |
|---|---|
| `predict_p2p(...)` | Point-to-point prediction using an explicit terrain elevation profile |
| `predict_area(...)` | Area-mode prediction using empirical terrain statistics (no profile needed) |

Both return a `PropagationResult` with `A__db` (loss in dB), `warnings` bitmask, and optional `IntermediateValues`.

**Common parameters:**

| Parameter | Type | Range | Unit | Purpose |
|---|---|---|---|---|
| `h_tx__meter` | float | [0.5, 3000] | m | TX antenna height |
| `h_rx__meter` | float | [0.5, 3000] | m | RX antenna height |
| `climate` | Climate | 1–7 | — | Radio climate |
| `N_0` | float | [250, 400] | N-Units | Surface refractivity |
| `f__mhz` | float | [20, 20000] | MHz | Frequency |
| `pol` | Polarization | 0–1 | — | Polarization (H/V) |
| `epsilon` | float | >1 | — | Ground relative permittivity |
| `sigma` | float | >0 | S/m | Ground conductivity |
| `mdvar` | int | 0–3, ±10, ±20 | — | Variability mode |
| `time, location, situation` | float | (0, 100) | % | Variability percentages |
| `return_intermediate` | bool | — | — | Populate `IntermediateValues` in output |

`predict_p2p` additionally takes `terrain: TerrainProfile`.
`predict_area` additionally takes `tx_siting`, `rx_siting` (`SitingCriteria`), `d__km`, and `delta_h__meter`.

---

## Terrain Analysis — `itm/terrain.py`

| Function | Description |
|---|---|
| `find_horizons(elevations, resolution, h, a_e)` | Computes radio horizon angles and distances for TX and RX by scanning elevation profile |
| `compute_delta_h(elevations, resolution, d_start, d_end)` | Terrain irregularity parameter via inter-decile range of deviations from linear fit |
| `quick_pfl(terrain, gamma_e, h)` | Extracts all path parameters from terrain profile in one pass (horizons, effective heights, delta_h, distance) |
| `linear_least_squares_fit(elevations, resolution, d_start, d_end)` | Linear fit to elevation data between two distances |
| `initialize_area(site_criteria, gamma_e, delta_h, h)` | Computes effective heights and horizon values for area-mode (siting-quality bonus applied) |

---

## Propagation Loss — `itm/propagation.py`

| Function | Description |
|---|---|
| `free_space_loss(d, f_mhz)` | Basic free-space transmission loss (dB) |
| `fresnel_integral(v2)` | Approximate knife-edge diffraction via Fresnel integrals |
| `knife_edge_diffraction(...)` | Knife-edge diffraction loss (two-ray model) |
| `smooth_earth_diffraction(...)` | Smooth-Earth diffraction via Vogler 3-radii method |
| `diffraction_loss(...)` | Combined diffraction blending knife-edge, smooth-earth, and terrain clutter |
| `line_of_sight_loss(...)` | LOS attenuation including ground reflection and terrain roughness |
| `height_function(x_km, K)` | Vogler height gain function F(x, K) for smooth-earth diffraction |
| `h0_function(r, eta_s)` | Troposcatter frequency gain H₀(r, η_s) via interpolated curve fits |
| `h0_curve(j, r)` | Piecewise 4th-order polynomial for H₀ curve |
| `f_function(td)` | Attenuation function F(θ·d) for troposcatter (3-segment piecewise linear) |
| `troposcatter_loss(...)` | Trans-horizon troposcatter propagation loss |
| `initialize_point_to_point(...)` | Computes surface refractivity N_s, effective Earth curvature γ_e, and ground impedance Z_g |
| `longley_rice(...)` | **Core algorithm**: multi-region propagation combining LOS, diffraction, and troposcatter |

---

## Signal Variability — `itm/variability.py`

| Function | Description |
|---|---|
| `iccdf(q)` | Inverse complementary CDF — converts probability to z-score (Abramowitz & Stegun) |
| `terrain_roughness(d, delta_h)` | Effective terrain roughness as function of distance |
| `sigma_h_function(delta_h)` | RMS terrain deviation within first Fresnel zone |
| `variability(time, location, situation, ...)` | Main variability engine: applies time/location/situation spreading using climate-dependent statistical tables and variability mode |
| `curve(c1, c2, x1, x2, x3, d_e)` | Rational curve model for climate-dependent gain/loss (TN101v2) |

---

## Data Models — `itm/models.py`

| Type | Kind | Description |
|---|---|---|
| `TerrainProfile` | dataclass | Elevation array + resolution; `from_pfl()` parses C-style PFL format |
| `PropagationResult` | dataclass | Output: `A__db`, `warnings`, optional `intermediate` |
| `IntermediateValues` | dataclass | Internal values: horizon angles/distances, effective heights, N_s, δh, A_ref, A_fs, d, PropMode |
| `Climate` | IntEnum | 7 climates: Equatorial (1) → Maritime Temperate Sea (7) |
| `Polarization` | IntEnum | Horizontal (0) / Vertical (1) |
| `MDVar` | IntEnum | Single Message (0), Accidental (1), Mobile (2), Broadcast (3); +10 skips location var, +20 skips situation var |
| `PropMode` | IntEnum | Line-of-Sight (1), Diffraction (2), Troposcatter (3) |
| `SitingCriteria` | IntEnum | Random (0), Careful (1), Very Careful (2) |

---

## Constants & Warnings — `itm/_constants.py`

14 warning bitmask flags:

| Constant | Trigger |
|---|---|
| `WARN__TX_TERMINAL_HEIGHT` | TX height outside [1, 1000] m |
| `WARN__RX_TERMINAL_HEIGHT` | RX height outside [1, 1000] m |
| `WARN__FREQUENCY` | Frequency outside [40, 10000] MHz |
| `WARN__PATH_DISTANCE_TOO_SMALL_*` | Path distance below minimum threshold |
| `WARN__PATH_DISTANCE_TOO_BIG_*` | Path distance above maximum threshold |
| `WARN__TX_HORIZON_ANGLE` | TX horizon angle > 0.2 rad |
| `WARN__RX_HORIZON_ANGLE` | RX horizon angle > 0.2 rad |
| `WARN__TX_HORIZON_DISTANCE_*` | TX horizon distance out of range |
| `WARN__RX_HORIZON_DISTANCE_*` | RX horizon distance out of range |
| `WARN__EXTREME_VARIABILITIES` | Any variability z-score beyond ±3.1 σ |
| `WARN__SURFACE_REFRACTIVITY` | N_s < 250 N-Units |

Inspect with: `result.warnings & WARN__<flag>`

---

## Test Coverage — `tests/`

| File | What it covers |
|---|---|
| `test_p2p.py` | 35+ parametrized tests vs. reference CSV; ±0.01 dB tolerance |
| `test_area.py` | Area-mode vs. reference CSV |
| `test_itm.py` | Input validation, warning flags, intermediate values |
| `test_terrain.py` | Horizon finding, delta-h, PFL parsing |
| `test_propagation.py` | Free-space loss, Fresnel, H₀, ground impedance |
| `test_variability.py` | ICCDF, terrain roughness, variability engine |
| `test_models.py` | Enums, dataclasses, PFL constructor |

---

## Key Design Notes

- **No CLI** — import `itm.predict_p2p` or `itm.predict_area`
- **Warning system** — bitmask accumulates across all stages; inspect individual flags with `&`
- **Naming convention** — pseudo-LaTeX underscores: `h_e__meter`, `A_ref__db`, `d__km`
- **Two modes** — Point-to-Point (explicit terrain profile) vs. Area (distance + empirical δh)
- **CI** — GitHub Actions runs `pytest -v` and `ruff check itm/` on every push/PR to main
