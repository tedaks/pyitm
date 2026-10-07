# pyitm-ng — Agent Guide

## Project overview

Pure-Python port of the ITS Irregular Terrain Model (ITM / Longley-Rice).  
Predicts terrestrial radiowave propagation loss for frequencies 20 MHz – 20 GHz.  
Public entry points: `predict_p2p`, `predict_area`, `predict_p2p_cr`, `predict_area_cr` (see `pyitm_ng/itm.py`).

## Setup

```bash
pip install -e ".[dev]"
```

Requires Python ≥ 3.10 and numpy.

## Verification

```bash
python3 -m pytest          # all 172 tests must pass (6 differential tests skip without ITM_REFERENCE_LIB); mypy must be clean
ruff check pyitm_ng/            # zero lint errors
```

Run both commands after every change. Never submit work that breaks either.

Changes to numeric code in `pyitm_ng/` should also pass the differential test against the NTIA/itm C++ reference (Linux, needs g++):

```bash
ITM_DIFF_EXACT=1 ITM_REFERENCE_LIB=$(tools/build_itm_reference.sh) python3 -m pytest tests/test_differential.py
```

## Repository layout

```
pyitm_ng/
  _constants.py    — physics constants and warning/error flag values
  models.py        — enums (Climate, Polarization, MDVar, …) and dataclasses
  terrain.py       — horizon/delta-h/PFL geometry helpers
  variability.py   — statistical variability (ICCDF, curve fit, variability)
  propagation.py   — core propagation (LOS, diffraction, troposcatter, longley_rice)
  itm.py           — public API: predict_p2p, predict_area, predict_p2p_cr, predict_area_cr
tests/
  test_p2p.py      — integration: every row of data/synthetic/p2p.csv against data/synthetic/pfls.csv
  test_area.py     — integration: every row of data/synthetic/area.csv
  test_ntia_reference.py — NTIA/itm's own reference CSVs (tests/data/ntia/, real terrain)
  test_differential.py — random inputs vs the C++ reference (skips without ITM_REFERENCE_LIB)
tools/
  build_itm_reference.sh — builds NTIA/itm (pinned commit) as libitm.so
  test_*.py        — unit tests per module
tests/data/synthetic/          — synthetic reference cases (do not modify)
tests/data/ntia/               — NTIA/itm reference data, verbatim from master 183ad95 (do not modify)
```

## Accuracy constraint

All outputs must match the reference CSVs within **0.01 dB**. This tolerance is hardcoded in `test_p2p.py` and `test_area.py`. Do not change it.

## Fidelity policy: match the C++ exactly

The port reproduces the NTIA/itm C++ reference (master `183ad95`) operation for operation, **including its numeric quirks**. In particular, `linear_least_squares_fit` truncates distances to terrain indices with `int()`, so a last-bit difference in a distance can select a neighbouring index and move `A__db` by more than 1 dB (NTIA/itm#21). This is intentional; do not "fix" it:

- Do not adopt rounding fixes such as the unmerged NTIA/itm#22, or any other deviation from the C++ arithmetic, even where it is arguably more robust.
- Vectorize only if the result is bit-identical to the C++ order of operations (e.g. `np.cumsum` for `d += xi`, not `i * xi`). Sequential `+=` reductions stay sequential loops (no `np.sum` / `np.dot` / `.mean()`).
- Square with `sq(x)` (from `_constants`) wherever the C++ has `pow(x, 2)`. GCC compiles that to `x*x`; Python `x**2` calls libm `pow()`, which differs from `x*x` in the last bit for ~0.1% of inputs. Other exponents stay `**` / `pow()`: the compiled C++ calls `pow()` for those too.
- Keep scalar code on Python floats: read array elements with `float(...)`. A numpy scalar silently turns complex arithmetic into `np.complex128`, whose division is not the C++ / CPython algorithm (`test_p2p_returns_python_floats` guards this).
- Where the C++ yields an IEEE ±inf / nan instead of failing (division by zero, `log(0)`), produce the same value (`_ieee_div`, `_c_max`, `iccdf`) instead of letting Python raise.
- `tests/test_differential.py` is the arbiter. Run it with `ITM_DIFF_EXACT=1`: `A__db` must be bit-identical, not just within 0.01 dB (a reordered reduction stays well inside 0.01 dB, so only exact mode catches it). CI runs it that way. The reference is built with `-ffp-contract=off -fcx-fortran-rules` (no fused multiply-adds, complex division inline rather than libgcc's FMA-using `__divdc3`), so the C++ is plain IEEE on every architecture; keep it that way.

Deliberate deviations from the C++ (the only ones). All are input checks that reject input the C++ would turn into undefined behaviour, a crash, nan, or a plausible wrong answer. None changes arithmetic on valid input (the exact differential only uses valid input and must stay bit-identical):

- Non-finite numbers: every float argument of the four entry points and every terrain elevation must be finite, else `ValueError` naming the argument (elevations: the first offending index). The C++ lets NaN through every range comparison: `N_0=NaN` returns 99.58 dB with success.
- Terrain: `TerrainProfile` needs at least 2 points and `resolution` finite and > 0 (resolution 0 or NaN segfaults the C++). `TerrainProfile.from_pfl` rejects a header that is not a whole number >= 1, and a PFL whose header declares more points than it holds (the C++ reads past the array). Extra trailing values are ignored, as in the C++.
- Types: `climate`, `pol`, `mdvar`, `tx_siting`, `rx_siting` must be integers or enum members (`operator.index`), and float arguments real numbers; otherwise `TypeError`. A C caller cannot pass `mdvar=2.7`; Python must not truncate it.

Validation code lives in `pyitm_ng/models.py` (`require_finite`, `require_int`, `TerrainProfile.__post_init__`) and the entry points in `itm.py`; tests in `tests/test_validation.py`.
- Track merged upstream changes, never unmerged proposals. `.github/workflows/upstream.yml` checks NTIA/itm `master` weekly and opens an issue when it no longer equals the pin. To follow it: diff the upstream change, port it, update `ITM_COMMIT` in `tools/build_itm_reference.sh` (and the pin quoted in README, CLAUDE.md, AGENTS.md, LICENSE.md; `tests/test_docs_sync.py` checks they agree), then the bit-exact differential must pass.
- This section is duplicated verbatim in CLAUDE.md and AGENTS.md (`tests/test_docs_sync.py` fails if they drift); edit both.

## Conventions

- Internal functions return values; no output-pointer pattern.
- Warnings are OR'd integer bitmasks propagated upward through callers.
- Variable names mirror ITM mathematical notation (e.g. `h_e__meter`, `A_fs__db`).
- Constants live in `_constants.py`; do not embed magic numbers in other modules.

## Releasing

1. Set `__version__` in `pyitm_ng/__init__.py` (the only place the version lives).
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` and add a fresh empty `## [Unreleased]` above it.
3. Merge to `main`, then tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. `.github/workflows/release.yml` builds, verifies the tag matches the version, refuses to publish unless `CHANGELOG.md` has a `## [X.Y.Z] - YYYY-MM-DD` section for that version (so a tag pushed while the changelog still says `[Unreleased]`, i.e. publishing on hold, stops there), runs the bit-exact differential against the C++ reference, tests the built wheel, and publishes to PyPI (trusted publishing, `pypi` environment).
