# Code Review: `pyitm` — Python Port of the ITS Irregular Terrain Model

## Summary

This is a well-structured Python port of the Longley-Rice / ITM radio propagation model. The code is mathematically faithful to the reference specification (TN101, ERL 79-ITS 67), correctly passes all reference test cases, and has a clean module decomposition. However, there are several issues ranging from a **potential runtime crash bug** to lint violations, type safety concerns, and maintainability items.

**All 35 tests pass. Ruff finds 0 errors in `itm/`, 19 errors in `tests/` (16 fixable unused imports + 3 import-ordering).**

---

## 🔴 Critical Issues

### 1. Potential `IndexError` in `h0_function` — `propagation.py:150-155`

```python
def h0_function(r: float, eta_s: float) -> float:
    eta_s = min(max(eta_s, 1.0), 5.0)
    i = int(eta_s)
    q = eta_s - i
    result = h0_curve(i - 1, r)       # i=5 → h0_curve(4, r) — OK
    if q != 0.0:
        result = (1.0 - q) * result + q * h0_curve(i, r)  # i=5 → h0_curve(5, r) — CRASH!
```

When `eta_s` is clamped to exactly `5.0` and `q` is not exactly zero due to floating-point representation (e.g., `eta_s = 5.0` but `5.0 - int(5.0) = 0.0` is fine in practice), this is safe. However, **if any upstream computation produces a value like `4.9999999999999` or `5.0000000000001`**, the behavior diverges:
- `4.9999...` → `i=4`, `q≈1.0`, calls `h0_curve(3)` and `h0_curve(4)` — valid
- `5.0` → `i=5`, `q=0.0`, calls `h0_curve(4)` — valid but different path
- If `eta_s` somehow exceeds `5.0` before clamping occurs (or clamping fails), `i=5` and `q≠0` → `h0_curve(5, r)` → **`IndexError`**

**Recommendation:** Add an explicit guard at the top of the interpolation branch:
```python
if q != 0.0 and i < 5:  # a, b arrays have 5 elements (indices 0-4)
    result = (1.0 - q) * result + q * h0_curve(i, r)
```
This matches the reference C++ behavior where the j index is bounded to 0–4.

### 2. Potential Division by Zero — `smooth_earth_diffraction`, `propagation.py:110-114`

```python
a__meter = [
    (d__meter - d_ML__meter) / (d__meter / a_e__meter - theta_los),
    0.5 * d_hzn__meter[0] ** 2 / h_e__meter[0],
    0.5 * d_hzn__meter[1] ** 2 / h_e__meter[1],
]
```

If `h_e__meter[0]` or `h_e__meter[1]` is zero (which can happen in area mode when `SitingCriteria.RANDOM` is used and the terminal height equals terrain height), this divides by zero. The first element can also produce division by zero if `d__meter / a_e__meter == theta_los`.

**Recommendation:** Add guards or document preconditions. At minimum, add `assert` statements or defensive checks:
```python
if h_e__meter[0] <= 0 or h_e__meter[1] <= 0:
    raise ValueError("Effective antenna heights must be positive for smooth earth diffraction")
```

### 3. Potential `math.log(0)` or `math.sqrt(negative)` in `iccdf` — `variability.py:16-32`

```python
x = q if q <= 0.5 else 1.0 - q
T_x = math.sqrt(-2.0 * math.log(x))
```

If `q` is exactly 0.0 or 1.0, `x` becomes 0.0 and `math.log(0)` raises `ValueError`. While input validation in `itm.py` checks `0 < time/location/situation < 100`, the `iccdf` function itself has no guard and is a public function.

**Recommendation:** Either document the `(0, 1)` domain precondition or add a guard:
```python
if q <= 0.0 or q >= 1.0:
    raise ValueError(f"iccdf requires 0 < q < 1, got {q}")
```

---

## 🟠 Significant Issues

### 4. Inconsistent Type Annotations — Throughout `itm/`

Many internal functions use `list[float]` for parameters that are semantically fixed-size tuples of 2:

```python
def longley_rice(
    theta_hzn: list[float],     # always length 2
    d_hzn__meter: list[float],  # always length 2
    h_e__meter: list[float],    # always length 2
    ...
) -> tuple[float, int, PropMode]:
```

Using `list[float]` implies an arbitrary-length sequence. Since these are always 2-element pairs, `tuple[float, float]` would be more precise and catch accidental misuse.

**Recommendation:** Change type hints to `tuple[float, float]` for all 2-element pairs (theta_hzn, d_hzn__meter, h_e__meter, h__meter, site_criteria). This also makes `__init__.py`'s `IntermediateValues.theta_hzn` and `d_hzn__meter` types consistent with the dataclass definition.

### 5. Mutable Default Arguments Pattern — `quick_pfl` and `initialize_area` — `terrain.py:152, 208-210`

```python
h_e__meter = [0.0, 0.0]
d_hzn__meter = [0.0, 0.0]
theta_hzn = [0.0, 0.0]
```

These are mutable lists being created and returned. While no default-argument bug exists here (they're created fresh each call), this pattern makes the return types mutable when they shouldn't be. Functions return these lists, and callers could accidentally mutate them.

**Recommendation:** Return `tuple[float, float]` instead of `list[float]` for these 2-element results. This also aligns with the `IntermediateValues` dataclass which stores `theta_hzn` as `tuple[float, float]`.

### 6. Missing `ruff` Dev Dependency in CI — `.github/workflows/ci.yml:38-39`

The CI pipeline installs `ruff` separately (`pip install ruff`) rather than using the project's dev dependencies:

```yaml
- name: Install linting tools
  run: pip install ruff
```

Meanwhile `pyproject.toml` lists `ruff` in `dev` dependencies. The lint step should use `pip install -e ".[dev]"` like the test step, to ensure version consistency.

**Recommendation:**
```yaml
- name: Install dependencies
  run: pip install -e ".[dev]"
- name: Lint
  run: ruff check itm/
```

### 7. Unused Imports in Test Files

Ruff reports 16 unused imports across test files:

| File | Unused imports |
|------|---------------|
| `test_itm.py:8` | `MDVar` |
| `test_models.py:2` | `numpy` |
| `test_models.py:5-10` | `Polarization`, `MDVar`, `PropMode`, `SitingCriteria`, `IntermediateValues` |
| `test_propagation.py:3` | `cmath` |
| `test_propagation.py:4` | `pytest` |
| `test_propagation.py:8-16` | `height_function`, `f_function`, `knife_edge_diffraction`, `smooth_earth_diffraction`, `troposcatter_loss`, `line_of_sight_loss`, `diffraction_loss` |

**Recommendation:** Remove unused imports with `ruff check --fix tests/`.

### 8. E402 Module-Level Import Not at Top — `test_variability.py:60-62`

Three imports are placed after test functions:

```python
def test_curve_zero_distance():
    ...

from itm.variability import variability
from itm.models import Climate, MDVar
from itm._constants import WARN__EXTREME_VARIABILITIES
```

**Recommendation:** Move these to the top of the file alongside the other imports.

---

## 🟡 Minor Issues

### 9. `TerrainProfile.from_pfl` Docstring Mismatch — `models.py:50-56`

The docstring says:
```
pfl[2+]  = elevation values (np+1 values at pfl[2]..pfl[np+2])
```

But `np_ + 3` in the slice `pfl[2 : np_ + 3]` produces `np_ + 1` elements (indices 2 through `np_+2`). The test confirms this:
```python
pfl = [3.0, 100.0, 10.0, 20.0, 15.0, 25.0, 12.0]
# np=3, expects 4 elevation values: indices 2..4 → [10, 20, 15, 25]
```

Wait — `np_=3`, so `pfl[2:3+3] = pfl[2:6]` gives elements at indices 2, 3, 4, 5 → `[10, 20, 15, 25]` — that's 4 elements = `np_+1`. Correct, but the docstring says "elevation values (np+1 values at pfl[2]..pfl[np+2])" which means indices 2 through `np_+2 = 5`, i.e., 4 elements. This is actually correct.

However, the `pfl` array in the test has 7 elements. That means `pfl[6] = 12.0` is unused. If this is intentional (trailing data), document it; otherwise, it may confuse readers.

### 10. `__init__.py` — Missing Exports — `itm/__init__.py`

The `__init__.py` does not export several publicly-used symbols:
- `_constants` module: `WARN__*` flags are imported directly in test files from `itm._constants`, but these aren't in `__all__`. This is fine for internal use but inconsistent.
- `longley_rice`, `quick_pfl`, `initialize_area`, etc. are internal but have no `_` prefix convention.

**Recommendation:** Either add a `_` prefix to truly internal functions (`_longley_rice`, `_quick_pfl`) or explicitly document that they are internal/unstable.

### 11. Floating-Point Comparison with `q != 0.0` — `propagation.py:153`

```python
if q != 0.0:
    result = (1.0 - q) * result + q * h0_curve(i, r)
```

Exact comparison to `0.0` with floats is fragile. If `eta_s` is computed as (say) `3.0000000000000004`, then `q = 4e-16 ≠ 0.0`, which causes interpolation to run — potentially fine numerically, but the intent was to skip interpolation only for exact integers.

**Recommendation:** Use a tolerance: `if q > 1e-10:` or document that this matches the reference implementation's exact comparison behavior.

### 12. No `__slots__` on Dataclasses — `models.py`

`TerrainProfile`, `IntermediateValues`, and `PropagationResult` are `@dataclass` without `slots=True`. For performance-critical code processing many terrain points, this adds memory overhead.

**Recommendation:** For Python 3.10+, add `slots=True`:
```python
@dataclass(slots=True)
class TerrainProfile:
    ...
```

### 13. Hardcoded Magic Numbers — `propagation.py`, `variability.py`

Several magic numbers appear without explanation:
- `0.0795775` in `knife_edge_diffraction` (line 59) — likely `1 / (4 * pi)`
- `0.65` in `quick_pfl` and `initialize_area` — terrain factor
- `0.04665` and `9460.0` in `initialize_point_to_point`
- `575.7e12`, `130e3`, `47.7`, `0.133` in `variability()`

The constants module (`_constants.py`) was created to extract some magic numbers, but these remain inline.

**Recommendation:** Either extract remaining magic numbers to `_constants.py` with named constants (e.g., `INV_4PI = 0.0795775`) or add inline comments with their mathematical meaning. The `0.0795775` is particularly inscrutable without a comment noting it's `1/(4π) * (1/M)` for some `M`.

### 14. No Type Checking Configuration — `pyproject.toml`

There's no `mypy` or `pyright` configuration. Given the numerical nature of this code, type checking would catch subtle bugs like passing `list[float]` where `float` is expected.

**Recommendation:** Add `mypy` or `pyright` to dev dependencies and CI:
```toml
[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]
```

### 15. Test Coverage Gaps

There are no tests for:
- **Edge cases** in `smooth_earth_diffraction`, `diffraction_loss`, `troposcatter_loss`, `line_of_sight_loss` — the most complex functions
- **Error paths** in `longley_rice` (e.g., invalid `N_s`, `a_e__meter`, `Z_g`)
- **Warning generation** (all 14 warning bits are untested)
- **Area mode intermediate values**
- **`predict_p2p` / `predict_area` with non-flat terrain profiles**

The `test_propagation.py` file imports but never tests `height_function`, `f_function`, `knife_edge_diffraction`, `smooth_earth_diffraction`, `troposcatter_loss`, `line_of_sight_loss`, or `diffraction_loss`.

**Recommendation:** Add unit tests for at minimum the warning paths and the untested propagation functions with constructed inputs.

### 16. `build-backend` Mismatch — `pyproject.toml:3`

The plan document specifies `setuptools.backends.legacy:build` but the actual file uses `setuptools.build_meta`:

```toml
build-backend = "setuptools.build_meta"  # actual
build-backend = "setuptools.backends.legacy:build"  # in plan
```

The actual file is correct; the plan document is outdated. No action needed, but worth noting.

### 17. `pfl` Parsing: No Bounds Validation — `models.py:50-60`

`TerrainProfile.from_pfl()` does not validate that the pfl array has enough elements:

```python
np_ = int(pfl[0])
resolution = float(pfl[1])
elevations = np.array(pfl[2 : np_ + 3], dtype=float)
```

If `pfl` has fewer than `np_ + 3` elements, this silently produces a shorter array, leading to cryptic downstream errors.

**Recommendation:** Add validation:
```python
if len(pfl) < np_ + 3:
    raise ValueError(f"PFL array has {len(pfl)} elements, expected at least {np_ + 3}")
if np_ < 1:
    raise ValueError(f"PFL interval count must be >= 1, got {np_}")
```

### 18. ~~No `__repr__` or `__str__` on `PropagationResult`~~ — `models.py`

The main result type has no human-readable representation. Debugging with `print(result)` yields unhelpful output like `PropagationResult(A__db=142.345, warnings=4, intermediate=None)`.

Actually, `@dataclass` auto-generates `__repr__`, so this is already available. Disregard.

### 19. `compute_delta_h` Comment Confusion — `terrain.py:112-115`

```python
# q10: p10-th largest value (≈ 90th percentile)
q10 = float(-np.partition(-diffs, p10 - 1)[p10 - 1])
# q90: (p90+1)-th largest value (≈ 10th percentile)
q90 = float(-np.partition(-diffs, p90)[p90])
```

The variable names `q10` and `q90` are misleading. `q10` is actually the *90th percentile* (the p10-th largest when sorted descending) and `q90` is the *10th percentile*. The comment uses "≈" which acknowledges this is approximate due to finite samples, but the variable names invert the convention.

**Recommendation:** Rename to `percentile_90` and `percentile_10`, or add a clarifying comment that `q10` means "the value at the q=0.10 quantile position in the sorted-descending array" to match the reference implementation naming.

---

## ✅ What's Done Well

1. **Clear module decomposition** — Constants, models, terrain, variability, propagation, and entry points are cleanly separated.
2. **Reference citations** — Equations are annotated with their source (TN101, ERL 79-ITS 67, Algorithm §, Vogler 1964).
3. **Physical unit annotations** — The `__meter`, `__km`, `__db` suffix convention makes units explicit and reduces interpretation errors.
4. **IntEnum for enums** — `Climate`, `Polarization`, etc. are `IntEnum`, which is correct for this domain where values must map to integers for the algorithm.
5. **Dataclass models** — Clean use of `@dataclass` for `TerrainProfile`, `IntermediateValues`, `PropagationResult`.
6. **Warning bitmask pattern** — Warnings accumulate as OR'd bitmasks, matching the C++ reference and allowing non-fatal issues.
7. **Test organization** — Reference validation tests (`test_p2p.py`, `test_area.py`) parametrize over CSV data, while unit tests cover individual functions.
8. **All tests pass** — 35/35 at 0.01 dB tolerance, matching the reference implementation.

---

## Priority Action Items

| Priority | Issue | Action |
|----------|-------|--------|
| 🔴 P0 | #1 | Guard `h0_function` interpolation branch against `i ≥ 5` |
| 🔴 P0 | #2 | Add precondition checks or documentation for division-by-zero in `smooth_earth_diffraction` |
| 🔴 P0 | #3 | Guard `iccdf` against `q ∈ {0, 1}` |
| 🟠 P1 | #4 | Change `list[float]` → `tuple[float, float]` for 2-element pairs |
| 🟠 P1 | #6 | Fix CI to use project dev dependencies for lint |
| 🟠 P1 | #7 | Clean up unused imports in tests |
| 🟠 P1 | #8 | Fix E402 import ordering in `test_variability.py` |
| 🟡 P2 | #5 | Return tuples instead of mutable lists |
| 🟡 P2 | #13 | Extract remaining magic numbers or add inline comments |
| 🟡 P2 | #15 | Add tests for warning paths and untested functions |
| 🟡 P2 | #17 | Add bounds validation to `TerrainProfile.from_pfl` |
| 🟡 P3 | #9, #11, #19 | Doc/comment improvements |
