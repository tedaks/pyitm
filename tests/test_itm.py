# tests/test_itm.py
import pytest
import numpy as np
from itm import predict_p2p, predict_area
from itm.models import (
    Climate,
    Polarization,
    MDVar,
    SitingCriteria,
    TerrainProfile,
    PropagationResult,
)


def make_flat_terrain(n=100, resolution=100.0, elevation=0.0):
    elevs = np.full(n + 1, elevation)
    return TerrainProfile(elevations=elevs, resolution=resolution)


def test_predict_p2p_returns_result():
    terrain = make_flat_terrain()
    result = predict_p2p(
        h_tx__meter=10.0,
        h_rx__meter=1.0,
        terrain=terrain,
        climate=Climate.CONTINENTAL_TEMPERATE,
        N_0=301.0,
        f__mhz=230.0,
        pol=Polarization.VERTICAL,
        epsilon=15.0,
        sigma=0.008,
        mdvar=12,
        time=50.0,
        location=17.0,
        situation=23.0,
    )
    assert isinstance(result, PropagationResult)
    assert isinstance(result.A__db, float)
    assert result.intermediate is None


def test_predict_p2p_intermediate_values():
    terrain = make_flat_terrain()
    result = predict_p2p(
        h_tx__meter=10.0,
        h_rx__meter=1.0,
        terrain=terrain,
        climate=Climate.CONTINENTAL_TEMPERATE,
        N_0=301.0,
        f__mhz=230.0,
        pol=Polarization.VERTICAL,
        epsilon=15.0,
        sigma=0.008,
        mdvar=12,
        time=50.0,
        location=17.0,
        situation=23.0,
        return_intermediate=True,
    )
    assert result.intermediate is not None
    assert result.intermediate.d__km == pytest.approx(10.0, rel=1e-3)


def test_predict_p2p_invalid_height():
    terrain = make_flat_terrain()
    with pytest.raises(ValueError, match="h_tx"):
        predict_p2p(
            h_tx__meter=0.1,  # below minimum 0.5m
            h_rx__meter=1.0,
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


def test_predict_area_returns_result():
    result = predict_area(
        h_tx__meter=10.0,
        h_rx__meter=1.0,
        tx_siting=SitingCriteria.RANDOM,
        rx_siting=SitingCriteria.RANDOM,
        d__km=16.0,
        delta_h__meter=0.0,
        climate=Climate.CONTINENTAL_TEMPERATE,
        N_0=301.0,
        f__mhz=230.0,
        pol=Polarization.HORIZONTAL,
        epsilon=15.0,
        sigma=0.008,
        mdvar=0,
        time=87.0,
        location=50.0,
        situation=50.0,
    )
    assert isinstance(result, PropagationResult)
    assert result.A__db > 0
