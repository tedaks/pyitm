# tests/test_validation.py
"""Input validation at the entry points.

The C++ has no finiteness checks: NaN passes every range comparison and yields nan,
a plausible wrong answer (N_0=NaN -> 99.58 dB, success) or a segfault (resolution 0
or NaN). pyitm-ng rejects such input with a clear error instead (documented deviation,
CLAUDE.md "Fidelity policy"). None of this changes results for valid input.
"""

import math

import numpy as np
import pytest

from pyitm_ng import (
    Climate,
    MDVar,
    Polarization,
    SitingCriteria,
    TerrainProfile,
    Warnings,
    predict_area,
    predict_area_cr,
    predict_p2p,
    predict_p2p_cr,
)

NAN, INF = math.nan, math.inf


def _pfl(n=99, res=100.0, elev=None):
    return [float(n), res] + (elev if elev is not None else [float(i % 7) for i in range(n + 1)])


P2P = dict(
    h_tx__meter=10.0, h_rx__meter=2.0, climate=Climate.CONTINENTAL_TEMPERATE, N_0=301.0,
    f__mhz=230.0, pol=Polarization.VERTICAL, epsilon=15.0, sigma=0.008,
    mdvar=MDVar.MOBILE + 10, time=50.0, location=50.0, situation=50.0,
)
AREA = dict(
    h_tx__meter=10.0, h_rx__meter=2.0, tx_siting=SitingCriteria.CAREFUL,
    rx_siting=SitingCriteria.RANDOM, d__km=50.0, delta_h__meter=90.0,
    climate=Climate.CONTINENTAL_TEMPERATE, N_0=301.0, f__mhz=230.0,
    pol=Polarization.VERTICAL, epsilon=15.0, sigma=0.008, mdvar=MDVar.SINGLE_MESSAGE,
    time=50.0, location=50.0, situation=50.0,
)


def p2p(**kw):
    return predict_p2p(terrain=kw.pop("terrain", TerrainProfile.from_pfl(_pfl())), **{**P2P, **kw})


P2P_FLOATS = ["h_tx__meter", "h_rx__meter", "N_0", "f__mhz", "epsilon", "sigma", "time", "location", "situation"]
AREA_FLOATS = P2P_FLOATS + ["d__km", "delta_h__meter"]


@pytest.mark.parametrize("bad", [NAN, INF, -INF])
@pytest.mark.parametrize("name", P2P_FLOATS)
def test_p2p_non_finite_rejected(name, bad):
    with pytest.raises(ValueError, match=f"^{name}=.* must be finite"):
        p2p(**{name: bad})


@pytest.mark.parametrize("bad", [NAN, INF])
@pytest.mark.parametrize("name", AREA_FLOATS)
def test_area_non_finite_rejected(name, bad):
    with pytest.raises(ValueError, match=f"^{name}=.* must be finite"):
        predict_area(**{**AREA, name: bad})


@pytest.mark.parametrize("name", ["confidence", "reliability"])
def test_cr_non_finite_rejected(name):
    cr = {"confidence": 50.0, "reliability": 50.0, name: NAN}
    base = {k: v for k, v in P2P.items() if k not in ("time", "location", "situation")}
    with pytest.raises(ValueError, match="must be finite"):
        predict_p2p_cr(terrain=TerrainProfile.from_pfl(_pfl()), **base, **cr)
    abase = {k: v for k, v in AREA.items() if k not in ("time", "location", "situation")}
    with pytest.raises(ValueError, match="must be finite"):
        predict_area_cr(**abase, **cr)


@pytest.mark.parametrize("bad", [NAN, INF, -INF])
def test_non_finite_elevation_rejected_with_index(bad):
    elev = [0.0] * 100
    elev[37] = bad
    with pytest.raises(ValueError, match="1 non-finite value.*first at index 37"):
        TerrainProfile.from_pfl(_pfl(elev=elev))
    with pytest.raises(ValueError, match="first at index 37"):
        TerrainProfile(elevations=np.array(elev), resolution=100.0)


@pytest.mark.parametrize("res, err", [(0.0, "must be > 0"), (-100.0, "must be > 0"),
                                      (NAN, "must be finite"), (INF, "must be finite")])
def test_bad_resolution_rejected(res, err):
    # resolution 0 or NaN segfaults the C++
    with pytest.raises(ValueError, match=err):
        TerrainProfile.from_pfl(_pfl(res=res))


@pytest.mark.parametrize("header", [NAN, 0.0, -5.0, 99.5])
def test_bad_pfl_header_rejected(header):
    with pytest.raises(ValueError, match="pfl\\[0\\]"):
        TerrainProfile.from_pfl([header, 100.0] + [0.0] * 100)


def test_truncated_pfl_rejected():
    with pytest.raises(ValueError, match="declares 99 intervals .100 elevation points. but only 60"):
        TerrainProfile.from_pfl([99.0, 100.0] + [0.0] * 60)


@pytest.mark.parametrize("name, bad", [
    ("mdvar", 2.7), ("mdvar", "2"), ("mdvar", 12.0), ("mdvar", True),
    ("climate", 5.9), ("climate", "5"), ("pol", 1.5), ("pol", None),
])
def test_enum_like_args_must_be_integers(name, bad):
    with pytest.raises(TypeError, match=f"^{name} must be an integer or enum member"):
        p2p(**{name: bad})


@pytest.mark.parametrize("name, bad", [("tx_siting", 1.0), ("rx_siting", "0")])
def test_siting_must_be_integer(name, bad):
    with pytest.raises(TypeError, match=f"^{name} must be an integer"):
        predict_area(**{**AREA, name: bad})


@pytest.mark.parametrize("name, bad", [("h_tx__meter", "10"), ("f__mhz", None), ("N_0", True)])
def test_float_args_must_be_real_numbers(name, bad):
    with pytest.raises(TypeError, match=f"^{name} must be a real number"):
        p2p(**{name: bad})


def test_integer_like_values_accepted():
    # plain ints, numpy ints and enum arithmetic are all fine, and give the same answer
    ref = p2p().A__db
    assert p2p(mdvar=12, climate=5, pol=1).A__db == ref
    assert p2p(mdvar=np.int64(12), climate=np.int32(5), pol=np.int8(1)).A__db == ref
    assert p2p(h_tx__meter=10, N_0=np.float32(301.0)).A__db == ref


def test_warnings_is_flag_enum():
    r = p2p(h_rx__meter=0.8)  # below 1 m: RX terminal height warning
    assert isinstance(r.warnings, Warnings)
    assert Warnings.RX_TERMINAL_HEIGHT in r.warnings
    assert r.warnings == int(r.warnings)  # still an int for existing callers


def test_terrain_profile_is_immutable_and_hashable():
    elev = np.arange(100.0)
    t = TerrainProfile(elevations=elev, resolution=100.0)
    elev[0] = 999.0  # the caller's array is copied, not aliased
    assert t.elevations[0] == 0.0
    with pytest.raises(ValueError, match="read-only"):
        t.elevations[0] = 1.0
    same = TerrainProfile.from_pfl([99.0, 100.0] + list(np.arange(100.0)))
    assert t == same and hash(t) == hash(same)
    assert t != TerrainProfile(elevations=np.arange(100.0), resolution=50.0)
    assert len({t, same}) == 1
