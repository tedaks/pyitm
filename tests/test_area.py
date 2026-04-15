# tests/test_area.py
"""
Validate predict_area against all reference cases in area.csv.
Tolerance: 0.01 dB.
"""

import csv
import pathlib
import pytest
from itm import predict_area, Climate, Polarization, SitingCriteria

ROOT = pathlib.Path(__file__).parent.parent


def load_area_cases():
    cases = []
    with open(ROOT / "area.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append({k: float(v) for k, v in row.items()})
    return cases


AREA_CASES = load_area_cases()


@pytest.mark.parametrize("idx", range(len(AREA_CASES)))
def test_area_reference(idx):
    c = AREA_CASES[idx]
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
    assert result.A__db == pytest.approx(c["A__db"], abs=0.01), (
        f"Case {idx}: expected {c['A__db']:.2f} dB, got {result.A__db:.2f} dB"
    )
