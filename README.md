# pyitm — ITS Irregular Terrain Model (Longley-Rice)

Pure-Python port of the NTIA ITM/Longley-Rice model for predicting terrestrial
radiowave propagation loss at frequencies 20 MHz – 20 GHz.

## Installation

```bash
pip install -e .
```

## Quick Start

### Point-to-Point Mode

```python
from itm import predict_p2p, TerrainProfile, Climate, Polarization

pfl = [99, 100.0] + [0.0] * 100  # 100 intervals, 100m resolution, flat terrain
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
    mdvar=12,
    time=50.0,
    location=50.0,
    situation=50.0,
)
print(f"Propagation loss: {result.A__db:.2f} dB")
```

### Area Mode

```python
from itm import predict_area, Climate, Polarization, SitingCriteria

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
    mdvar=0,
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
ruff check itm/
```

## References

- G.A. Hufford, [The ITS Irregular Terrain Model, version 1.2.2 Algorithm](https://www.its.bldrdoc.gov/media/50676/itm_alg.pdf)
- G.A. Hufford, [The Irregular Terrain Model](https://www.its.bldrdoc.gov/media/50674/itm.pdf)
- A.G. Longley and P.L. Rice, [Prediction of Tropospheric Radio Transmission Loss Over Irregular Terrain](https://www.its.bldrdoc.gov/publications/details.aspx?pub=2784), NTIA Technical Report ERL 79-ITS 67, July 1968.

Derived from [NTIA/itm](https://github.com/NTIA/itm). Copyright NTIA.