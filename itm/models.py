# itm/models.py
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
import numpy as np


class Climate(IntEnum):
    EQUATORIAL = 1
    CONTINENTAL_SUBTROPICAL = 2
    MARITIME_SUBTROPICAL = 3
    DESERT = 4
    CONTINENTAL_TEMPERATE = 5
    MARITIME_TEMPERATE_LAND = 6
    MARITIME_TEMPERATE_SEA = 7


class Polarization(IntEnum):
    HORIZONTAL = 0
    VERTICAL = 1


class MDVar(IntEnum):
    SINGLE_MESSAGE = 0
    ACCIDENTAL = 1
    MOBILE = 2
    BROADCAST = 3


class PropMode(IntEnum):
    LINE_OF_SIGHT = 1
    DIFFRACTION = 2
    TROPOSCATTER = 3


class SitingCriteria(IntEnum):
    RANDOM = 0
    CAREFUL = 1
    VERY_CAREFUL = 2


@dataclass
class TerrainProfile:
    """Terrain elevation profile in PFL format."""

    elevations: np.ndarray  # elevation above sea level, meters; shape (np+1,)
    resolution: float  # point spacing, meters

    @classmethod
    def from_pfl(cls, pfl: list[float]) -> TerrainProfile:
        """Construct from raw C-style PFL array.

        pfl[0]   = number of elevation intervals (np), so np+1 points total
        pfl[1]   = resolution in meters
        pfl[2+]  = elevation values (np+1 values at pfl[2]..pfl[np+2])
        """
        if len(pfl) < 3:
            raise ValueError(
                f"PFL array must have at least 3 elements (np, resolution, one elevation), got {len(pfl)}"
            )
        np_ = int(pfl[0])
        if np_ < 1:
            raise ValueError(f"PFL interval count must be >= 1, got {np_}")
        resolution = float(pfl[1])
        elevations = np.array(pfl[2 : np_ + 3], dtype=float)
        return cls(elevations=elevations, resolution=resolution)


@dataclass
class IntermediateValues:
    theta_hzn: tuple[float, float]  # terminal horizon angles, radians
    d_hzn__meter: tuple[float, float]  # terminal horizon distances, meters
    h_e__meter: tuple[float, float]  # effective terminal heights, meters
    N_s: float  # surface refractivity, N-Units
    delta_h__meter: float  # terrain irregularity parameter, meters
    A_ref__db: float  # reference attenuation, dB
    A_fs__db: float  # free-space basic transmission loss, dB
    d__km: float  # path distance, km
    mode: PropMode  # propagation mode


@dataclass
class PropagationResult:
    A__db: float  # basic transmission loss, dB
    warnings: int  # warning bitmask
    intermediate: IntermediateValues | None = None
