# Adding Antenna Gain to PyITM

## What A__db represents

`A__db` is **basic transmission loss** — it assumes isotropic 0 dBi antennas at both ends. No antenna gain is included anywhere in the library.

The signal budget relationship is:

```
Received Power (dBm) = TX Power (dBm) + TX Gain (dBi) + RX Gain (dBi) - A__db
```

---

## Option 1 — Apply gain outside the library (simplest)

If you just need a scalar gain at each end, no changes to pyitm are needed:

```python
from itm import predict_p2p, Climate, Polarization, TerrainProfile

result = predict_p2p(
    h_tx__meter=30.0,
    h_rx__meter=5.0,
    terrain=terrain,
    climate=Climate.CONTINENTAL_TEMPERATE,
    N_0=301.0,
    f__mhz=915.0,
    pol=Polarization.VERTICAL,
    epsilon=15.0,
    sigma=0.005,
    mdvar=3,
    time=50.0,
    location=50.0,
    situation=50.0,
)

tx_gain_dbi = 12.0   # e.g. directional Yagi
rx_gain_dbi  =  2.0  # e.g. dipole
tx_power_dbm = 30.0

path_loss_db        = result.A__db
effective_loss_db   = path_loss_db - tx_gain_dbi - rx_gain_dbi
received_power_dbm  = tx_power_dbm - effective_loss_db

print(f"Path loss:      {path_loss_db:.2f} dB")
print(f"Effective loss: {effective_loss_db:.2f} dB")
print(f"Rx power:       {received_power_dbm:.2f} dBm")
```

---

## Option 2 — Add antenna gain into the library

If you want gain baked into the result, the changes are minimal and confined to two files.

### `itm/models.py` — extend `PropagationResult`

```python
@dataclass
class PropagationResult:
    A__db: float                        # basic transmission loss (isotropic baseline)
    warnings: int
    A_eff__db: float = 0.0              # effective loss after antenna gains applied
    intermediate: IntermediateValues | None = None
```

### `itm/itm.py` — add gain parameters to both functions

```python
def predict_p2p(
    ...
    tx_antenna_gain_dbi: float = 0.0,
    rx_antenna_gain_dbi: float = 0.0,
    *,
    return_intermediate: bool = False,
) -> PropagationResult:
    ...
    # existing final line:
    A__db = var_db + A_fs__db

    return PropagationResult(
        A__db=A__db,
        A_eff__db=A__db - tx_antenna_gain_dbi - rx_antenna_gain_dbi,
        warnings=warnings,
        intermediate=iv,
    )
```

Apply the same pattern to `predict_area`.

---

## Option 3 — Antenna patterns (directional, angle-dependent)

For full antenna pattern support you need the elevation angle toward the remote terminal, which is already available via `return_intermediate=True`:

```python
import math

result = predict_p2p(..., return_intermediate=True)
iv = result.intermediate

# Elevation angle from TX toward RX (radians, negative = below horizon)
# theta_hzn[0] is the TX horizon angle; use it as a proxy for the path angle
tx_elevation_angle_rad = iv.theta_hzn[0]
tx_elevation_angle_deg = math.degrees(tx_elevation_angle_rad)

# Look up gain from your antenna pattern at this elevation
def antenna_gain_dbi(elevation_deg: float) -> float:
    # Replace with your pattern table or analytical model
    # Example: simple cosine rolloff from boresight at 0 degrees
    return 10.0 * math.cos(math.radians(elevation_deg))

tx_gain = antenna_gain_dbi(tx_elevation_angle_deg)
rx_gain = antenna_gain_dbi(-tx_elevation_angle_deg)   # mirror for RX

effective_loss = result.A__db - tx_gain - rx_gain
```

---

## Summary

| Approach | Changes needed | When to use |
|---|---|---|
| External calculation | None | Scalar gains, quick integration |
| Add params to library | `models.py` + `itm.py` | Clean API, gains logged in result |
| Antenna patterns | External + `theta_hzn` from intermediate values | Directional/phased array antennas |

For most use cases, **Option 1 is sufficient** — the library is intentionally scoped to path loss only, and antenna gain is a post-processing step in the link budget.
