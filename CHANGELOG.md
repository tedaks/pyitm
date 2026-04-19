# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.2.0] - 2026-04-19

### Added

- `predict_p2p_cr` / `predict_area_cr`: now accept an explicit `mdvar` parameter, matching the C++ `ITM_P2P_CR` / `ITM_AREA_CR` API signature
- `TerrainProfile.from_pfl`: logs a warning when PFL data is truncated (fewer elevation values than the header declares)
- `test_predict_p2p_cr_matches_tls_equivalent` and `test_predict_area_cr_matches_tls_equivalent`: verify CR→TLS mapping correctness (test count 66 → 68)

### Changed

- **CR→TLS mapping** (`predict_p2p_cr`, `predict_area_cr`): changed from `time=reliability, location=confidence, situation=confidence, mdvar=1` to `time=reliability, location=50, situation=confidence` with caller-supplied `mdvar`, matching the C++ reference implementation (`ITM_P2P_CR_Ex`, `ITM_AREA_CR_Ex`)
- **`_validate_inputs`**: reordered checks so warning-range tests execute before error-range tests, matching the C++ `ValidateInputs.cpp` evaluation order
- **`PropagationResult.warnings`**: typed as `int` instead of `Warnings` (IntFlag), consistent with how warnings are accumulated throughout the codebase as plain integer bitmasks
- **`linear_least_squares_fit`**: inner accumulation loop vectorized with numpy (`np.sum`, `np.dot`) for improved performance on large terrain profiles

## [0.1.0] - 2026-04-15

### Added

- Package scaffold: `pyproject.toml`, `itm/` package, `tests/` directory
- `itm/_constants.py`: named constants replacing magic numbers from the C++ source
- `itm/models.py`: enums (`Climate`, `Polarization`, `MDVar`, `PropMode`, `SitingCriteria`) and dataclasses (`TerrainProfile`, `IntermediateValues`, `PropagationResult`)
- `itm/terrain.py`: `find_horizons`, `compute_delta_h`, `quick_pfl`, `initialize_area`
- `itm/variability.py`: `iccdf`, `terrain_roughness`, `sigma_h_function`, `linear_least_squares_fit`, `curve`, `variability`
- `itm/propagation.py`: `free_space_loss`, `fresnel_integral`, `knife_edge_diffraction`, `height_function`, `smooth_earth_diffraction`, `h0_curve`, `h0_function`, `f_function`, `troposcatter_loss`, `line_of_sight_loss`, `diffraction_loss`, `initialize_point_to_point`, `longley_rice`
- `itm/itm.py`: public entry points `predict_p2p`, `predict_area`, `predict_p2p_cr`, `predict_area_cr` with input validation
- Integration tests for point-to-point mode against `p2p.csv` / `pfls.csv` reference data
- Integration tests for area prediction mode against `area.csv` reference data
- README with model description, input/output tables, and references
- GitHub Actions workflow for tests and linting
- `ruff` added as a dev dependency for linting
- `TerrainProfile.from_pfl`: validates `len(pfl) >= 3` and `np_ >= 1`; raises `ValueError` with a clear message on bad input
- `predict_p2p`: validates `len(terrain.elevations) >= 2` before processing; raises `ValueError` on degenerate terrain
- Tests for warning bits: `WARN__TX_TERMINAL_HEIGHT`, `WARN__RX_TERMINAL_HEIGHT`, `WARN__FREQUENCY`, `WARN__SURFACE_REFRACTIVITY`, `WARN__PATH_DISTANCE_TOO_BIG_1`, `WARN__PATH_DISTANCE_TOO_SMALL_2`
- Upper-clamp assertion to `test_h0_function_clamps_eta` confirming `eta_s > 5` is safe

### Changed

- `predict_p2p`: replaced `sum(terrain.elevations[...]) / n` with `terrain.elevations[...].mean()` for the system height computation
- `iccdf` docstring: documents `0 < q < 1` precondition
- `smooth_earth_diffraction` docstring: documents preconditions on `h_e__meter` and denominator positivity
- `troposcatter_loss` docstring: documents `h_e__meter[0] > 0` precondition
- CI lint job: uses `pip install -e ".[dev]"` (pinned ruff version) instead of a bare `pip install ruff`
- CI lint job: now also lints `tests/` in addition to `itm/`
- CI test job: runs a matrix across Python 3.10, 3.11, 3.12, and 3.13

### Fixed

- Removed 16 unused imports from test files (`test_itm.py`, `test_models.py`, `test_propagation.py`)
- Fixed 3 E402 module-level-import-not-at-top violations in `test_variability.py`
- Fixed incorrect comment in `test_models.py`: `from_pfl` produces `np+1` elevation points, not `np+2`
