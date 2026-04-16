# PyITM — Third-Party Add-ons

## Terrain data — directly integrates with `TerrainProfile`

### `python-srtm` — best fit for pyitm

```bash
pip install python-srtm
```

Produces a list of elevation values between two lat/lon coordinates — exactly what `TerrainProfile` needs:

```python
from srtm import Srtm1HeightMapCollection
import numpy as np
from itm import predict_p2p, TerrainProfile, Climate, Polarization

elevations = Srtm1HeightMapCollection().get_elevation_profile(
    51.100, -1.200,   # TX lat/lon
    51.145, -1.150,   # RX lat/lon
)

resolution = 30.0  # SRTM1 = 30 m grid
terrain = TerrainProfile(
    elevations=np.array(elevations, dtype=float),
    resolution=resolution,
)

result = predict_p2p(h_tx__meter=30.0, h_rx__meter=5.0, terrain=terrain, ...)
```

Also available: `elevation` (pip) for downloading GeoTIFF DEMs at 30 m / 90 m via CGIAR-CSI.

---

## Atmospheric corrections — additive on top of `A__db`

### `itur` (ITU-Rpy) — atmospheric gas & rain attenuation

```bash
pip install itur
```

Covers effects not modeled in ITM at all. Most relevant to pyitm:

| Recommendation | What it adds |
|---|---|
| P.676-12 | Oxygen + water vapour absorption |
| P.838-3 | Rain attenuation along path |
| P.840-8 | Cloud and fog attenuation |
| P.453-13 | Refractivity data (feeds `N_0` in pyitm) |

Integration pattern — all additive on top of `result.A__db`:

```python
import itur
from itm import predict_p2p

result = predict_p2p(..., N_0=301.0, f__mhz=10000.0, return_intermediate=True)

# Gas attenuation (relevant above ~1 GHz)
A_gas = itur.gaseous_attenuation_terrestrial_path(
    r=result.intermediate.d__km,
    f=10.0,        # GHz
    el=0.5,        # elevation angle, degrees
    rho=7.5,       # water vapour density g/m³
    T=15,          # temperature °C
    P=1013,        # pressure hPa
).value

# Rain attenuation
A_rain = itur.rain_attenuation(
    lat=51.5, lon=-1.2,
    f=10.0,        # GHz
    el=0.5,
    p=0.01,        # % of time exceeded
).value

A_total = result.A__db + A_gas + A_rain
```

**Note:** Most impactful above ~3 GHz where gas absorption becomes significant. At pyitm's lower frequencies (< 1 GHz) the contribution is small.

---

## Alternative terrestrial model — cross-validation

### `Py1812` — ITU-R P.1812

```bash
pip install git+https://github.com/eeveetza/Py1812
```

- **Frequency:** 30 MHz–6 GHz
- **Inputs:** same as pyitm — terrain profile, antenna heights, frequency, polarization
- **Output:** basic transmission loss (dB)
- **Key difference:** P.1812 is a newer ITU standard incorporating terrain diffraction + troposcatter + clutter; pyitm (ITM) is the classic NTIA model

Use as a cross-check on the same terrain profile:

```python
from Py1812 import bt_loss
from itm import predict_p2p

itm_result  = predict_p2p(terrain=terrain, f__mhz=900.0, ...)
p1812_loss  = bt_loss(f=0.9, t=50, lat=51.5, lon=-1.2, pfl=pfl, ...)

print(f"ITM:    {itm_result.A__db:.1f} dB")
print(f"P.1812: {p1812_loss:.1f} dB")
```

### `Py452` — ITU-R P.452

```bash
pip install git+https://github.com/eeveetza/Py452
```

- **Use case:** Interference and coordination studies between terrestrial stations
- **Integrates as:** Cross-validation for interference path loss calculations alongside ITM

---

## Summary

| Library | PyPI | Category | Integrates with pyitm as |
|---|---|---|---|
| `python-srtm` | Yes | Terrain data | Feed `TerrainProfile` from real coordinates |
| `elevation` | Yes | Terrain data | Download GeoTIFF DEMs for profile extraction |
| `itur` | Yes | Atmospheric attenuation | Additive correction on `A__db` (gas, rain, cloud) |
| `Py1812` | GitHub | Alternative model | Cross-validation against ITM on same terrain |
| `Py452` | GitHub | Interference model | Cross-validation for interference studies |

The highest-value additions: **`python-srtm`** (enables real-world p2p predictions from coordinates alone) and **`itur`** (adds weather/atmospheric effects above 3 GHz that ITM does not model).

---

## References

- [python-srtm — PyPI](https://pypi.org/project/python-srtm/)
- [elevation — PyPI](https://pypi.org/project/elevation/)
- [itur (ITU-Rpy) — GitHub](https://github.com/inigodelportillo/ITU-Rpy)
- [Py1812 — GitHub](https://github.com/eeveetza/Py1812)
- [Py452 — GitHub](https://github.com/eeveetza/Py452)
