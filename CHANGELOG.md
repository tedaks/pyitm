# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-04-15

### Added

- Package scaffold: `pyproject.toml`, `itm/` package, `tests/` directory
- `itm/_constants.py`: named constants replacing magic numbers from the C++ source
- `itm/models.py`: enums (`Climate`, `Polarization`, `MDVar`, `PropMode`, `SitingCriteria`) and dataclasses (`TerrainProfile`, `IntermediateValues`, `PropagationResult`)
- `itm/terrain.py`: `find_horizons`, `compute_delta_h`, `quick_pfl`, `initialize_area`
- `itm/variability.py`: `iccdf`, `terrain_roughness`, `sigma_h_function`, `linear_least_squares_fit`, `curve`, `variability`
- `itm/propagation.py`: `free_space_loss`, `fresnel_integral`, `knife_edge_diffraction`, `height_function`, `smooth_earth_diffraction`, `h0_curve`, `h0_function`, `f_function`, `troposcatter_loss`, `line_of_sight_loss`, `diffraction_loss`, `initialize_point_to_point`, `longley_rice`
- `itm/itm.py`: public entry points `predict_p2p` and `predict_area` with input validation
- Integration tests for point-to-point mode against `p2p.csv` / `pfls.csv` reference data
- Integration tests for area prediction mode against `area.csv` reference data
- README with model description, input/output tables, and references
- GitHub Actions workflow for tests and linting
- `ruff` added as a dev dependency for linting
