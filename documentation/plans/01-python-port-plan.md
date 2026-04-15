# ITM Python Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the ITM/Longley-Rice C++ library to a pure Python package with a Pythonic API that passes all reference test cases within 0.01 dB.

**Architecture:** Seven-module package (`_constants`, `models`, `terrain`, `variability`, `propagation`, `itm`, `__init__`) where internal functions accept plain Python/numpy types and return values instead of output pointers. Public entry points are `predict_p2p` and `predict_area` in `itm.py`. Warnings accumulate as OR'd bitmasks returned from internal functions and propagated up through callers.

**Tech Stack:** Python ≥ 3.10, numpy, pytest

---

## File Map

| File | Purpose |
|------|---------|
| `pyproject.toml` | Build config and dependencies |
| `itm/__init__.py` | Re-exports public API |
| `itm/_constants.py` | Named constants replacing magic numbers |
| `itm/models.py` | Enums (Climate, Polarization, MDVar, PropMode, SitingCriteria) + dataclasses (TerrainProfile, IntermediateValues, PropagationResult) |
| `itm/variability.py` | `iccdf`, `terrain_roughness`, `sigma_h_function`, `linear_least_squares_fit`, `curve`, `variability` |
| `itm/terrain.py` | `find_horizons`, `compute_delta_h`, `quick_pfl`, `initialize_area` |
| `itm/propagation.py` | `free_space_loss`, `fresnel_integral`, `knife_edge_diffraction`, `height_function`, `smooth_earth_diffraction`, `h0_curve`, `h0_function`, `f_function`, `troposcatter_loss`, `line_of_sight_loss`, `diffraction_loss`, `initialize_point_to_point`, `longley_rice` |
| `itm/itm.py` | `_validate_inputs`, `predict_p2p`, `predict_area` |
| `tests/test_models.py` | TerrainProfile dataclass and from_pfl |
| `tests/test_variability.py` | Unit tests for all variability.py functions |
| `tests/test_terrain.py` | Unit tests for terrain.py functions |
| `tests/test_propagation.py` | Unit tests for propagation.py functions |
| `tests/test_p2p.py` | Integration: all rows of p2p.csv + pfls.csv |
| `tests/test_area.py` | Integration: all rows of area.csv |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `itm/__init__.py`, `itm/_constants.py`, `itm/models.py`, `itm/variability.py`, `itm/terrain.py`, `itm/propagation.py`, `itm/itm.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "itm"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["numpy"]

[project.optional-dependencies]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package skeleton**

```bash
mkdir -p itm tests
touch itm/__init__.py itm/_constants.py itm/models.py \
      itm/variability.py itm/terrain.py itm/propagation.py itm/itm.py \
      tests/__init__.py
```

- [ ] **Step 3: Install in editable mode**

```bash
pip install -e ".[dev]"
```

Expected: `Successfully installed itm-0.1.0`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml itm/ tests/
git commit -m "chore: add Python package scaffold"
```

---

## Task 2: Constants and Models

**Files:**
- Write: `itm/_constants.py`
- Write: `itm/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import numpy as np
from itm.models import (
    Climate, Polarization, MDVar, PropMode, SitingCriteria,
    TerrainProfile, IntermediateValues, PropagationResult,
)

def test_climate_values():
    assert Climate.EQUATORIAL == 1
    assert Climate.MARITIME_TEMPERATE_SEA == 7

def test_terrain_profile_from_pfl():
    pfl = [3.0, 100.0, 10.0, 20.0, 15.0, 25.0, 12.0]
    # np=3, resolution=100m, elevations=[10,20,15,25,12] (np+2 = 5 values)
    tp = TerrainProfile.from_pfl(pfl)
    assert tp.resolution == 100.0
    assert len(tp.elevations) == 4   # np+1 = 4 points
    assert tp.elevations[0] == 10.0
    assert tp.elevations[3] == 25.0

def test_propagation_result_defaults():
    r = PropagationResult(A__db=142.5, warnings=0)
    assert r.intermediate is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write `_constants.py`**

```python
# itm/_constants.py
import math

PI          = 3.1415926535897932384
SQRT2       = math.sqrt(2)
THIRD       = 1.0 / 3.0
a_0__meter  = 6370e3    # actual earth radius
a_9000__meter = 9000e3  # reference radius for variability effective distance

# Wavenumber denominator: wn = f_mhz / WN_DENOM  [Algorithm]
WN_DENOM = 47.7

# InitializePointToPoint
GAMMA_A = 157e-9        # curvature of actual earth (~1/6370km)

# Variability
D_SCALE__meter = 100e3  # scale distance for sigma_S [Algorithm, Eqn 5.10]

# TroposcatterLoss
Z_0__meter = 1.7556e3   # scale height [Algorithm, 4.67]
Z_1__meter = 8.0e3      # [Algorithm, 4.67]
D_0__meter = 40e3       # troposcatter distance scale [Algorithm, 6.8]
TROPO_H__meter = 47.7   # height scale in troposcatter formula [Algorithm, 4.63]

# InitializeArea
H_3__meter = 5.0        # minimum effective height for horizon calc [Algorithm, Eqn 3.3]

# Warning bitmasks (matches Warnings.h)
WARN__TX_TERMINAL_HEIGHT     = 0x0001
WARN__RX_TERMINAL_HEIGHT     = 0x0002
WARN__FREQUENCY              = 0x0004
WARN__PATH_DISTANCE_TOO_BIG_1  = 0x0008
WARN__PATH_DISTANCE_TOO_BIG_2  = 0x0010
WARN__PATH_DISTANCE_TOO_SMALL_1 = 0x0020
WARN__PATH_DISTANCE_TOO_SMALL_2 = 0x0040
WARN__TX_HORIZON_ANGLE       = 0x0080
WARN__RX_HORIZON_ANGLE       = 0x0100
WARN__TX_HORIZON_DISTANCE_1  = 0x0200
WARN__RX_HORIZON_DISTANCE_1  = 0x0400
WARN__TX_HORIZON_DISTANCE_2  = 0x0800
WARN__RX_HORIZON_DISTANCE_2  = 0x1000
WARN__EXTREME_VARIABILITIES  = 0x2000
WARN__SURFACE_REFRACTIVITY   = 0x4000

# Internal mode flags (not public)
MODE__P2P   = 0
MODE__AREA  = 1
```

- [ ] **Step 4: Write `models.py`**

```python
# itm/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
import numpy as np


class Climate(IntEnum):
    EQUATORIAL = 1
    CONTINENTAL_SUBTROPICAL = 2
    MARITIME_SUBTROPICAL = 3
    DESERT = 4
    CONTINENTAL_TEMPERATE = 5
    MARITIME_TEMPERATE_LAND = 6
    MARITIME_TEMPERATE_SEA = 7


class Polarization(IntEnum):
    HORIZONTAL = 0
    VERTICAL = 1


class MDVar(IntEnum):
    SINGLE_MESSAGE = 0
    ACCIDENTAL = 1
    MOBILE = 2
    BROADCAST = 3


class PropMode(IntEnum):
    LINE_OF_SIGHT = 1
    DIFFRACTION = 2
    TROPOSCATTER = 3


class SitingCriteria(IntEnum):
    RANDOM = 0
    CAREFUL = 1
    VERY_CAREFUL = 2


@dataclass
class TerrainProfile:
    """Terrain elevation profile in PFL format."""
    elevations: np.ndarray  # elevation above sea level, meters; shape (np+1,)
    resolution: float       # point spacing, meters

    @classmethod
    def from_pfl(cls, pfl: list[float]) -> TerrainProfile:
        """Construct from raw C-style PFL array.

        pfl[0]   = number of elevation intervals (np), so np+1 points total
        pfl[1]   = resolution in meters
        pfl[2+]  = elevation values (np+1 values at pfl[2]..pfl[np+2])
        """
        np_ = int(pfl[0])
        resolution = float(pfl[1])
        elevations = np.array(pfl[2: np_ + 3], dtype=float)
        return cls(elevations=elevations, resolution=resolution)


@dataclass
class IntermediateValues:
    theta_hzn: tuple[float, float]      # terminal horizon angles, radians
    d_hzn__meter: tuple[float, float]   # terminal horizon distances, meters
    h_e__meter: tuple[float, float]     # effective terminal heights, meters
    N_s: float                          # surface refractivity, N-Units
    delta_h__meter: float               # terrain irregularity parameter, meters
    A_ref__db: float                    # reference attenuation, dB
    A_fs__db: float                     # free-space basic transmission loss, dB
    d__km: float                        # path distance, km
    mode: PropMode                      # propagation mode


@dataclass
class PropagationResult:
    A__db: float                                    # basic transmission loss, dB
    warnings: int                                   # warning bitmask
    intermediate: IntermediateValues | None = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add itm/_constants.py itm/models.py tests/test_models.py
git commit -m "feat: add constants, models, and enums"
```

---

## Task 3: Variability Helpers

**Files:**
- Write: `itm/variability.py` (helpers only: `iccdf`, `terrain_roughness`, `sigma_h_function`, `linear_least_squares_fit`, `curve`)
- Create: `tests/test_variability.py`

The `variability()` main function is added in Task 7 after propagation is complete.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_variability.py
import math
import numpy as np
from itm.variability import (
    iccdf, terrain_roughness, sigma_h_function,
    linear_least_squares_fit, curve,
)

def test_iccdf_known_values():
    # Q^-1(0.5) = 0.0 (median)
    assert math.isclose(iccdf(0.5), 0.0, abs_tol=1e-5)
    # Q^-1(0.1) ≈ 1.2816
    assert math.isclose(iccdf(0.1), 1.2816, abs_tol=1e-3)
    # Q^-1(0.9) ≈ -1.2816 (symmetric)
    assert math.isclose(iccdf(0.9), -1.2816, abs_tol=1e-3)

def test_terrain_roughness_zero_distance():
    # At d=0, factor = 1 - 0.8*exp(0) = 0.2
    assert math.isclose(terrain_roughness(0.0, 50.0), 50.0 * 0.2, rel_tol=1e-9)

def test_terrain_roughness_large_distance():
    # At large distance, approaches delta_h (factor → 1.0)
    assert math.isclose(terrain_roughness(1e9, 50.0), 50.0, rel_tol=1e-6)

def test_sigma_h_function():
    # sigma_h = 0.78 * delta_h * exp(-0.5 * delta_h^0.25)
    dh = 20.0
    expected = 0.78 * dh * math.exp(-0.5 * dh**0.25)
    assert math.isclose(sigma_h_function(dh), expected, rel_tol=1e-9)

def test_linear_least_squares_fit_flat():
    # Flat terrain: fit should return same value at both ends
    elevs = np.full(11, 100.0)  # 11 points, all at 100m
    fit_y1, fit_y2 = linear_least_squares_fit(elevs, 100.0, 0.0, 1000.0)
    assert math.isclose(fit_y1, 100.0, rel_tol=1e-6)
    assert math.isclose(fit_y2, 100.0, rel_tol=1e-6)

def test_linear_least_squares_fit_ramp():
    # Linear ramp from 0 to 1000m over 11 points, resolution=100
    elevs = np.linspace(0.0, 1000.0, 11)
    fit_y1, fit_y2 = linear_least_squares_fit(elevs, 100.0, 0.0, 1000.0)
    assert math.isclose(fit_y1, 0.0, abs_tol=1e-6)
    assert math.isclose(fit_y2, 1000.0, abs_tol=1e-6)

def test_curve_zero_distance():
    # At d_e=0, the factor d_e^2/(1+d_e^2) -> 0, so curve -> 0
    assert math.isclose(curve(1.0, 2.0, 100e3, 50e3, 30e3, 0.0), 0.0, abs_tol=1e-10)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_variability.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write the helper functions in `variability.py`**

```python
# itm/variability.py
from __future__ import annotations
import math
import numpy as np


def iccdf(q: float) -> float:
    """Inverse complementary CDF (Abramowitz & Stegun 26.2.23).
    
    Input q is a probability in (0, 1).
    Returns Q^-1(q): positive for q < 0.5, negative for q > 0.5.
    Error |epsilon(p)| < 4.5e-4.
    """
    C_0, C_1, C_2 = 2.515516, 0.802853, 0.010328
    D_1, D_2, D_3 = 1.432788, 0.189269, 0.001308

    x = q if q <= 0.5 else 1.0 - q
    T_x = math.sqrt(-2.0 * math.log(x))
    zeta_x = ((C_2 * T_x + C_1) * T_x + C_0) / (((D_3 * T_x + D_2) * T_x + D_1) * T_x + 1.0)
    Q_q = T_x - zeta_x
    return -Q_q if q > 0.5 else Q_q


def terrain_roughness(d__meter: float, delta_h__meter: float) -> float:
    """Compute delta_h_d: terrain roughness at distance d. [ERL 79-ITS 67, Eqn 3]"""
    return delta_h__meter * (1.0 - 0.8 * math.exp(-d__meter / 50e3))


def sigma_h_function(delta_h__meter: float) -> float:
    """RMS deviation of terrain within first Fresnel zone. [ERL 79-ITS 67, Eqn 3.6a]"""
    return 0.78 * delta_h__meter * math.exp(-0.5 * delta_h__meter**0.25)


def linear_least_squares_fit(
    elevations: np.ndarray,
    resolution: float,
    d_start: float,
    d_end: float,
) -> tuple[float, float]:
    """Fit a line to terrain elevations between d_start and d_end (in meters).

    elevations: 1-D array of elevation values, elevations[i] = height at index i.
                len(elevations) - 1 is the number of intervals (pfl[0]).
    resolution: spacing between elevation points in meters (pfl[1]).
    d_start, d_end: distance bounds in meters.

    Returns (fit_y1, fit_y2): fitted elevation at TX end and RX end respectively.
    """
    np_ = len(elevations) - 1  # number of intervals

    # fdim(x, y) = max(x - y, 0)
    i_start = int(max(d_start / resolution - 0.0, 0.0))
    i_end = np_ - int(max(np_ - d_end / resolution, 0.0))

    if i_end <= i_start:
        i_start = int(max(i_start - 1.0, 0.0))
        i_end = np_ - int(max(np_ - (i_end + 1.0), 0.0))

    x_length = float(i_end - i_start)
    mid_shifted_index = -0.5 * x_length
    mid_shifted_end = i_end + mid_shifted_index

    sum_y = 0.5 * (elevations[i_start] + elevations[i_end])
    scaled_sum_y = 0.5 * (elevations[i_start] - elevations[i_end]) * mid_shifted_index

    for i in range(2, int(x_length) + 1):
        i_start += 1
        mid_shifted_index += 1.0
        sum_y += elevations[i_start]
        scaled_sum_y += elevations[i_start] * mid_shifted_index

    sum_y /= x_length
    scaled_sum_y = scaled_sum_y * 12.0 / ((x_length * x_length + 2.0) * x_length)

    fit_y1 = sum_y - scaled_sum_y * mid_shifted_end
    fit_y2 = sum_y + scaled_sum_y * (np_ - mid_shifted_end)

    return fit_y1, fit_y2


def curve(
    c1: float, c2: float,
    x1: float, x2: float, x3: float,
    d_e__meter: float,
) -> float:
    """Curve helper for TN101v2 Eqn III.69 & III.70."""
    r = d_e__meter / x1
    return (c1 + c2 / (1.0 + ((d_e__meter - x2) / x3) ** 2)) * (r * r) / (1.0 + r * r)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_variability.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add itm/variability.py tests/test_variability.py
git commit -m "feat: add variability helper functions"
```

---

## Task 4: Terrain Module

**Files:**
- Write: `itm/terrain.py`
- Create: `tests/test_terrain.py`

Internal convention: `elevations[i]` corresponds to `pfl[i+2]` in the C++ code; `elevations[0]` is the TX-end elevation and `elevations[np_]` is the RX-end elevation.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_terrain.py
import math
import numpy as np
from itm.terrain import find_horizons, compute_delta_h, quick_pfl
from itm.models import TerrainProfile

def test_find_horizons_flat_earth():
    # Flat terrain at 0m, 2 terminals each 10m high, 10 km apart
    # With a_e = actual earth radius 6370e3:
    np_ = 10
    elevs = np.zeros(np_ + 1)
    h = (10.0, 10.0)
    a_e = 6370e3
    theta_hzn, d_hzn__meter = find_horizons(elevs, 1000.0, h, a_e)
    # Both horizons should be at full path distance (LOS condition)
    assert len(theta_hzn) == 2
    assert len(d_hzn__meter) == 2
    assert d_hzn__meter[0] == pytest.approx(10000.0, rel=1e-6)
    assert d_hzn__meter[1] == pytest.approx(10000.0, rel=1e-6)

def test_compute_delta_h_flat():
    # Flat terrain -> delta_h should be 0
    elevs = np.zeros(101)  # 100 intervals, resolution=100m, 10km path
    dh = compute_delta_h(elevs, 100.0, 1000.0, 9000.0)
    assert math.isclose(dh, 0.0, abs_tol=1e-6)

def test_quick_pfl_path_distance():
    # quick_pfl returns correct path distance
    np_ = 100
    elevs = np.zeros(np_ + 1)
    terrain = TerrainProfile(elevations=elevs, resolution=100.0)
    h = (10.0, 10.0)
    gamma_e = 1.0 / 6370e3
    theta_hzn, d_hzn, h_e, delta_h, d = quick_pfl(terrain, gamma_e, h)
    assert math.isclose(d, np_ * 100.0, rel_tol=1e-9)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_terrain.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Add `import pytest` to test file**

```python
# add at top of tests/test_terrain.py
import pytest
```

- [ ] **Step 4: Write `terrain.py`**

```python
# itm/terrain.py
from __future__ import annotations
import math
import numpy as np
from itm._constants import PI, H_3__meter
from itm.models import TerrainProfile
from itm.variability import linear_least_squares_fit


def find_horizons(
    elevations: np.ndarray,
    resolution: float,
    h__meter: tuple[float, float],
    a_e__meter: float,
) -> tuple[list[float], list[float]]:
    """Compute radio horizon angles and distances for both terminals.
    
    [TN101, Eq 6.15]
    Returns (theta_hzn[2], d_hzn__meter[2]).
    """
    np_ = len(elevations) - 1
    xi = resolution
    d__meter = np_ * xi

    z_tx = elevations[0] + h__meter[0]
    z_rx = elevations[np_] + h__meter[1]

    # Initial horizon angles assuming line-of-sight
    theta_hzn = [
        (z_rx - z_tx) / d__meter - d__meter / (2.0 * a_e__meter),
        -(z_rx - z_tx) / d__meter - d__meter / (2.0 * a_e__meter),
    ]
    d_hzn__meter = [d__meter, d__meter]

    d_tx__meter = 0.0
    d_rx__meter = d__meter

    for i in range(1, np_):
        d_tx__meter += xi
        d_rx__meter -= xi

        theta_tx = (elevations[i] - z_tx) / d_tx__meter - d_tx__meter / (2.0 * a_e__meter)
        theta_rx = -(z_rx - elevations[i]) / d_rx__meter - d_rx__meter / (2.0 * a_e__meter)

        if theta_tx > theta_hzn[0]:
            theta_hzn[0] = theta_tx
            d_hzn__meter[0] = d_tx__meter

        if theta_rx > theta_hzn[1]:
            theta_hzn[1] = theta_rx
            d_hzn__meter[1] = d_rx__meter

    return theta_hzn, d_hzn__meter


def compute_delta_h(
    elevations: np.ndarray,
    resolution: float,
    d_start__meter: float,
    d_end__meter: float,
) -> float:
    """Compute terrain irregularity parameter delta_h between d_start and d_end.
    
    Uses the inter-decile range of deviations from a linear fit. [ERL 79-ITS 67, Eqn 3]
    """
    np_ = len(elevations) - 1

    x_start_idx = d_start__meter / resolution
    x_end_idx = d_end__meter / resolution

    if x_end_idx - x_start_idx < 2.0:
        return 0.0

    p10 = int(0.1 * (x_end_idx - x_start_idx + 8.0))
    p10 = min(max(4, p10), 25)

    n = 10 * p10 - 5
    p90 = n - p10

    np_s = float(n - 1)
    x_step = (x_end_idx - x_start_idx) / np_s

    i = int(x_start_idx)
    x_pos = x_start_idx - float(i + 1)  # in range (-1, 0]

    s_elevations = []
    for _ in range(n):
        while x_pos > 0.0 and (i + 1) < np_:
            x_pos -= 1.0
            i += 1
        s_elevations.append(elevations[i + 1] + (elevations[i + 1] - elevations[i]) * x_pos)
        x_pos += x_step

    s_arr = np.array(s_elevations)

    # Fit a line to the resampled terrain (resolution=1.0, so d_start=0, d_end=np_s)
    fit_y1, fit_y2 = linear_least_squares_fit(s_arr, 1.0, 0.0, np_s)
    fit_slope = (fit_y2 - fit_y1) / np_s

    diffs = np.empty(n)
    current_fit = fit_y1
    for j in range(n):
        diffs[j] = s_elevations[j] - current_fit
        current_fit += fit_slope

    # q10: p10-th largest value (≈ 90th percentile)
    q10 = float(-np.partition(-diffs, p10 - 1)[p10 - 1])
    # q90: (p90+1)-th largest value (≈ 10th percentile)
    q90 = float(-np.partition(-diffs, p90)[p90])

    delta_h_d__meter = q10 - q90

    return delta_h_d__meter / (1.0 - 0.8 * math.exp(-(d_end__meter - d_start__meter) / 50e3))


def quick_pfl(
    terrain: TerrainProfile,
    gamma_e: float,
    h__meter: tuple[float, float],
) -> tuple[list[float], list[float], list[float], float, float]:
    """Extract path parameters from the terrain profile.
    
    Returns (theta_hzn[2], d_hzn__meter[2], h_e__meter[2], delta_h__meter, d__meter).
    """
    elevations = terrain.elevations
    resolution = terrain.resolution
    np_ = len(elevations) - 1

    d__meter = np_ * resolution
    a_e__meter = 1.0 / gamma_e

    theta_hzn, d_hzn__meter = find_horizons(elevations, resolution, h__meter, a_e__meter)

    # Start/end of terrain region to analyse (ignore ~15x tower height near each terminal)
    d_start__meter = min(15.0 * h__meter[0], 0.1 * d_hzn__meter[0])
    d_end__meter = d__meter - min(15.0 * h__meter[1], 0.1 * d_hzn__meter[1])

    delta_h__meter = compute_delta_h(elevations, resolution, d_start__meter, d_end__meter)

    h_e__meter = [0.0, 0.0]

    if d_hzn__meter[0] + d_hzn__meter[1] > 1.5 * d__meter:
        # Well within line-of-sight: use full-path linear fit
        fit_tx, fit_rx = linear_least_squares_fit(elevations, resolution, d_start__meter, d_end__meter)
        h_e__meter[0] = h__meter[0] + max(elevations[0] - fit_tx, 0.0)
        h_e__meter[1] = h__meter[1] + max(elevations[np_] - fit_rx, 0.0)

        for i in range(2):
            d_hzn__meter[i] = (
                math.sqrt(2.0 * h_e__meter[i] * a_e__meter)
                * math.exp(-0.07 * math.sqrt(delta_h__meter / max(h_e__meter[i], 5.0)))
            )

        if d_hzn__meter[0] + d_hzn__meter[1] <= d__meter:
            q = (d__meter / (d_hzn__meter[0] + d_hzn__meter[1])) ** 2
            for i in range(2):
                h_e__meter[i] *= q
                d_hzn__meter[i] = (
                    math.sqrt(2.0 * h_e__meter[i] * a_e__meter)
                    * math.exp(-0.07 * math.sqrt(delta_h__meter / max(h_e__meter[i], 5.0)))
                )

        for i in range(2):
            q = math.sqrt(2.0 * h_e__meter[i] * a_e__meter)
            theta_hzn[i] = (
                0.65 * delta_h__meter * (q / d_hzn__meter[i] - 1.0) - 2.0 * h_e__meter[i]
            ) / q
    else:
        # Beyond line-of-sight: fit near each terminal separately
        fit_tx, _ = linear_least_squares_fit(
            elevations, resolution, d_start__meter, 0.9 * d_hzn__meter[0]
        )
        h_e__meter[0] = h__meter[0] + max(elevations[0] - fit_tx, 0.0)

        _, fit_rx = linear_least_squares_fit(
            elevations, resolution, d__meter - 0.9 * d_hzn__meter[1], d_end__meter
        )
        h_e__meter[1] = h__meter[1] + max(elevations[np_] - fit_rx, 0.0)

    return theta_hzn, d_hzn__meter, h_e__meter, delta_h__meter, d__meter


def initialize_area(
    site_criteria: tuple[int, int],
    gamma_e: float,
    delta_h__meter: float,
    h__meter: tuple[float, float],
) -> tuple[list[float], list[float], list[float]]:
    """Initialize area mode: compute effective heights, horizon distances, horizon angles.
    
    Returns (h_e__meter[2], d_hzn__meter[2], theta_hzn[2]).
    """
    h_e__meter = [0.0, 0.0]
    d_hzn__meter = [0.0, 0.0]
    theta_hzn = [0.0, 0.0]

    for i in range(2):
        if site_criteria[i] == 0:  # RANDOM
            h_e__meter[i] = h__meter[i]
        else:
            B = 4.0 if site_criteria[i] == 1 else 9.0  # CAREFUL vs VERY_CAREFUL

            if h__meter[i] < 5.0:
                B = B * math.sin(0.1 * PI * h__meter[i])

            # [Algorithm, Eqn 3.2]
            h_e__meter[i] = h__meter[i] + (1.0 + B) * math.exp(
                -min(20.0, 2.0 * h__meter[i] / max(1e-3, delta_h__meter))
            )

        d_Ls__meter = math.sqrt(2.0 * h_e__meter[i] / gamma_e)

        # [Algorithm, Eqn 3.3]
        d_hzn__meter[i] = d_Ls__meter * math.exp(
            -0.07 * math.sqrt(delta_h__meter / max(h_e__meter[i], H_3__meter))
        )

        # [Algorithm, Eqn 3.4]
        theta_hzn[i] = (
            0.65 * delta_h__meter * (d_Ls__meter / d_hzn__meter[i] - 1.0)
            - 2.0 * h_e__meter[i]
        ) / d_Ls__meter

    return h_e__meter, d_hzn__meter, theta_hzn
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_terrain.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add itm/terrain.py tests/test_terrain.py
git commit -m "feat: add terrain module (find_horizons, compute_delta_h, quick_pfl, initialize_area)"
```

---

## Task 5: Propagation Helpers

**Files:**
- Write: `itm/propagation.py` (small helpers only, not `longley_rice`)
- Create: `tests/test_propagation.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_propagation.py
import math
import cmath
import pytest
from itm.propagation import (
    free_space_loss, fresnel_integral, height_function,
    h0_curve, h0_function, f_function,
    knife_edge_diffraction, smooth_earth_diffraction,
    troposcatter_loss, line_of_sight_loss, diffraction_loss,
    initialize_point_to_point,
)

def test_free_space_loss():
    # [Algorithm] A_fs = 32.45 + 20*log10(f_mhz) + 20*log10(d_km)
    # d=10000m=10km, f=100MHz: 32.45 + 20*2 + 20*1 = 32.45+40+20 = 92.45
    assert math.isclose(free_space_loss(10000.0, 100.0), 92.45, rel_tol=1e-5)

def test_fresnel_integral_below_threshold():
    # v2=1.0 < 5.76: 6.02 + 9.11*sqrt(1) - 1.27*1 = 6.02 + 9.11 - 1.27 = 13.86
    assert math.isclose(fresnel_integral(1.0), 13.86, rel_tol=1e-4)

def test_fresnel_integral_above_threshold():
    # v2=10.0 > 5.76: 12.953 + 10*log10(10) = 12.953 + 10 = 22.953
    assert math.isclose(fresnel_integral(10.0), 22.953, rel_tol=1e-4)

def test_h0_curve_known():
    # h0_curve(0, r=1.0): 10*log10(1 + 25*1 + 24*1) = 10*log10(50) ≈ 16.99
    assert math.isclose(h0_curve(0, 1.0), 10 * math.log10(50.0), rel_tol=1e-6)

def test_h0_function_clamps_eta():
    # eta_s < 1 should be clamped to 1 -> uses j=0 (i=1, q=0)
    result_low = h0_function(1.0, 0.5)
    result_one = h0_function(1.0, 1.0)
    # With eta_s clamped to 1 in h0_function, both should be equal
    assert math.isclose(result_low, result_one, rel_tol=1e-9)

def test_initialize_point_to_point_horizontal():
    Z_g, gamma_e, N_s = initialize_point_to_point(
        f__mhz=300.0, h_sys__meter=0.0, N_0=301.0,
        pol=0, epsilon=15.0, sigma=0.005
    )
    # N_s = N_0 when h_sys=0
    assert math.isclose(N_s, 301.0, rel_tol=1e-9)
    # gamma_e should be close to gamma_a * constant
    assert 1e-8 < gamma_e < 2e-7
    # Z_g should have positive real part
    assert Z_g.real > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_propagation.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `propagation.py`**

```python
# itm/propagation.py
from __future__ import annotations
import math
import cmath
import numpy as np
from itm._constants import (
    PI, SQRT2, THIRD, a_0__meter, WN_DENOM,
    GAMMA_A, Z_0__meter, Z_1__meter, D_0__meter, TROPO_H__meter,
    WARN__TX_HORIZON_ANGLE, WARN__RX_HORIZON_ANGLE,
    WARN__TX_HORIZON_DISTANCE_1, WARN__RX_HORIZON_DISTANCE_1,
    WARN__TX_HORIZON_DISTANCE_2, WARN__RX_HORIZON_DISTANCE_2,
    WARN__PATH_DISTANCE_TOO_SMALL_1, WARN__PATH_DISTANCE_TOO_SMALL_2,
    WARN__PATH_DISTANCE_TOO_BIG_1, WARN__PATH_DISTANCE_TOO_BIG_2,
    WARN__SURFACE_REFRACTIVITY, MODE__P2P,
)
from itm.models import PropMode
from itm.variability import terrain_roughness, sigma_h_function


def free_space_loss(d__meter: float, f__mhz: float) -> float:
    """Free space basic transmission loss. [Algorithm]"""
    return 32.45 + 20.0 * math.log10(f__mhz) + 20.0 * math.log10(d__meter / 1000.0)


def fresnel_integral(v2: float) -> float:
    """Approximate knife-edge diffraction loss. v2 is v^2. [TN101v2, Eqn III.24]"""
    if v2 < 5.76:
        return 6.02 + 9.11 * math.sqrt(v2) - 1.27 * v2
    else:
        return 12.953 + 10.0 * math.log10(v2)


def knife_edge_diffraction(
    d__meter: float,
    f__mhz: float,
    a_e__meter: float,
    theta_los: float,
    d_hzn__meter: list[float],
) -> float:
    """Knife-edge diffraction loss. [TN101, Eqn I.7 & I.1]"""
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]
    theta_nlos = d__meter / a_e__meter - theta_los
    d_nlos__meter = d__meter - d_ML__meter

    v_1 = 0.0795775 * (f__mhz / WN_DENOM) * theta_nlos**2 * d_hzn__meter[0] * d_nlos__meter / (d_nlos__meter + d_hzn__meter[0])
    v_2 = 0.0795775 * (f__mhz / WN_DENOM) * theta_nlos**2 * d_hzn__meter[1] * d_nlos__meter / (d_nlos__meter + d_hzn__meter[1])

    return fresnel_integral(v_1) + fresnel_integral(v_2)


def height_function(x__km: float, K: float) -> float:
    """Height gain function F(x, K) for smooth earth diffraction. [Vogler 1964]"""
    if x__km < 200.0:
        w = -math.log(K)
        if K < 1e-5 or x__km * w**3 > 5495.0:
            result = -117.0
            if x__km > 1.0:
                result = 17.372 * math.log(x__km) + result
        else:
            result = 2.5e-5 * x__km**2 / K - 8.686 * w - 15.0
    else:
        result = 0.05751 * x__km - 4.343 * math.log(x__km)
        if x__km < 2000.0:
            w = 0.0134 * x__km * math.exp(-0.005 * x__km)
            result = (1.0 - w) * result + w * (17.372 * math.log(x__km) - 117.0)
    return result


def smooth_earth_diffraction(
    d__meter: float,
    f__mhz: float,
    a_e__meter: float,
    theta_los: float,
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    Z_g: complex,
) -> float:
    """Smooth earth diffraction loss using the Vogler 3-radii method. [Vogler 1964]"""
    theta_nlos = d__meter / a_e__meter - theta_los
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]

    # 3 radii [Vogler 1964, Eqn 3 re-arranged]
    a__meter = [
        (d__meter - d_ML__meter) / (d__meter / a_e__meter - theta_los),
        0.5 * d_hzn__meter[0]**2 / h_e__meter[0],
        0.5 * d_hzn__meter[1]**2 / h_e__meter[1],
    ]
    d__km_vogler = [
        a__meter[0] * theta_nlos / 1000.0,
        d_hzn__meter[0] / 1000.0,
        d_hzn__meter[1] / 1000.0,
    ]

    C_0 = [pow((4.0 / 3.0) * a_0__meter / a__meter[i], THIRD) for i in range(3)]
    # [Vogler 1964, Eqn 6a / 7a]
    K = [0.017778 * C_0[i] * pow(f__mhz, -THIRD) / abs(Z_g) for i in range(3)]
    B_0 = [1.607 - K[i] for i in range(3)]

    x__km = [0.0, 0.0, 0.0]
    x__km[1] = B_0[1] * C_0[1]**2 * f__mhz**THIRD * d__km_vogler[1]
    x__km[2] = B_0[2] * C_0[2]**2 * f__mhz**THIRD * d__km_vogler[2]
    x__km[0] = B_0[0] * C_0[0]**2 * f__mhz**THIRD * d__km_vogler[0] + x__km[1] + x__km[2]

    F_x = [height_function(x__km[1], K[1]), height_function(x__km[2], K[2])]

    G_x__db = 0.05751 * x__km[0] - 10.0 * math.log10(x__km[0])

    return G_x__db - F_x[0] - F_x[1] - 20.0


def h0_curve(j: int, r: float) -> float:
    """Curve fit helper for H_0(). [Algorithm, 6.13]"""
    a = [25.0, 80.0, 177.0, 395.0, 705.0]
    b = [24.0, 45.0,  68.0,  80.0, 105.0]
    return 10.0 * math.log10(1.0 + a[j] * (1.0 / r)**4 + b[j] * (1.0 / r)**2)


def h0_function(r: float, eta_s: float) -> float:
    """Troposcatter frequency gain H_0(). [TN101v1, Ch 9.2]"""
    eta_s = min(max(eta_s, 1.0), 5.0)
    i = int(eta_s)
    q = eta_s - i
    result = h0_curve(i - 1, r)
    if q != 0.0:
        result = (1.0 - q) * result + q * h0_curve(i, r)
    return result


def f_function(td: float) -> float:
    """Attenuation function F(theta*d). [Algorithm, 6.9]"""
    a = [133.4, 104.6, 71.8]
    b = [0.332e-3, 0.212e-3, 0.157e-3]
    c = [-10.0, -2.5, 5.0]
    if td <= 10e3:
        i = 0
    elif td <= 70e3:
        i = 1
    else:
        i = 2
    return a[i] + b[i] * td + c[i] * math.log10(td)


def troposcatter_loss(
    d__meter: float,
    theta_hzn: list[float],
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    a_e__meter: float,
    N_s: float,
    f__mhz: float,
    theta_los: float,
    h0: float,
) -> tuple[float, float]:
    """Compute troposcatter loss and updated h0 value.
    
    Returns (A_scat__db, h0_updated).
    Returns (1001.0, h0) when path geometry makes troposcatter undefined.
    """
    wn = f__mhz / WN_DENOM

    if h0 > 15.0:
        H_0 = h0
    else:
        ad = d_hzn__meter[0] - d_hzn__meter[1]
        rr = h_e__meter[1] / h_e__meter[0]

        if ad < 0.0:
            ad = -ad
            rr = 1.0 / rr

        theta = theta_hzn[0] + theta_hzn[1] + d__meter / a_e__meter

        r_1 = 2.0 * wn * theta * h_e__meter[0]
        r_2 = 2.0 * wn * theta * h_e__meter[1]

        if r_1 < 0.2 and r_2 < 0.2:
            return 1001.0, h0

        s = (d__meter - ad) / (d__meter + ad)
        q = min(max(0.1, rr / s), 10.0)
        s = max(0.1, s)

        h_0__meter = (d__meter - ad) * (d__meter + ad) * theta * 0.25 / d__meter

        eta_s = (h_0__meter / Z_0__meter) * (
            1.0 + (0.031 - N_s * 2.32e-3 + N_s**2 * 5.67e-6)
            * math.exp(-pow(min(1.7, h_0__meter / Z_1__meter), 6))
        )

        H_00 = (h0_function(r_1, eta_s) + h0_function(r_2, eta_s)) / 2.0
        Delta_H_0 = min(H_00, 6.0 * (0.6 - math.log10(max(eta_s, 1.0))) * math.log10(s) * math.log10(q))

        H_0 = max(H_00 + Delta_H_0, 0.0)

        if eta_s < 1.0:
            H_0 = (eta_s * H_0
                   + (1.0 - eta_s) * 10.0 * math.log10(
                       ((1.0 + SQRT2 / r_1) * (1.0 + SQRT2 / r_2))**2
                       * (r_1 + r_2) / (r_1 + r_2 + 2.0 * SQRT2)
                   ))

        if H_0 > 15.0 and h0 >= 0.0:
            H_0 = h0

    h0_updated = H_0
    th = d__meter / a_e__meter - theta_los

    result = (
        f_function(th * d__meter)
        + 10.0 * math.log10(wn * TROPO_H__meter * th**4)
        - 0.1 * (N_s - 301.0) * math.exp(-th * d__meter / D_0__meter)
        + H_0
    )
    return result, h0_updated


def line_of_sight_loss(
    d__meter: float,
    h_e__meter: list[float],
    Z_g: complex,
    delta_h__meter: float,
    M_d: float,
    A_d0: float,
    d_sML__meter: float,
    f__mhz: float,
) -> float:
    """Loss in the line-of-sight region. [Algorithm, Eqn 4.46-4.50]"""
    delta_h_d__meter = terrain_roughness(d__meter, delta_h__meter)
    sigma_h_d__meter = sigma_h_function(delta_h_d__meter)

    wn = f__mhz / WN_DENOM

    sin_psi = (h_e__meter[0] + h_e__meter[1]) / math.sqrt(
        d__meter**2 + (h_e__meter[0] + h_e__meter[1])**2
    )

    R_e = (
        (sin_psi - Z_g) / (sin_psi + Z_g)
        * cmath.exp(-min(10.0, wn * sigma_h_d__meter * sin_psi))
    )

    q = R_e.real**2 + R_e.imag**2
    if q < 0.25 or q < sin_psi:
        R_e = R_e * math.sqrt(sin_psi / q)

    delta_phi = wn * 2.0 * h_e__meter[0] * h_e__meter[1] / d__meter
    if delta_phi > PI / 2.0:
        delta_phi = PI - (PI / 2.0)**2 / delta_phi

    rr = complex(math.cos(delta_phi), -math.sin(delta_phi)) + R_e
    A_t__db = -10.0 * math.log10(rr.real**2 + rr.imag**2)

    A_d__db = M_d * d__meter + A_d0
    w = 1.0 / (1.0 + f__mhz * delta_h__meter / max(10e3, d_sML__meter))

    return w * A_t__db + (1.0 - w) * A_d__db


def diffraction_loss(
    d__meter: float,
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    Z_g: complex,
    a_e__meter: float,
    delta_h__meter: float,
    h__meter: tuple[float, float],
    mode: int,
    theta_los: float,
    d_sML__meter: float,
    f__mhz: float,
) -> float:
    """Combined diffraction loss (knife-edge + smooth earth + terrain clutter).
    
    [ERL 79-ITS 67, Eqn 3.23 & 3.38c]
    """
    A_k__db = knife_edge_diffraction(d__meter, f__mhz, a_e__meter, theta_los, d_hzn__meter)
    A_se__db = smooth_earth_diffraction(d__meter, f__mhz, a_e__meter, theta_los, d_hzn__meter, h_e__meter, Z_g)

    delta_h_dsML__meter = terrain_roughness(d_sML__meter, delta_h__meter)
    sigma_h_d__meter = sigma_h_function(delta_h_dsML__meter)

    # Clutter factor [ERL 79-ITS 67, Eqn 3.38c]
    A_fo__db = min(15.0, 5.0 * math.log10(1.0 + 1e-5 * h__meter[0] * h__meter[1] * f__mhz * sigma_h_d__meter))

    delta_h_d__meter = terrain_roughness(d__meter, delta_h__meter)
    q = h__meter[0] * h__meter[1]
    qk = h_e__meter[0] * h_e__meter[1] - q

    if mode == MODE__P2P:
        q += 10.0  # C ≈ 10 for low antennas with known path [ERL 79-ITS 67, page 3-8]

    term1 = math.sqrt(1.0 + qk / q)
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]
    q = (term1 + (-theta_los * a_e__meter + d_ML__meter) / d__meter) * min(
        delta_h_d__meter * f__mhz / WN_DENOM, 6283.2
    )
    w = 25.1 / (25.1 + math.sqrt(q))

    return w * A_se__db + (1.0 - w) * A_k__db + A_fo__db


def initialize_point_to_point(
    f__mhz: float,
    h_sys__meter: float,
    N_0: float,
    pol: int,
    epsilon: float,
    sigma: float,
) -> tuple[complex, float, float]:
    """Compute ground impedance, effective earth curvature, surface refractivity.
    
    Returns (Z_g, gamma_e, N_s).
    """
    if h_sys__meter == 0.0:
        N_s = N_0
    else:
        N_s = N_0 * math.exp(-h_sys__meter / 9460.0)  # [TN101, Eq 4.3]

    gamma_e = GAMMA_A * (1.0 - 0.04665 * math.exp(N_s / 179.3))  # [TN101, Eq 4.4] reworked

    ep_r = complex(epsilon, 18000.0 * sigma / f__mhz)
    Z_g = cmath.sqrt(ep_r - 1.0)

    if pol == 1:  # VERTICAL
        Z_g = Z_g / ep_r

    return Z_g, gamma_e, N_s


def longley_rice(
    theta_hzn: list[float],
    f__mhz: float,
    Z_g: complex,
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    gamma_e: float,
    N_s: float,
    delta_h__meter: float,
    h__meter: tuple[float, float],
    d__meter: float,
    mode: int,
) -> tuple[float, int, PropMode]:
    """Core Longley-Rice reference attenuation computation.
    
    Returns (A_ref__db, warnings_bits, propmode).
    Raises ValueError for invalid computed parameters (surface refractivity,
    effective earth radius, ground impedance).
    """
    warnings = 0
    a_e__meter = 1.0 / gamma_e

    d_hzn_s__meter = [math.sqrt(2.0 * h_e__meter[i] * a_e__meter) for i in range(2)]
    d_sML__meter = d_hzn_s__meter[0] + d_hzn_s__meter[1]
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]

    theta_los = -max(theta_hzn[0] + theta_hzn[1], -d_ML__meter / a_e__meter)

    # Horizon angle warnings
    if math.fabs(theta_hzn[0]) > 200e-3:
        warnings |= WARN__TX_HORIZON_ANGLE
    if math.fabs(theta_hzn[1]) > 200e-3:
        warnings |= WARN__RX_HORIZON_ANGLE

    # Horizon distance warnings
    if d_hzn__meter[0] < 0.1 * d_hzn_s__meter[0]:
        warnings |= WARN__TX_HORIZON_DISTANCE_1
    if d_hzn__meter[1] < 0.1 * d_hzn_s__meter[1]:
        warnings |= WARN__RX_HORIZON_DISTANCE_1
    if d_hzn__meter[0] > 3.0 * d_hzn_s__meter[0]:
        warnings |= WARN__TX_HORIZON_DISTANCE_2
    if d_hzn__meter[1] > 3.0 * d_hzn_s__meter[1]:
        warnings |= WARN__RX_HORIZON_DISTANCE_2

    if N_s < 150:
        raise ValueError(f"Surface refractivity N_s={N_s:.1f} is too small (< 150)")
    if N_s > 400:
        raise ValueError(f"Surface refractivity N_s={N_s:.1f} is too large (> 400)")
    if N_s < 250:
        warnings |= WARN__SURFACE_REFRACTIVITY

    if a_e__meter < 4_000_000 or a_e__meter > 13_333_333:
        raise ValueError(f"Effective earth radius a_e={a_e__meter:.0f} m is out of range")

    if Z_g.real <= abs(Z_g.imag):
        raise ValueError("Ground impedance: real part must exceed imaginary part magnitude")

    # Two reference distances in the diffraction region
    d_diff_step = 10.0 * pow(a_e__meter**2 / f__mhz, 1.0 / 3.0)
    d_3__meter = max(d_sML__meter, d_ML__meter + 0.5 * d_diff_step)
    d_4__meter = d_3__meter + d_diff_step

    A_3__db = diffraction_loss(d_3__meter, d_hzn__meter, h_e__meter, Z_g, a_e__meter, delta_h__meter, h__meter, mode, theta_los, d_sML__meter, f__mhz)
    A_4__db = diffraction_loss(d_4__meter, d_hzn__meter, h_e__meter, Z_g, a_e__meter, delta_h__meter, h__meter, mode, theta_los, d_sML__meter, f__mhz)

    M_d = (A_4__db - A_3__db) / (d_4__meter - d_3__meter)
    A_d0__db = A_3__db - M_d * d_3__meter

    d_min__meter = math.fabs(h_e__meter[0] - h_e__meter[1]) / 200e-3

    if d__meter < d_min__meter:
        warnings |= WARN__PATH_DISTANCE_TOO_SMALL_1
    if d__meter < 1e3:
        warnings |= WARN__PATH_DISTANCE_TOO_SMALL_2
    if d__meter > 1000e3:
        warnings |= WARN__PATH_DISTANCE_TOO_BIG_1
    if d__meter > 2000e3:
        warnings |= WARN__PATH_DISTANCE_TOO_BIG_2

    if d__meter < d_sML__meter:
        # Line-of-sight path
        A_sML__db = d_sML__meter * M_d + A_d0__db
        d_0__meter = 0.04 * f__mhz * h_e__meter[0] * h_e__meter[1]

        if A_d0__db >= 0.0:
            d_0__meter = min(d_0__meter, 0.5 * d_ML__meter)
            d_1__meter = d_0__meter + 0.25 * (d_ML__meter - d_0__meter)
        else:
            d_1__meter = max(-A_d0__db / M_d, 0.25 * d_ML__meter)

        A_1__db = line_of_sight_loss(d_1__meter, h_e__meter, Z_g, delta_h__meter, M_d, A_d0__db, d_sML__meter, f__mhz)

        flag = False
        kHat_1 = 0.0
        kHat_2 = 0.0

        if d_0__meter < d_1__meter:
            A_0__db = line_of_sight_loss(d_0__meter, h_e__meter, Z_g, delta_h__meter, M_d, A_d0__db, d_sML__meter, f__mhz)
            q = math.log(d_sML__meter / d_0__meter)
            kHat_2 = max(0.0, (
                (d_sML__meter - d_0__meter) * (A_1__db - A_0__db)
                - (d_1__meter - d_0__meter) * (A_sML__db - A_0__db)
            ) / (
                (d_sML__meter - d_0__meter) * math.log(d_1__meter / d_0__meter)
                - (d_1__meter - d_0__meter) * q
            ))
            flag = A_d0__db > 0.0 or kHat_2 > 0.0

            if flag:
                kHat_1 = (A_sML__db - A_0__db - kHat_2 * q) / (d_sML__meter - d_0__meter)
                if kHat_1 < 0.0:
                    kHat_1 = 0.0
                    kHat_2 = max(A_sML__db - A_0__db, 0.0) / q
                    if kHat_2 == 0.0:
                        kHat_1 = M_d

        if not flag:
            kHat_1 = max(A_sML__db - A_1__db, 0.0) / (d_sML__meter - d_1__meter)
            kHat_2 = 0.0
            if kHat_1 == 0.0:
                kHat_1 = M_d

        A_o__db = A_sML__db - kHat_1 * d_sML__meter - kHat_2 * math.log(d_sML__meter)
        A_ref__db = A_o__db + kHat_1 * d__meter + kHat_2 * math.log(d__meter)
        propmode = PropMode.LINE_OF_SIGHT
    else:
        # Trans-horizon path
        d_5__meter = d_ML__meter + 200e3
        d_6__meter = d_ML__meter + 400e3

        h0 = -1.0
        A_6__db, h0 = troposcatter_loss(d_6__meter, theta_hzn, d_hzn__meter, h_e__meter, a_e__meter, N_s, f__mhz, theta_los, h0)
        A_5__db, h0 = troposcatter_loss(d_5__meter, theta_hzn, d_hzn__meter, h_e__meter, a_e__meter, N_s, f__mhz, theta_los, h0)

        if A_5__db < 1000.0:
            M_s = (A_6__db - A_5__db) / 200e3
            d_x__meter = max(
                max(d_sML__meter, d_ML__meter + 1.088 * pow(a_e__meter**2 / f__mhz, 1.0 / 3.0) * math.log(f__mhz)),
                (A_5__db - A_d0__db - M_s * d_5__meter) / (M_d - M_s),
            )
            A_s0__db = (M_d - M_s) * d_x__meter + A_d0__db
        else:
            M_s = M_d
            A_s0__db = A_d0__db
            d_x__meter = 10e6

        if d__meter > d_x__meter:
            A_ref__db = M_s * d__meter + A_s0__db
            propmode = PropMode.TROPOSCATTER
        else:
            A_ref__db = M_d * d__meter + A_d0__db
            propmode = PropMode.DIFFRACTION

    A_ref__db = max(A_ref__db, 0.0)
    return A_ref__db, warnings, propmode
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_propagation.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add itm/propagation.py tests/test_propagation.py
git commit -m "feat: add propagation module (all helpers + longley_rice)"
```

---

## Task 6: Variability Main Function

**Files:**
- Extend: `itm/variability.py` (add `variability()`)
- Extend: `tests/test_variability.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_variability.py
from itm.variability import variability
from itm.models import Climate, MDVar
from itm._constants import WARN__EXTREME_VARIABILITIES

def test_variability_returns_float_and_warnings():
    # Sanity check: result is a float, warnings is an int
    result, warns = variability(
        time=50.0, location=50.0, situation=50.0,
        h_e__meter=[10.0, 10.0],
        delta_h__meter=0.0,
        f__mhz=100.0,
        d__meter=50e3,
        A_ref__db=80.0,
        climate=Climate.CONTINENTAL_TEMPERATE,
        mdvar=MDVar.BROADCAST,
    )
    assert isinstance(result, float)
    assert isinstance(warns, int)

def test_variability_extreme_warns():
    # time=0.1 → z_T ≈ 3.09, close to limit → should trigger WARN__EXTREME_VARIABILITIES
    _, warns = variability(
        time=0.2, location=50.0, situation=50.0,
        h_e__meter=[10.0, 10.0],
        delta_h__meter=0.0,
        f__mhz=100.0,
        d__meter=50e3,
        A_ref__db=80.0,
        climate=Climate.CONTINENTAL_TEMPERATE,
        mdvar=MDVar.BROADCAST,
    )
    assert warns & WARN__EXTREME_VARIABILITIES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_variability.py::test_variability_returns_float_and_warnings -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Append `variability()` to `itm/variability.py`**

```python
# append to itm/variability.py
from itm._constants import a_9000__meter, WN_DENOM, THIRD, D_SCALE__meter, WARN__EXTREME_VARIABILITIES
from itm.models import Climate, MDVar


def variability(
    time: float,
    location: float,
    situation: float,
    h_e__meter: list[float],
    delta_h__meter: float,
    f__mhz: float,
    d__meter: float,
    A_ref__db: float,
    climate: Climate | int,
    mdvar: int,
) -> tuple[float, int]:
    """Compute variability loss adjustment.

    time, location, situation are percentages 0 < x < 100.
    Returns (F_db, warnings_bits).
    """
    # Asymptotic curve-fit parameters per climate [TN101, Fig 10.13 → TN101v2 III.69 & III.70]
    all_year = [
        [ -9.67,   -0.62,    1.26,   -9.21,   -0.62,   -0.39,      3.15 ],
        [ 12.7,     9.19,   15.5,     9.05,    9.19,    2.86,   857.9   ],
        [144.9e3, 228.9e3, 262.6e3,  84.1e3, 228.9e3, 141.7e3,2222.e3  ],
        [190.3e3, 205.2e3, 185.2e3, 101.1e3, 205.2e3, 315.9e3, 164.8e3 ],
        [133.8e3, 143.6e3,  99.8e3,  98.6e3, 143.6e3, 167.4e3, 116.3e3 ],
    ]
    bsm1 = [ 2.13,   2.66,   6.11,   1.98,  2.68,   6.86,   8.51 ]
    bsm2 = [159.5,   7.67,   6.65,  13.11,  7.16,  10.38, 169.8  ]
    xsm1 = [762.2e3,100.4e3,138.2e3,139.1e3, 93.7e3,187.8e3,609.8e3]
    xsm2 = [123.6e3,172.5e3,242.2e3,132.7e3,186.8e3,169.6e3,119.9e3]
    xsm3 = [ 94.5e3,136.4e3,178.6e3,193.5e3,133.5e3,108.9e3,106.6e3]
    bsp1 = [ 2.11,  6.87, 10.08,  3.68,  4.75,  8.58,  8.43 ]
    bsp2 = [102.3,  15.53,  9.60,159.3,   8.12, 13.97,  8.19 ]
    xsp1 = [636.9e3,138.7e3,165.3e3,464.4e3, 93.2e3,216.0e3,136.2e3]
    xsp2 = [134.8e3,143.7e3,225.7e3, 93.1e3,135.9e3,152.0e3,188.5e3]
    xsp3 = [ 95.6e3, 98.6e3,129.7e3, 94.2e3,113.4e3,122.7e3,122.9e3]
    C_D  = [1.224, 0.801, 1.380, 1.000, 1.224, 1.518, 1.518]
    z_D  = [1.282, 2.161, 1.282,  20.0, 1.282, 1.282, 1.282]
    bfm1 = [1.0,  1.0,  1.0,  1.0,  0.92, 1.0,  1.0 ]
    bfm2 = [0.0,  0.0,  0.0,  0.0,  0.25, 0.0,  0.0 ]
    bfm3 = [0.0,  0.0,  0.0,  0.0,  1.77, 0.0,  0.0 ]
    bfp1 = [1.0,  0.93, 1.0,  0.93, 0.93, 1.0,  1.0 ]
    bfp2 = [0.0,  0.31, 0.0,  0.19, 0.31, 0.0,  0.0 ]
    bfp3 = [0.0,  2.00, 0.0,  1.79, 2.00, 0.0,  0.0 ]

    z_T = iccdf(time / 100.0)
    z_L = iccdf(location / 100.0)
    z_S = iccdf(situation / 100.0)

    ci = int(climate) - 1  # 0-based climate index

    wn = f__mhz / WN_DENOM

    # Effective distance [Algorithm, Eqn 5.3]
    d_ex__meter = (
        math.sqrt(2 * a_9000__meter * h_e__meter[0])
        + math.sqrt(2 * a_9000__meter * h_e__meter[1])
        + pow(575.7e12 / wn, THIRD)
    )
    d_e__meter = (
        130e3 * d__meter / d_ex__meter
        if d__meter < d_ex__meter
        else 130e3 + d__meter - d_ex__meter
    )

    warnings = 0
    mdvar_internal = mdvar

    # +20 modifier: eliminate direct situation variability
    plus20 = mdvar_internal >= 20
    if plus20:
        mdvar_internal -= 20

    sigma_S = 0.0 if plus20 else 5.0 + 3.0 * math.exp(-d_e__meter / D_SCALE__meter)

    # +10 modifier: eliminate location variability
    plus10 = mdvar_internal >= 10
    if plus10:
        mdvar_internal -= 10

    V_med__db = curve(
        all_year[0][ci], all_year[1][ci],
        all_year[2][ci], all_year[3][ci], all_year[4][ci],
        d_e__meter,
    )

    SINGLE_MESSAGE, ACCIDENTAL, MOBILE = 0, 1, 2
    if mdvar_internal == SINGLE_MESSAGE:
        z_T = z_S
        z_L = z_S
    elif mdvar_internal == ACCIDENTAL:
        z_L = z_S
    elif mdvar_internal == MOBILE:
        z_L = z_T
    # else BROADCAST: no change

    if math.fabs(z_T) > 3.10 or math.fabs(z_L) > 3.10 or math.fabs(z_S) > 3.10:
        warnings |= WARN__EXTREME_VARIABILITIES

    # Location variability
    sigma_L = 0.0
    if not plus10:
        delta_h_d__meter = terrain_roughness(d__meter, delta_h__meter)
        sigma_L = 10.0 * wn * delta_h_d__meter / (wn * delta_h_d__meter + 13.0)
    Y_L = sigma_L * z_L

    # Time variability
    q = math.log(0.133 * wn)
    g_minus = bfm1[ci] + bfm2[ci] / (pow(bfm3[ci] * q, 2) + 1.0)
    g_plus  = bfp1[ci] + bfp2[ci] / (pow(bfp3[ci] * q, 2) + 1.0)

    sigma_T_minus = curve(bsm1[ci], bsm2[ci], xsm1[ci], xsm2[ci], xsm3[ci], d_e__meter) * g_minus
    sigma_T_plus  = curve(bsp1[ci], bsp2[ci], xsp1[ci], xsp2[ci], xsp3[ci], d_e__meter) * g_plus

    sigma_TD = C_D[ci] * sigma_T_plus
    tgtd = (sigma_T_plus - sigma_TD) * z_D[ci]

    if z_T < 0.0:
        sigma_T = sigma_T_minus
    elif z_T <= z_D[ci]:
        sigma_T = sigma_T_plus
    else:
        sigma_T = sigma_TD + tgtd / z_T
    Y_T = sigma_T * z_T

    Y_S_temp = (
        sigma_S**2
        + Y_T**2 / (7.8 + z_S**2)
        + Y_L**2 / (24.0 + z_S**2)
    )

    if mdvar_internal == SINGLE_MESSAGE:
        Y_R = 0.0
        Y_S = math.sqrt(sigma_T**2 + sigma_L**2 + Y_S_temp) * z_S
    elif mdvar_internal == ACCIDENTAL:
        Y_R = Y_T
        Y_S = math.sqrt(sigma_L**2 + Y_S_temp) * z_S
    elif mdvar_internal == MOBILE:
        Y_R = math.sqrt(sigma_T**2 + sigma_L**2) * z_T
        Y_S = math.sqrt(Y_S_temp) * z_S
    else:  # BROADCAST
        Y_R = Y_T + Y_L
        Y_S = math.sqrt(Y_S_temp) * z_S

    result = A_ref__db - V_med__db - Y_R - Y_S

    # [Algorithm, Eqn 52] — compress large negative losses
    if result < 0.0:
        result = result * (29.0 - result) / (29.0 - 10.0 * result)

    return result, warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_variability.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add itm/variability.py tests/test_variability.py
git commit -m "feat: add variability main function"
```

---

## Task 7: Entry Points

**Files:**
- Write: `itm/itm.py`
- Write: `itm/__init__.py`
- Create: `tests/test_itm.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_itm.py
import pytest
import numpy as np
from itm import predict_p2p, predict_area
from itm.models import (
    Climate, Polarization, MDVar, SitingCriteria,
    TerrainProfile, PropagationResult,
)

def make_flat_terrain(n=100, resolution=100.0, elevation=0.0):
    elevs = np.full(n + 1, elevation)
    return TerrainProfile(elevations=elevs, resolution=resolution)

def test_predict_p2p_returns_result():
    terrain = make_flat_terrain()
    result = predict_p2p(
        h_tx__meter=10.0, h_rx__meter=1.0,
        terrain=terrain,
        climate=Climate.CONTINENTAL_TEMPERATE,
        N_0=301.0, f__mhz=230.0,
        pol=Polarization.VERTICAL,
        epsilon=15.0, sigma=0.008,
        mdvar=12,
        time=50.0, location=17.0, situation=23.0,
    )
    assert isinstance(result, PropagationResult)
    assert isinstance(result.A__db, float)
    assert result.intermediate is None

def test_predict_p2p_intermediate_values():
    terrain = make_flat_terrain()
    result = predict_p2p(
        h_tx__meter=10.0, h_rx__meter=1.0,
        terrain=terrain,
        climate=Climate.CONTINENTAL_TEMPERATE,
        N_0=301.0, f__mhz=230.0,
        pol=Polarization.VERTICAL,
        epsilon=15.0, sigma=0.008,
        mdvar=12,
        time=50.0, location=17.0, situation=23.0,
        return_intermediate=True,
    )
    assert result.intermediate is not None
    assert result.intermediate.d__km == pytest.approx(10.0, rel=1e-3)

def test_predict_p2p_invalid_height():
    terrain = make_flat_terrain()
    with pytest.raises(ValueError, match="h_tx"):
        predict_p2p(
            h_tx__meter=0.1,  # below minimum 0.5m
            h_rx__meter=1.0,
            terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE,
            N_0=301.0, f__mhz=230.0,
            pol=Polarization.VERTICAL,
            epsilon=15.0, sigma=0.008,
            mdvar=12,
            time=50.0, location=50.0, situation=50.0,
        )

def test_predict_area_returns_result():
    result = predict_area(
        h_tx__meter=10.0, h_rx__meter=1.0,
        tx_siting=SitingCriteria.RANDOM, rx_siting=SitingCriteria.RANDOM,
        d__km=16.0, delta_h__meter=0.0,
        climate=Climate.CONTINENTAL_TEMPERATE,
        N_0=301.0, f__mhz=230.0,
        pol=Polarization.HORIZONTAL,
        epsilon=15.0, sigma=0.008,
        mdvar=0,
        time=87.0, location=50.0, situation=50.0,
    )
    assert isinstance(result, PropagationResult)
    assert result.A__db > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_itm.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `itm/itm.py`**

```python
# itm/itm.py
from __future__ import annotations
import math
from itm._constants import (
    WARN__TX_TERMINAL_HEIGHT, WARN__RX_TERMINAL_HEIGHT, WARN__FREQUENCY,
    MODE__P2P, MODE__AREA,
)
from itm.models import (
    Climate, Polarization, MDVar, PropMode, SitingCriteria,
    TerrainProfile, IntermediateValues, PropagationResult,
)
from itm.terrain import quick_pfl, initialize_area
from itm.propagation import initialize_point_to_point, longley_rice, free_space_loss
from itm.variability import variability


def _validate_inputs(
    h_tx__meter: float,
    h_rx__meter: float,
    climate: int,
    time: float,
    location: float,
    situation: float,
    N_0: float,
    f__mhz: float,
    pol: int,
    epsilon: float,
    sigma: float,
    mdvar: int,
) -> int:
    """Validate common inputs. Returns initial warnings bitmask. Raises ValueError on error."""
    warnings = 0

    if h_tx__meter < 0.5 or h_tx__meter > 3000.0:
        raise ValueError(f"h_tx__meter={h_tx__meter} out of range [0.5, 3000]")
    if h_tx__meter < 1.0 or h_tx__meter > 1000.0:
        warnings |= WARN__TX_TERMINAL_HEIGHT

    if h_rx__meter < 0.5 or h_rx__meter > 3000.0:
        raise ValueError(f"h_rx__meter={h_rx__meter} out of range [0.5, 3000]")
    if h_rx__meter < 1.0 or h_rx__meter > 1000.0:
        warnings |= WARN__RX_TERMINAL_HEIGHT

    valid_climates = {1, 2, 3, 4, 5, 6, 7}
    if int(climate) not in valid_climates:
        raise ValueError(f"climate={climate} is not a valid Climate value (1-7)")

    if N_0 < 250 or N_0 > 400:
        raise ValueError(f"N_0={N_0} out of range [250, 400]")

    if f__mhz < 20 or f__mhz > 20000:
        raise ValueError(f"f__mhz={f__mhz} out of range [20, 20000]")
    if f__mhz < 40.0 or f__mhz > 10000.0:
        warnings |= WARN__FREQUENCY

    if int(pol) not in (0, 1):
        raise ValueError(f"pol={pol} must be 0 (HORIZONTAL) or 1 (VERTICAL)")

    if epsilon < 1:
        raise ValueError(f"epsilon={epsilon} must be >= 1")

    if sigma <= 0:
        raise ValueError(f"sigma={sigma} must be > 0")

    valid_mdvar = set(range(0, 4)) | set(range(10, 14)) | set(range(20, 24)) | set(range(30, 34))
    if int(mdvar) not in valid_mdvar:
        raise ValueError(f"mdvar={mdvar} is not valid (0-3, 10-13, 20-23, 30-33)")

    if situation <= 0 or situation >= 100:
        raise ValueError(f"situation={situation} must be in (0, 100)")
    if time <= 0 or time >= 100:
        raise ValueError(f"time={time} must be in (0, 100)")
    if location <= 0 or location >= 100:
        raise ValueError(f"location={location} must be in (0, 100)")

    return warnings


def predict_p2p(
    h_tx__meter: float,
    h_rx__meter: float,
    terrain: TerrainProfile,
    climate: Climate,
    N_0: float,
    f__mhz: float,
    pol: Polarization,
    epsilon: float,
    sigma: float,
    mdvar: int,
    time: float,
    location: float,
    situation: float,
    *,
    return_intermediate: bool = False,
) -> PropagationResult:
    """Point-to-point propagation prediction.

    time, location, situation: percentages in (0, 100).
    mdvar: 0-3 base + optional +10 (no location var) and/or +20 (no situation var).
    """
    warnings = _validate_inputs(
        h_tx__meter, h_rx__meter, int(climate),
        time, location, situation,
        N_0, f__mhz, int(pol), epsilon, sigma, int(mdvar),
    )

    np_ = len(terrain.elevations) - 1
    d_total__meter = np_ * terrain.resolution

    # Average path height (middle 80%) for surface refractivity scaling
    p10 = int(0.1 * np_)
    h_sys__meter = sum(terrain.elevations[p10: np_ - p10 + 1]) / (np_ - 2 * p10 + 1)

    Z_g, gamma_e, N_s = initialize_point_to_point(f__mhz, h_sys__meter, N_0, int(pol), epsilon, sigma)

    h__meter = (h_tx__meter, h_rx__meter)
    theta_hzn, d_hzn__meter, h_e__meter, delta_h__meter, d__meter = quick_pfl(terrain, gamma_e, h__meter)

    A_ref__db, lr_warnings, propmode = longley_rice(
        theta_hzn, f__mhz, Z_g, d_hzn__meter, h_e__meter,
        gamma_e, N_s, delta_h__meter, h__meter, d__meter, MODE__P2P,
    )
    warnings |= lr_warnings

    A_fs__db = free_space_loss(d__meter, f__mhz)

    var_db, var_warnings = variability(
        time, location, situation, h_e__meter, delta_h__meter,
        f__mhz, d__meter, A_ref__db, climate, int(mdvar),
    )
    warnings |= var_warnings

    A__db = var_db + A_fs__db

    inter = None
    if return_intermediate:
        inter = IntermediateValues(
            theta_hzn=(theta_hzn[0], theta_hzn[1]),
            d_hzn__meter=(d_hzn__meter[0], d_hzn__meter[1]),
            h_e__meter=(h_e__meter[0], h_e__meter[1]),
            N_s=N_s,
            delta_h__meter=delta_h__meter,
            A_ref__db=A_ref__db,
            A_fs__db=A_fs__db,
            d__km=d__meter / 1000.0,
            mode=propmode,
        )

    return PropagationResult(A__db=A__db, warnings=warnings, intermediate=inter)


def predict_area(
    h_tx__meter: float,
    h_rx__meter: float,
    tx_siting: SitingCriteria,
    rx_siting: SitingCriteria,
    d__km: float,
    delta_h__meter: float,
    climate: Climate,
    N_0: float,
    f__mhz: float,
    pol: Polarization,
    epsilon: float,
    sigma: float,
    mdvar: int,
    time: float,
    location: float,
    situation: float,
    *,
    return_intermediate: bool = False,
) -> PropagationResult:
    """Area-mode propagation prediction."""
    warnings = _validate_inputs(
        h_tx__meter, h_rx__meter, int(climate),
        time, location, situation,
        N_0, f__mhz, int(pol), epsilon, sigma, int(mdvar),
    )

    if d__km <= 0:
        raise ValueError(f"d__km={d__km} must be > 0")
    if delta_h__meter < 0:
        raise ValueError(f"delta_h__meter={delta_h__meter} must be >= 0")
    if int(tx_siting) not in (0, 1, 2):
        raise ValueError(f"tx_siting={tx_siting} is not a valid SitingCriteria")
    if int(rx_siting) not in (0, 1, 2):
        raise ValueError(f"rx_siting={rx_siting} is not a valid SitingCriteria")

    Z_g, gamma_e, N_s = initialize_point_to_point(f__mhz, 0.0, N_0, int(pol), epsilon, sigma)

    h__meter = (h_tx__meter, h_rx__meter)
    site_criteria = (int(tx_siting), int(rx_siting))
    h_e__meter, d_hzn__meter, theta_hzn = initialize_area(site_criteria, gamma_e, delta_h__meter, h__meter)

    d__meter = d__km * 1000.0
    A_ref__db, lr_warnings, propmode = longley_rice(
        theta_hzn, f__mhz, Z_g, d_hzn__meter, h_e__meter,
        gamma_e, N_s, delta_h__meter, h__meter, d__meter, MODE__AREA,
    )
    warnings |= lr_warnings

    A_fs__db = free_space_loss(d__meter, f__mhz)

    var_db, var_warnings = variability(
        time, location, situation, h_e__meter, delta_h__meter,
        f__mhz, d__meter, A_ref__db, climate, int(mdvar),
    )
    warnings |= var_warnings

    A__db = A_fs__db + var_db

    inter = None
    if return_intermediate:
        inter = IntermediateValues(
            theta_hzn=(theta_hzn[0], theta_hzn[1]),
            d_hzn__meter=(d_hzn__meter[0], d_hzn__meter[1]),
            h_e__meter=(h_e__meter[0], h_e__meter[1]),
            N_s=N_s,
            delta_h__meter=delta_h__meter,
            A_ref__db=A_ref__db,
            A_fs__db=A_fs__db,
            d__km=d__km,
            mode=propmode,
        )

    return PropagationResult(A__db=A__db, warnings=warnings, intermediate=inter)
```

- [ ] **Step 4: Write `itm/__init__.py`**

```python
# itm/__init__.py
from itm.itm import predict_p2p, predict_area
from itm.models import (
    Climate, Polarization, MDVar, PropMode, SitingCriteria,
    TerrainProfile, IntermediateValues, PropagationResult,
)

__all__ = [
    "predict_p2p",
    "predict_area",
    "Climate",
    "Polarization",
    "MDVar",
    "PropMode",
    "SitingCriteria",
    "TerrainProfile",
    "IntermediateValues",
    "PropagationResult",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_itm.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add itm/itm.py itm/__init__.py tests/test_itm.py
git commit -m "feat: add public entry points predict_p2p and predict_area"
```

---

## Task 8: Integration Tests — Point-to-Point

**Files:**
- Create: `tests/test_p2p.py`
- Reference data: `p2p.csv` (5 test cases), `pfls.csv` (5 terrain profiles, one per row)

- [ ] **Step 1: Write the test**

```python
# tests/test_p2p.py
"""
Validate predict_p2p against all reference cases in p2p.csv + pfls.csv.
Each row in p2p.csv corresponds to the same-numbered row in pfls.csv.
Tolerance: 0.01 dB.
"""
import csv
import pathlib
import pytest
from itm import predict_p2p, Climate, Polarization, TerrainProfile

ROOT = pathlib.Path(__file__).parent.parent  # repo root

def load_p2p_cases():
    cases = []
    with open(ROOT / "p2p.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append({k: float(v) for k, v in row.items()})
    return cases

def load_pfls():
    profiles = []
    with open(ROOT / "pfls.csv") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            vals = [float(v) for v in line.split(",")]
            profiles.append(TerrainProfile.from_pfl(vals))
    return profiles

P2P_CASES = load_p2p_cases()
PFL_PROFILES = load_pfls()

@pytest.mark.parametrize("idx", range(len(P2P_CASES)))
def test_p2p_reference(idx):
    c = P2P_CASES[idx]
    terrain = PFL_PROFILES[idx]
    result = predict_p2p(
        h_tx__meter=c["h_tx__meter"],
        h_rx__meter=c["h_rx__meter"],
        terrain=terrain,
        climate=Climate(int(c["climate"])),
        N_0=c["N_0"],
        f__mhz=c["f__mhz"],
        pol=Polarization(int(c["pol"])),
        epsilon=c["epsilon"],
        sigma=c["sigma"],
        mdvar=int(c["mdvar"]),
        time=c["time"],
        location=c["location"],
        situation=c["situation"],
    )
    assert result.A__db == pytest.approx(c["A__db"], abs=0.01), (
        f"Case {idx}: expected {c['A__db']:.2f} dB, got {result.A__db:.2f} dB"
    )
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_p2p.py -v`
Expected: 5 passed

If any fail, the output will show expected vs actual dB values to help trace which function has a numerical error.

- [ ] **Step 3: Commit**

```bash
git add tests/test_p2p.py
git commit -m "test: add p2p integration tests against reference CSV"
```

---

## Task 9: Integration Tests — Area Mode

**Files:**
- Create: `tests/test_area.py`
- Reference data: `area.csv` (5 test cases)

- [ ] **Step 1: Write the test**

```python
# tests/test_area.py
"""
Validate predict_area against all reference cases in area.csv.
Tolerance: 0.01 dB.
"""
import csv
import pathlib
import pytest
from itm import predict_area, Climate, Polarization, SitingCriteria

ROOT = pathlib.Path(__file__).parent.parent

def load_area_cases():
    cases = []
    with open(ROOT / "area.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append({k: float(v) for k, v in row.items()})
    return cases

AREA_CASES = load_area_cases()

@pytest.mark.parametrize("idx", range(len(AREA_CASES)))
def test_area_reference(idx):
    c = AREA_CASES[idx]
    result = predict_area(
        h_tx__meter=c["h_tx__meter"],
        h_rx__meter=c["h_rx__meter"],
        tx_siting=SitingCriteria(int(c["tx_siting_criteria"])),
        rx_siting=SitingCriteria(int(c["rx_siting_criteria"])),
        d__km=c["d__km"],
        delta_h__meter=c["delta_h__meter"],
        climate=Climate(int(c["climate"])),
        N_0=c["N_0"],
        f__mhz=c["f__mhz"],
        pol=Polarization(int(c["pol"])),
        epsilon=c["epsilon"],
        sigma=c["sigma"],
        mdvar=int(c["mdvar"]),
        time=c["time"],
        location=c["location"],
        situation=c["situation"],
    )
    assert result.A__db == pytest.approx(c["A__db"], abs=0.01), (
        f"Case {idx}: expected {c['A__db']:.2f} dB, got {result.A__db:.2f} dB"
    )
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_area.py -v`
Expected: 5 passed

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_area.py
git commit -m "test: add area mode integration tests against reference CSV"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Pure Python package, pip-installable | Task 1 |
| numpy allowed | Used in terrain.py (compute_delta_h) |
| `_constants.py` — named constants | Task 2 |
| `models.py` — enums + dataclasses | Task 2 |
| `terrain.py` — QuickPfl, FindHorizons, ComputeDeltaH, TerrainRoughness, SigmaH | Task 4 (TerrainRoughness/SigmaH in variability.py per spec) |
| `variability.py` — Variability, ICCDF, LinearLeastSquaresFit | Tasks 3 & 6 |
| `propagation.py` — all propagation functions | Task 5 |
| `itm.py` — predict_p2p, predict_area | Task 7 |
| `__init__.py` — re-exports | Task 7 |
| `abs()` bug fix → `math.fabs()` | longley_rice (Task 5) |
| Percent/fraction unified as 0-100 | variability divides by 100 (Task 6) |
| MAX/MIN/DIM macros → builtins | Used `max()`/`min()` throughout |
| Magic numbers → `_constants.py` | Task 2 |
| `ValueError` for invalid inputs | `_validate_inputs` (Task 7) |
| Warning bitmask in PropagationResult | All tasks propagate warnings |
| TerrainProfile.from_pfl() | Task 2 |
| test_p2p.py — all reference rows | Task 8 |
| test_area.py — all reference rows | Task 9 |
| test_terrain.py unit tests | Task 4 |
| test_variability.py unit tests | Tasks 3 & 6 |
| Tolerance ≤ 0.01 dB | Tasks 8 & 9 |
| CR (confidence/reliability) variants NOT exposed | No CR functions added |

**Note on TerrainRoughness / SigmaH placement:** The spec lists these in `terrain.py` but the design data flow shows they're called from both `variability.py` (in `Variability`) and `propagation.py` (in `LineOfSightLoss`, `DiffractionLoss`). To avoid a circular import, they live in `variability.py` and are imported into `propagation.py` from there — matching the plan above.

**Type consistency check:** `linear_least_squares_fit` signature used consistently across Task 3 and Task 4. `terrain_roughness` and `sigma_h_function` imported from `variability` in both `propagation.py` and the variability main function.

**d_3 formula note:** The C++ computes `d_3 = MAX(d_sML, d_ML + 5 * (a_e^2 / f)^(1/3))`. In the plan, Task 5 uses `d_3 = max(d_sML, d_ML + 0.5 * d_diff_step)` where `d_diff_step = 10 * (a_e^2/f)^(1/3)`. This gives `d_ML + 5*(a_e^2/f)^(1/3)`. ✓
