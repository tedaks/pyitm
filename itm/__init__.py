# itm/__init__.py
"""
Pure-Python port of the ITS Irregular Terrain Model (ITM / Longley-Rice).

Predicts terrestrial radiowave propagation loss for frequencies 20 MHz – 20 GHz.
Public entry points: `predict_p2p` and `predict_area`.

Derived from NTIA's Irregular Terrain Model (ITM). Copyright NTIA.
"""

from itm.itm import predict_p2p, predict_area, predict_p2p_cr, predict_area_cr
from itm.models import (
    Climate,
    Polarization,
    MDVar,
    PropMode,
    SitingCriteria,
    TerrainProfile,
    IntermediateValues,
    PropagationResult,
    Warnings,
)

__version__ = "0.1.0"

__all__ = [
    "predict_p2p",
    "predict_area",
    "predict_p2p_cr",
    "predict_area_cr",
    "Climate",
    "Polarization",
    "MDVar",
    "PropMode",
    "SitingCriteria",
    "TerrainProfile",
    "IntermediateValues",
    "PropagationResult",
    "Warnings",
    "__version__",
]
