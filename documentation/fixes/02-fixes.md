# pyitm — Full Port Recommendations

**Date:** 2026-04-17  
**Based on:** Full read-only review against C++ reference (`itm/`)

---

## P0 — Correctness / Functional Gaps

### P0-A: Fix `TerrainProfile.from_pfl` length validation

**File:** `itm/models.py`

`from_pfl` reads `np_ = int(pfl[0])` but never checks `len(pfl) >= np_ + 3`. A short array produces a silently truncated `elevations` array, leading to wrong answers or an `IndexError` deep inside `quick_pfl`.

```python
@classmethod
def from_pfl(cls, pfl: Sequence[float]) -> "TerrainProfile":
    np_ = int(pfl[0])
    if len(pfl) < np_ + 3:
        raise ValueError(
            f"pfl declares {np_} intervals but only {len(pfl) - 2} elevation values provided"
        )
    resolution = float(pfl[1])
    elevations = np.asarray(pfl[2 : np_ + 3], dtype=float)  # exact slice
    return cls(elevations=elevations, resolution=resolution)
```

Also slice `pfl[2 : np_ + 3]` (not `pfl[2:]`) to discard any trailing garbage.

---

### P0-B: Implement CR API (`predict_p2p_cr` / `predict_area_cr`)

**File:** new function(s) in `itm/itm.py`, exported from `itm/__init__.py`

The C++ reference exposes `ITM_P2P_CR` and `ITM_AREA_CR`. These accept `confidence` and `reliability` percentages and map them to `time`/`location`/`situation` via a fixed transformation before calling the core model. Python only has TLS mode.

Minimum viable CR API:

```python
def predict_p2p_cr(
    ...,
    confidence: float,   # percent, (0, 100)
    reliability: float,  # percent, (0, 100)
) -> PropagationResult:
    # CR→TLS mapping per ITM algorithm doc
    return predict_p2p(..., time=reliability, location=confidence, situation=confidence, mdvar=1)
```

Verify exact mapping against `itm_p2p.cpp` `ITM_P2P_CR` before shipping.

---

## P1 — Test Coverage

### P1-A: `iccdf` edge cases

```python
def test_iccdf_symmetry():
    assert iccdf(0.1) == pytest.approx(-iccdf(0.9))

def test_iccdf_midpoint():
    assert iccdf(0.5) == pytest.approx(0.0, abs=1e-6)

def test_iccdf_domain_error():
    with pytest.raises((ValueError, Exception)):
        iccdf(0.0)
    with pytest.raises((ValueError, Exception)):
        iccdf(1.0)
```

### P1-B: Propagation primitive unit tests

Add direct tests for the functions that are currently exercised only indirectly:

- `knife_edge_diffraction(v)` — test at v=0, v=-0.7, v=+2
- `smooth_earth_diffraction(d, f, ...)` — smoke test with known inputs
- `troposcatter_loss(...)` — test the `r_1 < 0.2 && r_2 < 0.2` sentinel path (should return ~1001)
- `line_of_sight_loss(...)` — smoke test

### P1-C: MDVar branch coverage

`variability()` has four branches (BROADCAST=0, ACCIDENTAL=1, MOBILE=2, SINGLE_MESSAGE=3) plus `+10` and `+20` modifiers. Current tests only exercise the default path. Add parametrized tests for all four base modes and both modifiers.

### P1-D: Warning bit tests

Add a test that drives each warning bit individually and checks `result.warnings & WARN_X != 0`:
- `WARN__TX_TERMINAL_HEIGHT` — set `h_tx=0.6`
- `WARN__FREQUENCY` — set `f__mhz=25`
- `WARN__EXTREME_VARIABILITIES` — set time/location/situation to near-boundary values

### P1-E: `from_pfl` error path (P0-A prerequisite)

```python
def test_from_pfl_too_short():
    with pytest.raises(ValueError, match="elevation"):
        TerrainProfile.from_pfl([10, 100.0, 1.0, 2.0])  # only 2 points for 10 intervals
```

---

## P1 — API Quality

### P1-F: Freeze result dataclasses

```python
@dataclass(frozen=True)
class PropagationResult:
    A__db: float
    warnings: int
    intermediate: IntermediateValues | None = None
```

Same for `IntermediateValues`. Prevents callers from accidentally mutating results.

### P1-G: `IntFlag` for warnings

```python
from enum import IntFlag

class Warnings(IntFlag):
    TX_TERMINAL_HEIGHT   = 0x0001
    RX_TERMINAL_HEIGHT   = 0x0002
    FREQUENCY            = 0x0004
    PATH_DISTANCE_TOO_BIG_1  = 0x0008
    # ... etc.
    NONE = 0
```

Change `PropagationResult.warnings` to `Warnings`. Callers get `result.warnings & Warnings.FREQUENCY` and `repr` shows the flag names. Keep the raw `int` constants in `_constants.py` for internal use.

### P1-H: Tighten two-element tuple types

`h_e__meter`, `d_hzn__meter`, `theta_hzn` are all `list[float]` indexed as `[0]`/`[1]`. Change internal signatures to `tuple[float, float]` (or a small `NamedTuple`) so static analysis catches out-of-bounds indexing.

---

## P2 — Code Quality

### P2-A: Hoist coefficient arrays out of `variability()`

**File:** `itm/variability.py`

Move `all_year`, `bsm1`–`xsp3`, `C_D`, `z_D`, `bfm*`, `bfp*` to module-level `tuple` constants. Currently they are `list` literals rebuilt on every call.

```python
_ALL_YEAR = (
    (-9.67, -0.62, 1.26, -9.21, -0.62, -0.39, 3.15),
    ...
)
_BSM1 = (2.13, 2.66, 6.11, 1.98, 2.68, 6.86, 8.51)
# etc.
```

### P2-B: Remove `sigma_h_function` dead code

**File:** `itm/variability.py`

`sigma_h_function` is defined but never called. Either wire it into the algorithm where it belongs (RMS terrain deviation for first Fresnel zone) or delete it. If deleted, note the removal in CHANGELOG.

### P2-C: Use `math.exp` where arguments are real

**File:** `itm/propagation.py`

Several `cmath.exp(real_value)` calls return `complex` with zero imaginary part. Replace with `math.exp` where the argument is guaranteed real. Reduces unnecessary complex arithmetic overhead and makes the type flow clearer.

### P2-D: Add `iccdf` domain guard

**File:** `itm/variability.py`

```python
def iccdf(q: float) -> float:
    if not 0.0 < q < 1.0:
        raise ValueError(f"iccdf requires 0 < q < 1, got {q}")
    ...
```

---

## P2 — Performance

### P2-E: Vectorize `find_horizons`

**File:** `itm/terrain.py`

Current implementation is a pure Python loop over every terrain point — the hot path for long profiles.

```python
# TX side (simplified concept)
effective = elevations + cumulative_earth_curvature  # vectorized
slope_to_i = (effective - h_tx_abs) / distances     # vectorized
theta_tx = np.maximum.accumulate(slope_to_i[::-1])[::-1].max()
```

Exact implementation requires care to match the C++ horizon angle sign convention.

### P2-F: Vectorize `compute_delta_h`

**File:** `itm/terrain.py`

The `np.partition` call is already O(n). The surrounding loop building the sample array `s` can be replaced with a vectorized slice; the 10th/90th percentile extraction becomes two `np.partition` calls or a single `np.percentile`.

### P2-G: Vectorize `linear_least_squares_fit`

**File:** `itm/variability.py`

The accumulation loop is O(n) Python. Replace with:

```python
indices = np.arange(i_start, i_end + 1)
mid = indices - (i_start + i_end) / 2.0
sum_y = elevations[indices].mean()
scaled_sum_y = (elevations[indices] * mid).sum() * 12.0 / (x_length**2 + 2.0) / x_length
```

---

## P3 — Packaging & Docs

### P3-A: Add `itm.egg-info/` to `.gitignore`

The egg-info directory is build output and should not be committed.

```
# .gitignore additions
*.egg-info/
dist/
build/
__pycache__/
*.pyc
```

### P3-B: Export `__version__`

**File:** `itm/__init__.py`

```python
__version__ = "0.1.0"
```

Keep in sync with `pyproject.toml`. Consider using `importlib.metadata` for a single source of truth.

### P3-C: Add `py.typed` marker

Create an empty `itm/py.typed` file and add to `pyproject.toml`:

```toml
[tool.setuptools.package-data]
itm = ["py.typed"]
```

This tells mypy the package ships inline types.

### P3-D: Pin numpy floor

```toml
dependencies = ["numpy>=1.21"]
```

`numpy>=2.0` if you want to use the new array API. Without a floor, `pip` may resolve numpy 1.x on older environments where `np.partition` semantics differ subtly.

### P3-E: Rewrite `README.md`

Replace the NTIA C++ README (with strikethrough Visual Studio sections) with a Python-specific README covering:
- What ITM/Longley-Rice is (one paragraph)
- Installation: `pip install itm`
- Quick-start: `predict_p2p` and `predict_area` examples
- Parameter reference (point to docstrings)
- Running tests: `pytest`
- Link to upstream NTIA C++ reference

### P3-F: Reconcile `AGENTS.md` test count

`AGENTS.md` says "35 tests must pass" — now 41. Update to match `CLAUDE.md`.

---

## Priority Summary

| ID | Item | Priority | Effort |
|---|---|---|---|
| P0-A | `from_pfl` length validation | P0 | 30 min |
| P0-B | CR API | P0 | 2–3 h |
| P1-A–E | Test coverage gaps | P1 | 2 h |
| P1-F–H | API quality (frozen, IntFlag, tuple types) | P1 | 2 h |
| P2-A | Hoist coefficient arrays | P2 | 30 min |
| P2-B | Remove `sigma_h_function` dead code | P2 | 5 min |
| P2-C | `math.exp` for real args | P2 | 15 min |
| P2-D | `iccdf` domain guard | P2 | 10 min |
| P2-E–G | Vectorize hot paths | P2 perf | 3–4 h |
| P3-A–F | Packaging & docs | P3 | 2 h |
