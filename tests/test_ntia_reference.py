# tests/test_ntia_reference.py
"""
Validate predict_p2p / predict_area against the reference cases shipped with
NTIA/itm (tests/data/ntia/, copied verbatim from master 183ad95). Unlike the
root CSVs these use real terrain profiles (78-3679 points).

The published A__db values are rounded (2 decimals for p2p, 1 for area), so the
check is that our result rounds to the published value, not a fixed tolerance.
"""

import csv
import pathlib

import pytest

from pyitm_ng import (
    Climate,
    Polarization,
    SitingCriteria,
    TerrainProfile,
    predict_area,
    predict_p2p,
)

DATA = pathlib.Path(__file__).parent / "data" / "ntia"


def load_cases(name):
    with open(DATA / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def decimals(text):
    return len(text.split(".")[1]) if "." in text else 0


def load_pfls():
    with open(DATA / "pfls.csv", encoding="utf-8", newline="") as f:
        return [[float(v) for v in line.split(",")] for line in f if line.strip()]


P2P_CASES = load_cases("p2p.csv")
AREA_CASES = load_cases("area.csv")
PFLS = load_pfls()


@pytest.mark.parametrize("idx", range(len(P2P_CASES)))
def test_p2p_ntia_reference(idx):
    row = P2P_CASES[idx]
    c = {k: float(v) for k, v in row.items()}
    result = predict_p2p(
        h_tx__meter=c["h_tx__meter"],
        h_rx__meter=c["h_rx__meter"],
        terrain=TerrainProfile.from_pfl(PFLS[idx]),
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
    assert round(result.A__db, decimals(row["A__db"])) == c["A__db"], (
        f"Case {idx}: published {row['A__db']} dB, got {result.A__db:.4f} dB"
    )


@pytest.mark.parametrize("idx", range(len(AREA_CASES)))
def test_area_ntia_reference(idx):
    row = AREA_CASES[idx]
    c = {k: float(v) for k, v in row.items()}
    result = predict_area(
        h_tx__meter=c["h_tx__meter"],
        h_rx__meter=c["h_rx__meter"],
        tx_siting=SitingCriteria(int(c["tx_siting_criteria"])),
        rx_siting=SitingCriteria(int(c["rx_siting_criteria"])),
        d__km=c["d__km"],
        delta_h__meter=c["delta_h__meter"],
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
    assert round(result.A__db, decimals(row["A__db"])) == c["A__db"], (
        f"Case {idx}: published {row['A__db']} dB, got {result.A__db:.4f} dB"
    )
