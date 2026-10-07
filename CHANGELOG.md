# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **Bit-identical with the C++ on the whole valid input space, not just typical paths.** Fuzzing the full documented ranges (heights to 3000 m, percentiles 0.001–99.999 %, profiles from 2 points, boundary values) found four ways the port crashed or diverged where the C++ returns a result (~370 per 8,000 cases). Fixed:
  - 2-point (1-interval) profiles raised `attempt to get argmax of an empty sequence`; `find_horizons` now returns early like the C++ loop
  - `math.log`/`log10`/`sqrt`/`exp`/`pow`/`sin`/`cos` raised where C libm returns nan/±inf (e.g. Vogler's B_0 < 0 at high antennas → `log10` of a negative number); all scalar math now goes through `pyitm_ng/_cfloat.py` with C semantics, checked against libm in `tests/test_cfloat.py`. Builtin `pow` with a negative base and fractional exponent returned a complex number (latent) and is fixed by the same change
  - `max`/`min` disagree with the C `MAX`/`MIN` macros on nan (each discards it in the opposite argument position); the two `DIM` sites were written as `max(a - b, 0)`. All 37 sites now use the exact C construct and argument order
  - `cmath.sqrt` differs from glibc's `csqrt` for purely imaginary arguments: at `epsilon == 1` the C++ rejects the ground impedance (error 1013) and Python could return a result. `c_csqrt` ports glibc's algorithm line for line (with libm `hypot` via `abs(complex)`: CPython's `math.hypot` is a different algorithm)
- New `Warnings.REFERENCE_ATTENUATION_NAN` (bit `1 << 30`): set where the C++ silently turns a NaN reference attenuation into 0 dB (~0.4% of valid inputs). `A__db` stays bit-identical to the C++.
- `TerrainProfile`: hash consistent with equality for `-0.0` vs `0.0`; pickling and copying rebuild through validation, so the elevations stay read-only in multiprocessing workers
- The differential test samples the full input space with boundary values over-sampled; `ITM_DIFF_SEED` varies the draw
- **Breaking — invalid input raises instead of computing.** Inputs the C++ turns into nan, a wrong answer or a crash now raise at the entry points (documented deviations, `CLAUDE.md`):
  - any NaN or infinity in a float argument or a terrain elevation: `ValueError` naming the argument / first bad index (was: `ValueError: cannot convert float NaN to integer`, `ZeroDivisionError`, or a silent `nan` result for NaN `f__mhz`, `epsilon`, `sigma`, `time`, ...)
  - terrain `resolution` <= 0: `ValueError` (was `ZeroDivisionError` / `math domain error`)
  - a PFL whose header declares more points than it holds: `ValueError` (was: computed a shorter path than described and only logged a warning)
  - a non-integral PFL header: `ValueError`
  - `climate`, `pol`, `mdvar`, `tx_siting`, `rx_siting` that are not integers or enum members (e.g. `mdvar=2.7`, `"2"`): `TypeError` (was silently truncated by `int()`); non-numeric float arguments: `TypeError`
- `TerrainProfile` validates on construction, stores a read-only copy of the elevations, and compares and hashes by value (`==` used to raise, `hash()` too)
- `PropagationResult.warnings` is a `Warnings` flag (an `int` subclass, so existing bit tests still work)
- `climate`, `pol`, `mdvar` and siting parameters are typed `Enum | int`
- **Breaking — renamed for PyPI:** distribution `pyitm` → `pyitm-ng` (the `pyitm` and `itm` names on PyPI belong to unrelated projects), import package `itm` → `pyitm_ng`. Update `from itm import …` to `from pyitm_ng import …`. (Entries for 0.1.0 and 0.2.0 below use the names of their time: distribution `pyitm`, package `itm/`.)
- Version 0.3.0; `pyitm_ng.__version__` is the single source (read by `pyproject.toml`)
- Package metadata for PyPI (description, readme, license file, classifiers, URLs); explicit package list so `tests/` and `tools/` are not installed
- Ruff rule set selected explicitly (`E4`, `E7`, `E9`, `F`) so ruff releases can't change what CI enforces
- **Bit-identical to the C++ reference.** `predict_p2p` / `predict_area` now reproduce NTIA/itm (`183ad95`) to the last bit on 50,000 random cases per mode (previously only within 0.01 dB). Results can change in the last few bits: 15,180 of those 100,000 cases moved, by at most 5.6e-12 dB. In principle a last-bit change in `h_sys` can flip an `int()` truncation and move a result by whole dB; none occurred in those runs. The remaining arithmetic deviations removed:
  - `h_sys` mean, `linear_least_squares_fit` sums and the `compute_delta_h` fit line use the C++ sequential `+=` order instead of `np.mean` / `np.sum` / `np.dot` / closed form
  - diffraction reference distances computed as `5.0*X` / `10.0*X` like the C++ (was `0.5*(10.0*X)`)
  - every C++ `pow(x, 2)` is `x*x` (`_constants.sq`), which is what GCC compiles it to; Python's `x**2` calls libm `pow()` and differs in the last bit for ~0.1% of inputs
  - numpy scalars no longer leak from the terrain array into scalar code; they turned `LineOfSightLoss`'s complex division into `np.complex128` division, a different algorithm from the C++ / CPython one
- `M_d == M_s` in `longley_rice` yields the C++ IEEE ±inf / nan (passed through the C++ `MAX` semantics) instead of raising `ZeroDivisionError`
- `iccdf` has no domain check, matching the C++: a time / location / situation small enough that `x / 100` underflows to 0 now gives the C++ result (the nan is discarded or propagated by the mdvar logic, as in the C++) instead of raising `ValueError`
- License: the port's own code is MIT; NTIA's notice is kept verbatim for the model and its reference data, with the statement of modifications it asks for (`LICENSE.md`). `pyproject.toml` declares `license = "MIT AND NTIA-PD"`, so PyPI shows it.
- numpy floors per Python, each the first numpy with wheels for that version (`>=1.21.2` on 3.10 up to `>=2.3.2` on 3.14; was `numpy>=1.21` for all, which cannot install on 3.11+)
- p2p is faster on long profiles while staying bit-identical: the sequential sums run through `np.add.accumulate` (strictly left to right, the C++ order) and the delta-h resampling jumps k points at once (`x_pos - k` gives the same bits as k exact `-= 1.0`). 10,000-point profile: 1.28 ms in 0.2.x, 0.60 ms now (median of 1,000 calls, CPython 3.11) (the first bit-exact version, using plain loops, took 2.41 ms).
- Test data from the repo root (`p2p.csv`, `pfls.csv`, `area.csv`, synthetic) moved to `tests/data/synthetic/`
- Ruff adds `B`, `UP`, `NPY`; `mypy --strict` runs in CI
- C++ reference built with `-ffp-contract=off -fcx-fortran-rules`: no fused multiply-adds on any architecture. On aarch64 a stock build's complex division (libgcc `__divdc3`) uses FMA and changed the last bit of ~0.02% of p2p results, found by the new aarch64 differential; pyitm-ng was already the same on both architectures.
- `release.yml` refuses to publish unless `CHANGELOG.md` has a `## [X.Y.Z] - YYYY-MM-DD` section for the tag, and runs the bit-exact differential before publishing

### Added

- `.github/workflows/release.yml`: on a `v*` tag, builds sdist + wheel, checks the tag matches the version, runs the test suite against the installed wheel, and publishes to PyPI via trusted publishing
- Documented fidelity policy (README, `CLAUDE.md`, `AGENTS.md`): pyitm-ng matches the NTIA/itm C++ exactly, including the `int()` truncation sensitivity in `linear_least_squares_fit` (NTIA/itm#21); upstream rounding fixes such as NTIA/itm#22 are deliberately not adopted. The two deliberate deviations (input checks where the C++ has undefined behaviour) are listed there.
- `tests/test_differential.py`: compares `predict_p2p` / `predict_area` against the NTIA/itm C++ reference on random inputs (A__db within 0.01 dB, identical warnings, matching errors); skips unless `ITM_REFERENCE_LIB` is set. `ITM_DIFF_EXACT=1` requires bit-identical `A__db`; CI runs it that way. Covers all four entry points (TLS and CR, p2p and area) and underflowing percentile inputs across every mdvar.
- `tests/test_differential.py::test_ground_impedance_extremes_match_cpp`: smallest sigma, epsilon floor, both polarizations and the frequency range ends on line-of-sight and diffraction paths, bit-identical to the C++ (including its ground-impedance error 1013); `tests/test_edge_cases.py` runs the same grid without the reference and asserts the `(sin_psi + Z_g)` denominator never raises
- `tests/test_cfloat.py`: `ieee_div` against IEEE division (signed infinities, 0/0, subnormal divisors) and `sq` against `x * x`
- `tests/test_reference_build.py`: compiles `pow` with the flags in `tools/build_itm_reference.sh` and asserts `pow(x, 2)` folds to one multiply while exponents 3, 4, 6, 1/3 and 0.25 stay `pow()` calls, the assumption behind `sq()` and `c_pow` (skipped without g++/objdump)
- `tools/build_itm_reference.sh`: builds the C++ reference at a pinned commit as `libitm.so`
- CI `differential` job running the above on 5000 cases per mode
- `tests/test_ntia_reference.py`: p2p and area cases from the CSVs shipped with NTIA/itm (`tests/data/ntia/`, real terrain profiles); results must round to the published values
- `test_p2p_returns_python_floats`: guards against numpy scalars in the scalar code path
- `tests/test_validation.py`: 79 cases for the input checks above
- `tests/test_edge_cases.py` (pinned C++ values for each edge bug, all failing on the previous code) and `tests/test_cfloat.py` (C-semantics helpers vs libm, incl. 45k `csqrt` inputs)
- CI `test` job on macOS and Windows as well as Linux (Python 3.10–3.14), backing the "OS Independent" classifier. It found that the tests read files with the platform default encoding (cp1252 on Windows); every read now says `utf-8`, and CI runs with `-X warn_default_encoding -W error::EncodingWarning` so an unspecified encoding fails on Linux too.
- Differential on Linux aarch64 as well as x86_64, Python 3.10 and 3.14; exact test on 1,000-10,000 point profiles
- CI `min-deps` job: every supported Python against its numpy floor
- `.github/workflows/upstream.yml`: weekly check of NTIA/itm `master` against the pin; opens an issue when it moves
- `tests/test_docs_sync.py`: the fidelity policy in CLAUDE.md and AGENTS.md must stay identical, and every quoted pin must match `tools/build_itm_reference.sh`
- README: platform scope of the bit-exact claim, upstream tracking, performance table, install-from-GitHub until the first PyPI release
- Python 3.14 in the CI test matrix

### Fixed

- `itm/__init__.py` docstring listed only two of the four entry points; `documentation/functions.md` claimed validation against "FORTRAN 1.2.2" (it is validated against the C++ reference) and had a stale test table; `documentation/todo.md` still listed CR mode as open
- **`find_horizons`**: horizon distances are again built by sequential accumulation (`d += xi`), as in the C++ reference, instead of `i * xi`. The vectorized form introduced in 0.2.0 differs in the last bit, which `int()` truncation in `linear_least_squares_fit` can turn into a different terrain index; on affected paths `predict_p2p` was off by up to ~1.9 dB. A differential run against NTIA/itm (C++, master `183ad95`) now matches exactly on 1000 random p2p and 1000 random area cases.
- `tests/data/synthetic/pfls.csv` row 1 declared 199 intervals but held 190 values; its expected `A__db` is exactly the C++ result for 189 intervals, so the header was a typo. The old clamp hid it; corrected to 189.
- README example: PFL header `99` means 99 intervals / 100 points (comment said 100 intervals); `mdvar` shown via `MDVar` (`MDVar.MOBILE + 10`) instead of a bare 12; footer said "Copyright NTIA" (NTIA's work is not under US copyright)
- Added `test_find_horizons_distances_match_cpp_accumulation` and `test_p2p_horizon_distance_rounding_regression` (test count 68 → 70)

### Removed

- Unused `logging` import and `logger` in `pyitm_ng/itm.py`

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
