# pyitm Port — Code Review

**Date:** 2026-04-17  
**Scope:** Full read-only review of `pyitm` against the C++ reference (`itm/`)  
**Test baseline:** 41 tests, all passing, 0.13 s

---

## Summary

The port is numerically faithful and well-structured. All critical algorithmic equivalences check out: `fdim` → `max(..., 0)`, `d_3`/`d_4` algebra in `longley_rice`, `np.partition` vs `std::nth_element` semantics, `h_sys` central-80% slice, and the `cmath` complex ground impedance path. Tolerance against the reference CSVs is ≤ 0.01 dB.

Two real issues stand out: a **latent crash bug** in `TerrainProfile.from_pfl` and a **missing public API** (CR mode). Everything else is quality/packaging work.

---

## File-by-File Notes

### `itm/models.py`

**Latent bug — `TerrainProfile.from_pfl` does not validate array length.**

```python
@classmethod
def from_pfl(cls, pfl: Sequence[float]) -> "TerrainProfile":
    np_ = int(pfl[0])
    resolution = float(pfl[1])
    elevations = np.asarray(pfl[2:], dtype=float)
    return cls(elevations=elevations, resolution=resolution)
```

If `len(pfl) < np_ + 3` the elevations array will be silently short, producing wrong answers or an IndexError deep inside `quick_pfl`. Fix: add `if len(pfl) < np_ + 3: raise ValueError(...)`.

**Minor: mutable defaults and no `__slots__`/`frozen`.** `TerrainProfile` and `IntermediateValues` are plain dataclasses. Making them `frozen=True` prevents accidental mutation of results; `PropagationResult` in particular should be immutable.

**Minor: `IntermediateValues` uses bare `tuple[float, float]` fields.** Caller must remember index 0 = TX, index 1 = RX. A two-field named sub-dataclass or a `NamedTuple` pair would be self-documenting.

**Minor: `MDVar` enum is unused internally.** `predict_p2p`/`predict_area` accept `int` and pass `int(mdvar)`. Either remove `MDVar` or thread it through the API.

**Minor: `warnings` on `PropagationResult` is a plain `int`.** Declaring it as `int` but meaning a bitmask is opaque. Consider `IntFlag` (see P1 section below).

---

### `itm/terrain.py`

**`linear_least_squares_fit` lives in `variability.py` but is imported by `terrain.py`.** Conceptually it belongs in `terrain.py` or a shared `_math.py`; the cross-module import is a layering surprise.

**`compute_delta_h` rebuilds a sorted copy on every call.** Uses `np.partition` for O(n) median extraction, which is correct. Could be vectorized further (see P2 perf below).

**`find_horizons` is a pure Python loop over every terrain point.** For long profiles this is the hot path. Vectorizable with `np.maximum.accumulate` (see P2 perf).

---

### `itm/variability.py`

**14 coefficient arrays are rebuilt on every call to `variability`.** `all_year`, `bsm1`–`xsp3`, `C_D`, `z_D`, `bfm*`, `bfp*` are `list` literals inside the function body. Move them to module-level `tuple` constants; saves allocation and makes the numeric data easier to audit.

**`sigma_h_function` is defined but never called.** Either wire it in or remove it.

**`iccdf` precondition is documented but not enforced.** `q=0` or `q=1` will raise `ValueError: math domain error` from `math.log(0)`. A deliberate `if not 0 < q < 1: raise ValueError(...)` gives a cleaner error message.

---

### `itm/propagation.py`

**`cmath.exp` vs `math.exp`.** Several intermediate values that are real (non-complex) use `cmath.exp`, returning a complex number with zero imaginary part. These are then implicitly cast back to float by arithmetic context. Explicit `math.exp` where the argument is real avoids the complex overhead and the implicit cast.

**`fresnel_integral` loop structure mirrors C exactly** — the port is correct but could be simplified with `sum()` or numpy; the loop is short (≤ 10 iterations) so it does not matter for performance.

**`TroposcatterLoss`: early-return guard.**  
C++: `if (r_1 < 0.2 && r_2 < 0.2) return 1001;`  
Python uses `1001.0` — correct, but worth a comment explaining this sentinel means "effectively no troposcatter contribution."

---

### `itm/itm.py`

**CR API is absent.** The C++ library exposes `ITM_P2P_CR` and `ITM_AREA_CR` variants that accept confidence/reliability percentages in place of time/location/situation. The Python port has only TLS mode. Users who need CR mode must re-derive the mapping manually. This is the largest functional gap vs. the reference.

**`_validate_inputs` raises `ValueError` while C++ returns typed error codes.** The Python choice is idiomatic and fine; just note it diverges from the C++ contract.

**`h_sys__meter` slice uses `terrain.elevations[p10 : np_ - p10 + 1].mean()`.** Cross-checked against `itm_p2p.cpp` — correct.

---

### `tests/`

**Coverage gaps vs. the reference test suite:**

| Area | Status |
|---|---|
| `predict_p2p` / `predict_area` integration | ✅ 41 tests, 0.01 dB |
| `iccdf` edge cases (q→0, q→1, q=0.5) | ❌ not tested |
| `knife_edge_diffraction` direct | ❌ not tested |
| `smooth_earth_diffraction` direct | ❌ not tested |
| `troposcatter_loss` direct | ❌ not tested |
| `line_of_sight_loss` direct | ❌ not tested |
| All 4 MDVar branches (0–3) exercised | ❌ only default path covered |
| `+10` / `+20` mdvar modifiers | ❌ not tested |
| Warning bits individually | ❌ only smoke-tested |
| `TerrainProfile.from_pfl` short array | ❌ bug not caught |

---

### `pyproject.toml` / packaging

- `itm.egg-info/` is committed to the repo — should be in `.gitignore`.
- No `__version__` attribute exported from `itm/__init__.py`.
- No `py.typed` marker — mypy treats the package as untyped.
- `numpy` dependency has no floor (`"numpy"`) — `>=1.21` or `>=2.0` would be safer.

---

### Documentation / meta

- `README.md` is still the upstream NTIA C++ README with strikethrough DLL/Visual Studio sections. Needs a Python-specific rewrite.
- `AGENTS.md` says "35 tests must pass" — stale, now 41.
- `CLAUDE.md` has correct test count (41) — `AGENTS.md` needs reconciliation.
- `CHANGELOG.md` is present and reasonably up to date.

---

## Risk Table

| Issue | Severity | Effort |
|---|---|---|
| `from_pfl` no length validation | Bug / silent wrong answer | Small |
| Missing CR API | Functional gap | Medium |
| Coefficient arrays rebuilt per call | Perf / readability | Small |
| `find_horizons` Python loop | Perf (long profiles) | Medium |
| `sigma_h_function` dead code | Cleanup | Trivial |
| `IntFlag` warnings | API quality | Small |
| Primitive unit test gaps | Test quality | Medium |
| egg-info committed | Packaging | Trivial |
| README stale | Docs | Small |
