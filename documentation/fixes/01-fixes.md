# Recommended Fixes

Derived from [`02-verification.md`](../code-review/02-verification.md). Ordered by effort/value. Each is a concrete change.

## Do now (low effort, real value)

1. ~~**Fix lint in tests** — `ruff check tests/ --fix` clears 16 F401s; manually move the 3 imports in [`test_variability.py:60-62`](../../tests/test_variability.py#L60-L62) to the top.~~ ✅ Done — 16 F401s auto-fixed, E402s resolved by moving imports to top of file.
2. ~~**CI: install dev extras for lint job** — [`.github/workflows/ci.yml:38-39`](../../.github/workflows/ci.yml#L38-L39): replace `pip install ruff` with `pip install -e ".[dev]"` and also `ruff check tests/`.~~ ✅ Done — lint job now uses `pip install -e ".[dev]"` and checks both `itm/` and `tests/`.
3. ~~**CI: Python version matrix** — test 3.10/3.11/3.12/3.13, since `pyproject.toml` declares `>=3.10`.~~ ✅ Done — test job runs a matrix across 3.10, 3.11, 3.12, 3.13.
4. ~~**Fix `test_models.py:22` comment** — change `(np+2 = 5 values)` to `(np+1 = 4 values; trailing 12.0 ignored)`, or drop the `12.0` from the fixture.~~ ✅ Done — comment corrected.
5. ~~**Add upper-clamp test for `h0_function`** — one line: `assert math.isclose(h0_function(1.0, 6.0), h0_function(1.0, 5.0), rel_tol=1e-9)`. Refutes prior review's #1 in code.~~ ✅ Done — added to `test_h0_function_clamps_eta` in [`test_propagation.py`](../../tests/test_propagation.py).

## Do soon (small fix, prevents real footguns)

6. ~~**Validate terrain size** in [`TerrainProfile.from_pfl`](../../itm/models.py#L49) and at the top of [`predict_p2p`](../../itm/itm.py#L87) — reject `np_ < 1` and `len(elevations) < 2` with a clear error instead of crashing deep in `linear_least_squares_fit`.~~ ✅ Done — `from_pfl` raises on `len(pfl) < 3` or `np_ < 1`; `predict_p2p` raises on `len(elevations) < 2`. Note: `len(pfl) < np_+3` was intentionally not enforced — reference PFL data legitimately has shorter arrays (numpy slicing handles this gracefully).
7. ~~**Use `.mean()` instead of `sum()`** at [`itm.py:126`](../../itm/itm.py#L126) — `float(terrain.elevations[p10:np_-p10+1].mean())`.~~ ✅ Done — incorporated alongside fix #6.

## Do when touching that code

8. ~~**Document preconditions** — one-line comments on `iccdf` (`q ∈ (0,1)`), `smooth_earth_diffraction` (`h_e[i] > 0`), `troposcatter_loss` (`h_e[0] > 0`). Avoids future "is this a bug?" reviews.~~ ✅ Done — precondition notes added to each function's docstring.
9. ~~**Add tests for warning bits** — at minimum `WARN__SURFACE_REFRACTIVITY`, `WARN__TX_HORIZON_*`, `WARN__PATH_DISTANCE_*`. Prior review item #15.~~ ✅ Done — added 6 new tests to [`test_itm.py`](../../tests/test_itm.py): `test_warn_terminal_height`, `test_warn_frequency`, `test_warn_surface_refractivity`, `test_warn_path_distance_too_big`, `test_warn_path_distance_too_small`, `test_predict_p2p_invalid_terrain`. Suite grows from 35 → 41 tests, all passing.

## Don't do

- **Don't** change `list[float]` → `tuple[float, float]` (prior review #4, #5). [`CLAUDE.md`](../../CLAUDE.md) says "Do not add type annotations to code you didn't author in this session."
- **Don't** add the `h0_function` "guard" from prior review #1 — it's defending against an impossible state and adds noise. The 1-line test in #5 above is the right defence.
- **Don't** add `__slots__`, mypy config, `_` prefixes, or `__version__` plumbing unless the project explicitly decides to. Prior review #10, #12, #14 are out of scope for a code review.
- **Don't** rename `q10`/`q90` (prior review #19) — they intentionally mirror the reference C++.

## Suggested commits

Three small commits keep history clean:

```
1. ci: lint tests, install dev extras, add Python matrix
2. test: fix test_models comment, test h0_function upper clamp
3. itm: validate terrain size, replace sum() with .mean()
```
