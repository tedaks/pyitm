# tests/test_p2p.py
"""
Validate predict_p2p against all reference cases in p2p.csv + pfls.csv.
Each row in p2p.csv corresponds to the same-numbered row in pfls.csv.
Tolerance: 0.01 dB.
"""

import csv
import pathlib
import pytest
from itm import predict_p2p, Climate, Polarization, TerrainProfile

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
