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
python3 -m pytest          # all 82 tests must pass (2 differential tests skip without ITM_REFERENCE_LIB)
ruff check itm/            # zero lint errors
```

Run both commands after every change. Never submit work that breaks either.

Changes to numeric code in `itm/` should also pass the differential test against the NTIA/itm C++ reference (Linux, needs g++):

```bash
ITM_REFERENCE_LIB=$(tools/build_itm_reference.sh) python3 -m pytest tests/test_differential.py
```

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
  test_ntia_reference.py — NTIA/itm's own reference CSVs (tests/data/ntia/, real terrain)
  test_differential.py — random inputs vs the C++ reference (skips without ITM_REFERENCE_LIB)
tools/
  build_itm_reference.sh — builds NTIA/itm (pinned commit) as libitm.so
  test_*.py        — unit tests per module
p2p.csv / pfls.csv / area.csv  — reference data (do not modify)
tests/data/ntia/               — NTIA/itm reference data, verbatim from master 183ad95 (do not modify)
```

## Accuracy constraint

All outputs must match the reference CSVs within **0.01 dB**. This tolerance is hardcoded in `test_p2p.py` and `test_area.py`. Do not change it.

## Fidelity policy: match the C++ exactly

The port reproduces the NTIA/itm C++ reference (master `183ad95`) operation for operation, **including its numeric quirks**. In particular, `linear_least_squares_fit` truncates distances to terrain indices with `int()`, so a last-bit difference in a distance can select a neighbouring index and move `A__db` by more than 1 dB (NTIA/itm#21). This is intentional; do not "fix" it:

- Do not adopt rounding fixes such as the unmerged NTIA/itm#22, or any other deviation from the C++ arithmetic, even where it is arguably more robust.
- Vectorize only if the result is bit-identical to the C++ order of operations (e.g. `np.cumsum` for `d += xi`, not `i * xi`). `tests/test_differential.py` is the arbiter.
- If upstream changes its arithmetic, update the pinned commit in `tools/build_itm_reference.sh` and follow it.

## Conventions

- Internal functions return values; no output-pointer pattern.
- Warnings are OR'd integer bitmasks propagated upward through callers.
- Variable names mirror ITM mathematical notation (e.g. `h_e__meter`, `A_fs__db`).
- Constants live in `_constants.py`; do not embed magic numbers in other modules.
