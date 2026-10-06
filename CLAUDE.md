# pyitm — Claude Code Guide

## Project overview

Pure-Python port of the ITS Irregular Terrain Model (ITM / Longley-Rice).  
Predicts terrestrial radiowave propagation loss for 20 MHz – 20 GHz.  
Public API: `predict_p2p`, `predict_area`, `predict_p2p_cr`, `predict_area_cr` in `itm/itm.py`, re-exported from `itm/__init__.py`.

## Commands

```bash
# Install (editable, with dev extras)
pip install -e ".[dev]"

# Run tests
python3 -m pytest

# Lint
ruff check itm/
```

All 82 tests must pass before any commit (the 2 in `tests/test_differential.py` skip unless `ITM_REFERENCE_LIB` is set).

```bash
# Differential test against the NTIA/itm C++ reference (Linux, needs g++)
ITM_REFERENCE_LIB=$(tools/build_itm_reference.sh) python3 -m pytest tests/test_differential.py
```

## Package layout

| Module | Responsibility |
|---|---|
| `itm/_constants.py` | Named constants (warn flags, mode codes, physics) |
| `itm/models.py` | Enums and dataclasses (`TerrainProfile`, `PropagationResult`, `IntermediateValues`, …) |
| `itm/terrain.py` | Horizon finding, delta-h, PFL helpers, area initialisation |
| `itm/variability.py` | ICCDF, signal variability statistics |
| `itm/propagation.py` | Free-space loss, diffraction, troposcatter, `longley_rice` |
| `itm/itm.py` | Input validation, `predict_p2p`, `predict_area`, `predict_p2p_cr`, `predict_area_cr` |

## Accuracy requirement

All predictions must match the reference CSVs (`p2p.csv` / `pfls.csv` / `area.csv`) to within **0.01 dB**, and must round to the published values in NTIA's own CSVs (`tests/data/ntia/`, checked by `tests/test_ntia_reference.py`). The integration tests in `tests/test_p2p.py` and `tests/test_area.py` enforce this tolerance — do not loosen it. `tests/test_differential.py` enforces it against the C++ reference on random inputs; a vectorization that reorders floating-point operations can pass the CSVs and still fail here.

### Fidelity policy: match the C++ exactly

The port reproduces the NTIA/itm C++ reference (master `183ad95`) operation for operation, **including its numeric quirks**. In particular, `linear_least_squares_fit` truncates distances to terrain indices with `int()`, so a last-bit difference in a distance can select a neighbouring index and move `A__db` by more than 1 dB (NTIA/itm#21). This is intentional; do not "fix" it:

- Do not adopt rounding fixes such as the unmerged NTIA/itm#22, or any other deviation from the C++ arithmetic, even where it is arguably more robust.
- Vectorize only if the result is bit-identical to the C++ order of operations (e.g. `np.cumsum` for `d += xi`, not `i * xi`). `tests/test_differential.py` is the arbiter.
- If upstream changes its arithmetic, update the pinned commit in `tools/build_itm_reference.sh` and follow it.

## Coding conventions

- Functions accept plain Python/numpy scalars and return values; no output-pointer pattern.
- Warnings accumulate as OR'd integer bitmasks; every function that can raise a warning returns `(result, warnings)`.
- Variable names follow the ITM mathematical notation with pseudo-LaTeX underscores (e.g. `h_e__meter`, `A_ref__db`).
- Do not add docstrings or type annotations to code you didn't author in this session.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs `pytest -v` and `ruff check itm/ tests/` on every push/PR to `main`, plus a `differential` job that builds the C++ reference and runs `tests/test_differential.py` on 5000 random cases per mode.
