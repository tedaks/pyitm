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

All 68 tests must pass before any commit.

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

All predictions must match the reference CSVs (`p2p.csv` / `pfls.csv` / `area.csv`) to within **0.01 dB**. The integration tests in `tests/test_p2p.py` and `tests/test_area.py` enforce this tolerance — do not loosen it.

## Coding conventions

- Functions accept plain Python/numpy scalars and return values; no output-pointer pattern.
- Warnings accumulate as OR'd integer bitmasks; every function that can raise a warning returns `(result, warnings)`.
- Variable names follow the ITM mathematical notation with pseudo-LaTeX underscores (e.g. `h_e__meter`, `A_ref__db`).
- Do not add docstrings or type annotations to code you didn't author in this session.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs `pytest -v` and `ruff check itm/` on every push/PR to `main`.
