# tests/test_models.py
from itm.models import (
    Climate,
    TerrainProfile,
    PropagationResult,
)


def test_climate_values():
    assert Climate.EQUATORIAL == 1
    assert Climate.MARITIME_TEMPERATE_SEA == 7


def test_terrain_profile_from_pfl():
    pfl = [3.0, 100.0, 10.0, 20.0, 15.0, 25.0, 12.0]
    # np=3, resolution=100m, elevations=[10,20,15,25] (np+1 = 4 values; trailing 12.0 ignored)
    tp = TerrainProfile.from_pfl(pfl)
    assert tp.resolution == 100.0
    assert len(tp.elevations) == 4  # np+1 = 4 points
    assert tp.elevations[0] == 10.0
    assert tp.elevations[3] == 25.0


def test_propagation_result_defaults():
    r = PropagationResult(A__db=142.5, warnings=0)
    assert r.intermediate is None
