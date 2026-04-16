# PyITM — Recommendations & TODO

## Low effort

- [ ] **Ground type presets** — Add `itm/ground_types.py` with a dict of common `epsilon`/`sigma` values (average, poor, good, fresh water, sea water, urban). Reduces lookup friction for the two most easily confused inputs.

- [ ] **Frequency / climate presets** — Add reference dicts for typical `N_0` by region and `climate` by geography.

- [ ] **Link budget helper** — Add `itm/link_budget.py` with a thin convenience function that takes TX power (dBm), TX/RX antenna gains (dBi), and a `PropagationResult`, and returns received power (dBm), and link margin (dB) given a noise floor.

- [ ] **Batch area sweep** — Add a vectorized wrapper in `itm/itm.py` (or a helper module) that accepts a list of distances and runs `predict_area` for each, returning a list of `PropagationResult`. Useful for coverage vs. distance plots.

---

## Medium effort

- [ ] **Confidence / reliability variability mode** — The README documents `confidence` and `reliability` as alternative inputs to `time/location/situation`, but the Python API does not expose this. Add a mapping layer in `itm/itm.py` so callers can pass these directly, matching the original ITM interface.

- [ ] **Antenna gain parameters in API** — Add optional `tx_antenna_gain_dbi=0.0` and `rx_antenna_gain_dbi=0.0` to `predict_p2p` and `predict_area`. Add `A_eff__db` field to `PropagationResult` (= `A__db - tx_gain - rx_gain`). Keep `A__db` as the isotropic baseline for transparency.
  - Files: `itm/models.py`, `itm/itm.py`

- [ ] **Ground clutter — clutter height correction** — Add a wrapper (e.g. `itm/clutter.py`) that accepts a clutter environment type per terminal (`open`, `rural`, `suburban`, `urban`, `dense_urban`, `forest`) and reduces the effective antenna height before calling `predict_p2p` or `predict_area`. Reference clutter heights: rural 4 m, suburban 9 m, urban 20 m, dense urban 30 m, forest 15 m. This feeds back into the ITM geometry (horizon angles, diffraction) rather than being a blind additive correction.

- [ ] **P.2108 integration — Height Gain Terminal Correction** (`proplib-p2108`) — For `predict_p2p`, apply `P2108.HeightGainTerminalCorrectionModel(f__ghz, h__meter, w_s__meter, R__meter, clutter_type)` per terminal and add the result to `A__db`. Frequency range: 0.03–3 GHz. Key inputs: clutter height `R__meter` (suburban ~9 m, urban ~15–20 m, dense urban ~25–30 m) and street width `w_s__meter` (residential ~10–15 m, arterial ~20–30 m).

- [ ] **P.2108 integration — Terrestrial Statistical Model** (`proplib-p2108`) — For `predict_area`, apply `P2108.TerrestrialStatisticalModel(f__ghz, d__km, p)` and add to `A__db`. Match `p` to the `location` percentage used in `predict_area` for statistical consistency. Frequency range: 0.5–67 GHz.

- [ ] **delta_h estimation utility** — `compute_delta_h()` already exists in `terrain.py` but is internal. Expose a public helper that estimates `delta_h__meter` from a coarse elevation profile for a given region, to assist area-mode callers who must currently supply this manually.

---

## High effort

- [ ] **SRTM terrain ingestion** — Add `itm/terrain_io.py` with a helper that accepts start/end coordinates (lat/lon), fetches SRTM elevation data (via `elevation` or `rasterio`), and returns a `TerrainProfile` ready for `predict_p2p`. This makes the library self-contained for real-world paths without manual profile construction.

- [ ] **Antenna pattern support** — Extend the antenna gain feature to support directional/angle-dependent gain. Use `theta_hzn` from `IntermediateValues` as the path elevation angle at each terminal. Accept a gain function or lookup table indexed by elevation angle (degrees → dBi). Relevant for Yagi, parabolic, and phased-array antennas.

---

## References

- `proplib-p2108`: `pip install proplib-p2108` — [NTIA/p2108-python](https://github.com/NTIA/p2108-python)
- P.2108 docs: [ITS Propagation Library Wiki](https://ntia.github.io/propagation-library-wiki/models/P2108/)
- SRTM data: `pip install elevation` or `rasterio`
