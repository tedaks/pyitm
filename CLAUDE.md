# pyitm-ng — Claude Code Guide

## Project overview

Pure-Python port of the ITS Irregular Terrain Model (ITM / Longley-Rice).  
Predicts terrestrial radiowave propagation loss for 20 MHz – 20 GHz.  
Public API: `predict_p2p`, `predict_area`, `predict_p2p_cr`, `predict_area_cr` in `pyitm_ng/itm.py`, re-exported from `pyitm_ng/__init__.py`.

## Commands

```bash
# Install (editable, with dev extras)
pip install -e ".[dev]"

# Run tests
python3 -m pytest

# Lint
ruff check pyitm_ng/
```

All 93 tests must pass before any commit, and `mypy` (strict, configured in `pyproject.toml`) must be clean (the 6 in `tests/test_differential.py` skip unless `ITM_REFERENCE_LIB` is set).

```bash
# Differential test against the NTIA/itm C++ reference (Linux, needs g++); exact = bit-identical
ITM_DIFF_EXACT=1 ITM_REFERENCE_LIB=$(tools/build_itm_reference.sh) python3 -m pytest tests/test_differential.py
```

## Package layout

| Module | Responsibility |
|---|---|
| `pyitm_ng/_constants.py` | Named constants (warn flags, mode codes, physics) |
| `pyitm_ng/models.py` | Enums and dataclasses (`TerrainProfile`, `PropagationResult`, `IntermediateValues`, …) |
| `pyitm_ng/terrain.py` | Horizon finding, delta-h, PFL helpers, area initialisation |
| `pyitm_ng/variability.py` | ICCDF, signal variability statistics |
| `pyitm_ng/propagation.py` | Free-space loss, diffraction, troposcatter, `longley_rice` |
| `pyitm_ng/itm.py` | Input validation, `predict_p2p`, `predict_area`, `predict_p2p_cr`, `predict_area_cr` |

## Accuracy requirement

All predictions must match the synthetic reference CSVs (`tests/data/synthetic/`: `p2p.csv` / `pfls.csv` / `area.csv`) to within **0.01 dB**, and must round to the published values in NTIA's own CSVs (`tests/data/ntia/`, checked by `tests/test_ntia_reference.py`). The integration tests in `tests/test_p2p.py` and `tests/test_area.py` enforce this tolerance — do not loosen it. `tests/test_differential.py` checks the C++ reference on random inputs, and with `ITM_DIFF_EXACT=1` (as in CI) requires bit-identical results; a vectorization that reorders floating-point operations can pass the CSVs and still fail there.

### Fidelity policy: match the C++ exactly

The port reproduces the NTIA/itm C++ reference (master `183ad95`) operation for operation, **including its numeric quirks**. In particular, `linear_least_squares_fit` truncates distances to terrain indices with `int()`, so a last-bit difference in a distance can select a neighbouring index and move `A__db` by more than 1 dB (NTIA/itm#21). This is intentional; do not "fix" it:

- Do not adopt rounding fixes such as the unmerged NTIA/itm#22, or any other deviation from the C++ arithmetic, even where it is arguably more robust.
- Vectorize only if the result is bit-identical to the C++ order of operations (e.g. `np.cumsum` for `d += xi`, not `i * xi`). Sequential `+=` reductions stay sequential loops (no `np.sum` / `np.dot` / `.mean()`).
- Square with `sq(x)` (from `_constants`) wherever the C++ has `pow(x, 2)`. GCC compiles that to `x*x`; Python `x**2` calls libm `pow()`, which differs from `x*x` in the last bit for ~0.1% of inputs. Other exponents stay `**` / `pow()`: the compiled C++ calls `pow()` for those too.
- Keep scalar code on Python floats: read array elements with `float(...)`. A numpy scalar silently turns complex arithmetic into `np.complex128`, whose division is not the C++ / CPython algorithm (`test_p2p_returns_python_floats` guards this).
- Where the C++ yields an IEEE ±inf / nan instead of failing (division by zero, `log(0)`), produce the same value (`_ieee_div`, `_c_max`, `iccdf`) instead of letting Python raise.
- `tests/test_differential.py` is the arbiter. Run it with `ITM_DIFF_EXACT=1`: `A__db` must be bit-identical, not just within 0.01 dB (a reordered reduction stays well inside 0.01 dB, so only exact mode catches it). CI runs it that way. The reference is built with `-ffp-contract=off -fcx-fortran-rules` (no fused multiply-adds, complex division inline rather than libgcc's FMA-using `__divdc3`), so the C++ is plain IEEE on every architecture; keep it that way.

Deliberate deviations from the C++ (the only ones). Both are input checks at an entry point where the C++ has undefined behaviour; neither changes arithmetic on valid input:

- `predict_p2p` / `predict_p2p_cr` raise `ValueError` for a terrain profile with fewer than 2 points (the C++ reads past the array).
- `TerrainProfile.from_pfl` clamps a PFL whose header declares more points than it contains, and logs a warning (the C++ reads out of bounds).
- Track merged upstream changes, never unmerged proposals. `.github/workflows/upstream.yml` checks NTIA/itm `master` weekly and opens an issue when it no longer equals the pin. To follow it: diff the upstream change, port it, update `ITM_COMMIT` in `tools/build_itm_reference.sh` (and the pin quoted in README, CLAUDE.md, AGENTS.md, LICENSE.md; `tests/test_docs_sync.py` checks they agree), then the bit-exact differential must pass.
- This section is duplicated verbatim in CLAUDE.md and AGENTS.md (`tests/test_docs_sync.py` fails if they drift); edit both.

## Coding conventions

- Functions accept plain Python/numpy scalars and return values; no output-pointer pattern.
- Warnings accumulate as OR'd integer bitmasks; every function that can raise a warning returns `(result, warnings)`.
- Variable names follow the ITM mathematical notation with pseudo-LaTeX underscores (e.g. `h_e__meter`, `A_ref__db`).
- Do not add docstrings or type annotations to code you didn't author in this session.

## Releasing

1. Set `__version__` in `pyitm_ng/__init__.py` (the only place the version lives).
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` and add a fresh empty `## [Unreleased]` above it.
3. Merge to `main`, then tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. `.github/workflows/release.yml` builds, verifies the tag matches the version, refuses to publish unless `CHANGELOG.md` has a `## [X.Y.Z] - YYYY-MM-DD` section for that version (so a tag pushed while the changelog still says `[Unreleased]`, i.e. publishing on hold, stops there), runs the bit-exact differential against the C++ reference, tests the built wheel, and publishes to PyPI (trusted publishing, `pypi` environment).

## CI

GitHub Actions (`.github/workflows/ci.yml`) on every push/PR to `main`:

- `test`: `pytest -v` on Python 3.10–3.14.
- `lint`: `ruff check` (rules in `pyproject.toml`) and `mypy` (strict).
- `min-deps`: each Python against its numpy floor from `pyproject.toml`.
- `differential`: builds the C++ reference and runs `tests/test_differential.py` (5000 random cases per entry point, `ITM_DIFF_EXACT=1`, bit-identical) on Linux x86_64 and aarch64, Python 3.10 and 3.14.

`.github/workflows/upstream.yml` runs weekly and opens an issue when NTIA/itm `master` moves past the pin.
