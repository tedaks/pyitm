# pyitm-ng — ITS Irregular Terrain Model (Longley-Rice)

Pure-Python port of the NTIA ITM/Longley-Rice model for predicting terrestrial
radiowave propagation loss at frequencies 20 MHz – 20 GHz.

pyitm-ng is an independent port of the [NTIA/itm](https://github.com/NTIA/itm)
C++ reference; it is not related to the `pyitm` package on PyPI.

## Installation

pyitm-ng is not on PyPI yet (the first release, 0.3.0, is pending). Until then,
install from GitHub:

```bash
pip install "pyitm-ng @ git+https://github.com/tedaks/pyitm"
```

Once released: `pip install pyitm-ng`.

```python
import pyitm_ng
```

For development, from a clone: `pip install -e ".[dev]"`.

## Quick Start

### Point-to-Point Mode

```python
from pyitm_ng import predict_p2p, TerrainProfile, Climate, MDVar, Polarization

# PFL format: [number of intervals, resolution in m, elevations...];
# 99 intervals = 100 elevation points, 100 m apart (flat terrain here).
pfl = [99, 100.0] + [0.0] * 100
terrain = TerrainProfile.from_pfl(pfl)

result = predict_p2p(
    h_tx__meter=10.0,
    h_rx__meter=2.0,
    terrain=terrain,
    climate=Climate.CONTINENTAL_TEMPERATE,
    N_0=301.0,
    f__mhz=230.0,
    pol=Polarization.VERTICAL,
    epsilon=15.0,
    sigma=0.008,
    mdvar=MDVar.MOBILE + 10,  # 12: mobile mode; +10 removes location variability
    time=50.0,
    location=50.0,
    situation=50.0,
)
print(f"Propagation loss: {result.A__db:.2f} dB")
```

### Area Mode

```python
from pyitm_ng import predict_area, Climate, MDVar, Polarization, SitingCriteria

result = predict_area(
    h_tx__meter=10.0,
    h_rx__meter=2.0,
    tx_siting=SitingCriteria.CAREFUL,
    rx_siting=SitingCriteria.RANDOM,
    d__km=50.0,
    delta_h__meter=50.0,
    climate=Climate.CONTINENTAL_TEMPERATE,
    N_0=301.0,
    f__mhz=230.0,
    pol=Polarization.VERTICAL,
    epsilon=15.0,
    sigma=0.008,
    mdvar=MDVar.SINGLE_MESSAGE,
    time=50.0,
    location=50.0,
    situation=50.0,
)
print(f"Propagation loss: {result.A__db:.2f} dB")
```

## API Reference

| Function | Description |
|----------|-------------|
| `predict_p2p` | Point-to-point propagation with time/location/situation (TLS) variability |
| `predict_p2p_cr` | Point-to-point propagation with confidence/reliability (CR) variability |
| `predict_area` | Area-mode propagation with TLS variability |
| `predict_area_cr` | Area-mode propagation with CR variability |

All functions return a `PropagationResult` with `.A__db` (propagation loss in dB) and `.warnings` (bitmask of warnings). Set `return_intermediate=True` to get `IntermediateValues` with detailed path parameters.

See docstrings for full parameter documentation.

## Running Tests

```bash
pip install -e ".[dev]"
python3 -m pytest
ruff check pyitm_ng/ tests/
```

To also compare against the NTIA/itm C++ reference on random inputs (Linux, needs g++):

```bash
ITM_DIFF_EXACT=1 ITM_REFERENCE_LIB=$(tools/build_itm_reference.sh) python3 -m pytest tests/test_differential.py
```

## Numerical fidelity

pyitm-ng reproduces the [NTIA/itm](https://github.com/NTIA/itm) C++ implementation (master `183ad95`) bit for bit: CI compiles the C++ and requires identical `A__db`, warnings and errors on random inputs for all four entry points.

**Where this is verified:** Linux x86_64 and Linux aarch64 (glibc), CPython 3.10 and 3.14, C++ built with g++ `-O2 -ffp-contract=off`, in CI on every change. Bit-identity depends on the platform's math library (`exp`, `log`, `pow`, `sin`, ...) and on the compiler not fusing multiply-adds. macOS, Windows and other math libraries are not verified: any differences there would start in the last bits, but because of the sensitivity described next, a last-bit difference can occasionally become a whole-dB difference on some paths.

That bit-for-bit match includes the C++ model's sensitivity to tiny terrain changes: because terrain-fit bounds are truncated to whole profile points, a change of ~1e-9 m in a terrain profile, or in its resolution, can occasionally shift `A__db` by over 1 dB ([NTIA/itm#21](https://github.com/NTIA/itm/issues/21)). pyitm-ng deliberately keeps this behaviour so its results match the reference; if you compare results across tools, small input differences can explain large output differences on some paths.

**Tracking upstream:** the C++ reference is pinned (`tools/build_itm_reference.sh`). A weekly CI job checks NTIA/itm `master` and opens an issue when it moves. A change is then ported, the pin bumped, and the bit-exact differential must pass. pyitm-ng follows merged upstream changes only; unmerged proposals such as NTIA/itm#22 are not adopted.

## Performance

Pure Python, one path per call. Median time per call on one core (x86_64, CPython 3.11, numpy 2.x), against the C++ reference called through ctypes:

| | pyitm-ng | C++ |
|---|---|---|
| p2p, 100-point profile | 0.23 ms | 0.007 ms |
| p2p, 1,000 points | 0.37 ms | 0.017 ms |
| p2p, 3,679 points | 0.46 ms | 0.048 ms |
| p2p, 10,000 points | 0.68 ms | 0.12 ms |
| area mode | 0.05 ms | — |

Roughly 1,500–4,500 p2p paths per second per core; for large coverage runs, parallelize across paths (e.g. `multiprocessing`). There is no vectorized batch API: a faster path would have to give up bit-identity with the C++.

## References

- G.A. Hufford, [The ITS Irregular Terrain Model, version 1.2.2 Algorithm](https://www.its.bldrdoc.gov/media/50676/itm_alg.pdf)
- G.A. Hufford, [The Irregular Terrain Model](https://www.its.bldrdoc.gov/media/50674/itm.pdf)
- A.G. Longley and P.L. Rice, [Prediction of Tropospheric Radio Transmission Loss Over Irregular Terrain](https://www.its.bldrdoc.gov/publications/details.aspx?pub=2784), NTIA Technical Report ERL 79-ITS 67, July 1968.

Derived from [NTIA/itm](https://github.com/NTIA/itm). The port is MIT-licensed; the model and NTIA's reference data remain under NTIA's public-domain notice (`MIT AND NTIA-PD`, see [LICENSE.md](LICENSE.md)).