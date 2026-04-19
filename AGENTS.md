# pyitm — Agent Guide

## Project overview

Pure-Python port of the ITS Irregular Terrain Model (ITM / Longley-Rice).  
Predicts terrestrial radiowave propagation loss for frequencies 20 MHz – 20 GHz.  
Public entry points: `predict_p2p`, `predict_area`, `predict_p2p_cr`, `predict_area_cr` (see `itm/itm.py`).

## Setup

```bash
pip install -e ".[dev]"
```

Requires Python ≥ 3.10 and numpy.

## Verification

```bash
python3 -m pytest          # all 68 tests must pass
ruff check itm/            # zero lint errors
```

Run both commands after every change. Never submit work that breaks either.

## Repository layout

```
itm/
  _constants.py    — physics constants and warning/error flag values
  models.py        — enums (Climate, Polarization, MDVar, …) and dataclasses
  terrain.py       — horizon/delta-h/PFL geometry helpers
  variability.py   — statistical variability (ICCDF, curve fit, variability)
  propagation.py   — core propagation (LOS, diffraction, troposcatter, longley_rice)
  itm.py           — public API: predict_p2p, predict_area, predict_p2p_cr, predict_area_cr
tests/
  test_p2p.py      — integration: every row of p2p.csv against pfls.csv terrain data
  test_area.py     — integration: every row of area.csv
  test_*.py        — unit tests per module
p2p.csv / pfls.csv / area.csv  — reference data (do not modify)
```

## Accuracy constraint

All outputs must match the reference CSVs within **0.01 dB**. This tolerance is hardcoded in `test_p2p.py` and `test_area.py`. Do not change it.

## Conventions

- Internal functions return values; no output-pointer pattern.
- Warnings are OR'd integer bitmasks propagated upward through callers.
- Variable names mirror ITM mathematical notation (e.g. `h_e__meter`, `A_fs__db`).
- Constants live in `_constants.py`; do not embed magic numbers in other modules.
