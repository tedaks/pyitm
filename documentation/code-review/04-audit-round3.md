# Audit Round 3 — pyitm-ng

Date: 2026-10-06 (approximate)
Scope: what the differential test and existing validation cannot catch.

## Method

- Full test suite: 227 passed, 7 skipped (no C++ reference lib in default env).
- Differential with C++ reference (`ITM_DIFF_EXACT=1`): 7 passed.
- Targeted probes on inputs outside the differential's documented range
  (`resolution ∈ [1, 2000] m`, `d__km ∈ [0.001, 2000] km`, `delta_h__meter ∈ [0, 3000] m`).

## Findings

### F1 — `predict_area`: unbounded `delta_h__meter` causes `ZeroDivisionError` (Medium)

**Reproduce:**
```python
from pyitm_ng import predict_area
predict_area(
    h_tx__meter=10.0, h_rx__meter=2.0,
    tx_siting=0, rx_siting=0, d__km=50.0, delta_h__meter=1e9,
    climate=3, N_0=301.0, f__mhz=230.0, pol=1, epsilon=15.0, sigma=0.008,
    mdvar=12, time=50.0, location=50.0, situation=50.0,
)
# raises ZeroDivisionError: division by zero
#   at pyitm_ng/terrain.py:249  (initialize_area)
```

**Root cause chain:**

1. `predict_area` validates `delta_h__meter >= 0` but places **no upper bound** (`pyitm_ng/itm.py:273`). The C++ reference has no such check either — it simply computes with whatever value the caller passes.
2. In `initialize_area` (`pyitm_ng/terrain.py:212`), the horizon distance is:
   ```python
   d_hzn__meter[i] = d_Ls__meter * c_exp(
       -0.07 * c_sqrt(delta_h__meter / c_max(h_e__meter[i], H_3__meter))
   )
   ```
   For `delta_h__meter` large enough that `c_sqrt(delta_h__meter / h_e)` exceeds ~26.6, the exponent underflows: `c_exp(-x) → 0.0`, so `d_hzn__meter[i] = 0.0`.
3. In `smooth_earth_diffraction` (`pyitm_ng/propagation.py:100`), Vogler's three radii include:
   ```python
   a__meter[2] = 0.5 * sq(d_hzn__meter[1]) / h_e__meter[1]   # = 0.0 when d_hzn underflows
   C_0[2] = c_pow((4.0/3.0) * a_0__meter / a__meter[2], THIRD)  # division by zero → ZeroDivisionError
   ```
   `c_pow` does not guard against a zero divisor; the plain `/` in the numerator expression raises before `c_pow` is called.

**Threshold (measured):** with `h_tx=10 m`, `h_rx=2 m`, `d__km=50`, `f=230 MHz`:
- Last value that completes: `delta_h__meter ≈ 1.4768244667 × 10⁸`
- First value that raises: `delta_h__meter ≈ 1.4768244668 × 10⁸`

The threshold is input-dependent (it depends on `h_e`, `a_e`, and which of the three radii underflows first), so it cannot be expressed as a simple bound on `delta_h__meter` alone.

**Why the differential misses this:** `_area_cases` in `tests/test_differential.py` draws `delta_h__meter` from `[0, 3000]` m — four orders of magnitude below the threshold.

**Why the C++ doesn't crash:** in C, division by zero for `double` is IEEE-754: it produces `±inf` or `nan`, not an exception. The C++ carries on and returns a (meaningless) result. Python raises instead.

**Recommended fix (two options, pick one):**

*Option A — document the deviation and raise:*
Add to the "Deliberate deviations" list in `CLAUDE.md` / `AGENTS.md`:
> `predict_area` with `delta_h__meter` large enough that Vogler's third radius underflows to zero raises `ZeroDivisionError` (the C++ would return a meaningless result). The threshold is input-dependent and not documented.

And add a test in `tests/test_validation.py` that pins the behaviour:
```python
def test_extreme_delta_h_raises():
    with pytest.raises(ZeroDivisionError):
        predict_area(..., delta_h__meter=1e9, ...)
```

*Option B — clamp at the entry point:*
In `predict_area`, after the existing `delta_h__meter >= 0` check, add:
```python
if delta_h__meter > DELTA_H_MAX:
    raise ValueError(f"delta_h__meter={delta_h__meter} is too large (> {DELTA_H_MAX})")
```
where `DELTA_H_MAX` is a documented upper bound (e.g. 10⁶ m, well above any physically meaningful terrain irregularity). This requires choosing and documenting the constant.

Option A is consistent with the existing deviation policy (reject what the C++ would turn into a meaningless result). Option B changes the API contract.

---

### F2 — `predict_p2p`: extremely large profile distance returns a finite but meaningless `A__db` (Low)

**Reproduce:**
```python
import numpy as np
from pyitm_ng import TerrainProfile, predict_p2p
t = TerrainProfile(elevations=np.zeros(10), resolution=3e9)  # d ≈ 2.7×10¹⁰ m = 27 million km
r = predict_p2p(h_tx__meter=10.0, h_rx__meter=2.0, terrain=t,
                climate=3, N_0=301.0, f__mhz=230.0, pol=1,
                epsilon=15.0, sigma=0.008, mdvar=12,
                time=50.0, location=50.0, situation=50.0)
print(r.A__db)  # 5214464815.792534 — finite, no exception, no useful warning
```

**What happens:** `TerrainProfile` validates `resolution > 0` and finiteness but places **no upper bound on the total path distance** (`(len(elevations)-1) * resolution`). The C++ reference has the same gap: it computes with whatever distance the profile implies. For distances far beyond the model's physical range (~6000 km), the result is a large finite number with no warning bit set that would alert the caller.

**Severity: Low.** The input is physically absurd (27 million km on Earth). The C++ has the same behaviour. No crash, no wrong answer for any realistic input. Noting it for completeness; no fix recommended unless the project wants to add a `PATH_DISTANCE_TOO_BIG` warning at the profile level (the C++ sets such warnings for `d__km` in area mode but not for p2p distance derived from the profile).

---

### F3 — Stale build artifacts in working tree (Info)

`dist/pyitm_ng-0.3.0-py3-none-any.whl` and `dist/pyitm_ng-0.3.0.tar.gz` are present in the working tree but **gitignored** (`.gitignore:10`). The v0.3.0 release was reverted (`e6c4bb5`) because PyPI publishing is on hold; the CHANGELOG correctly keeps the 0.3.0 entries under `[Unreleased]`. The `dist/` files are a local build artifact and do not affect the repo or CI. No action needed; noting so a future auditor doesn't flag them.

---

### F4 — `documentation/todo.md`: antenna-gain item scope check (Info)

The "Antenna gain parameters in API" item in `documentation/todo.md` is unchecked and lists files `pyitm_ng/models.py`, `pyitm_ng/itm.py`. No such parameters exist in the current codebase (confirmed by grep). The item is accurately described as not-yet-done. No discrepancy found.

---

## Summary

| ID | Severity | File(s) | Issue |
|----|----------|---------|-------|
| F1 | Medium | `pyitm_ng/terrain.py:249`, `pyitm_ng/propagation.py:129`, `pyitm_ng/itm.py:273` | `predict_area` with `delta_h__meter ≳ 1.5×10⁸` m raises `ZeroDivisionError`; no upper bound on `delta_h__meter`; differential samples only up to 3000 m |
| F2 | Low | `pyitm_ng/models.py:110-127` | p2p path distance unbounded; extremely large profiles return finite meaningless `A__db` with no warning (same as C++) |
| F3 | Info | `dist/` | Stale 0.3.0 build artifacts, gitignored, harmless |
| F4 | Info | `documentation/todo.md` | Antenna-gain item correctly marked as not done |

**F1 is the only finding that warrants a code or documentation change before release.**
