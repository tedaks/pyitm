# tests/test_p2p.py
"""
Validate predict_p2p against all reference cases in p2p.csv + pfls.csv.
Each row in p2p.csv corresponds to the same-numbered row in pfls.csv.
Tolerance: 0.01 dB.
"""

import csv
import pathlib
import pytest
from pyitm_ng import predict_p2p, Climate, Polarization, TerrainProfile

ROOT = pathlib.Path(__file__).parent.parent


def load_p2p_cases():
    cases = []
    with open(ROOT / "p2p.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append({k: float(v) for k, v in row.items()})
    return cases


def load_pfls():
    profiles = []
    with open(ROOT / "pfls.csv") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            vals = [float(v) for v in line.split(",")]
            profiles.append(TerrainProfile.from_pfl(vals))
    return profiles


P2P_CASES = load_p2p_cases()
PFL_PROFILES = load_pfls()


@pytest.mark.parametrize("idx", range(len(P2P_CASES)))
def test_p2p_reference(idx):
    c = P2P_CASES[idx]
    terrain = PFL_PROFILES[idx]
    result = predict_p2p(
        h_tx__meter=c["h_tx__meter"],
        h_rx__meter=c["h_rx__meter"],
        terrain=terrain,
        climate=Climate(int(c["climate"])),
        N_0=c["N_0"],
        f__mhz=c["f__mhz"],
        pol=Polarization(int(c["pol"])),
        epsilon=c["epsilon"],
        sigma=c["sigma"],
        mdvar=int(c["mdvar"]),
        time=c["time"],
        location=c["location"],
        situation=c["situation"],
    )
    assert result.A__db == pytest.approx(c["A__db"], abs=0.01), (
        f"Case {idx}: expected {c['A__db']:.2f} dB, got {result.A__db:.2f} dB"
    )


def test_p2p_horizon_distance_rounding_regression():
    # Path where i * xi and accumulated xi differ in the last bit and int()
    # truncation in linear_least_squares_fit picks a different index; the
    # vectorized find_horizons was 1.65 dB off. Expected value from NTIA/itm
    # C++ (ITM_P2P_TLS, master 183ad95).
    pfl = [11.0, 146.1, 377.0, 206.0, 139.0, 211.0, 329.0, 141.0, 298.0, 175.0, 156.0, 147.0, 375.0, 72.0]
    result = predict_p2p(
        h_tx__meter=50.0,
        h_rx__meter=1.0,
        terrain=TerrainProfile.from_pfl(pfl),
        climate=Climate(5),
        N_0=301.0,
        f__mhz=100.0,
        pol=Polarization(1),
        epsilon=15.0,
        sigma=0.005,
        mdvar=12,
        time=50.0,
        location=50.0,
        situation=50.0,
    )
    assert result.A__db == pytest.approx(128.2976016591739, abs=0.01)


@pytest.mark.parametrize("idx", range(len(P2P_CASES)))
def test_p2p_returns_python_floats(idx):
    """numpy scalars must not leak into the scalar code path: np.complex128 division
    is not the C++/CPython algorithm and changes the last bit (LineOfSightLoss)."""
    c = P2P_CASES[idx]
    result = predict_p2p(
        h_tx__meter=c["h_tx__meter"], h_rx__meter=c["h_rx__meter"], terrain=PFL_PROFILES[idx],
        climate=Climate(int(c["climate"])), N_0=c["N_0"], f__mhz=c["f__mhz"],
        pol=Polarization(int(c["pol"])), epsilon=c["epsilon"], sigma=c["sigma"],
        mdvar=int(c["mdvar"]), time=c["time"], location=c["location"],
        situation=c["situation"], return_intermediate=True,
    )
    iv = result.intermediate
    for v in (result.A__db, iv.A_ref__db, iv.delta_h__meter, *iv.h_e__meter, *iv.theta_hzn, *iv.d_hzn__meter):
        assert type(v) is float, type(v)
