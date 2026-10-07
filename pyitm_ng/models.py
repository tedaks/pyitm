# pyitm_ng/models.py
from __future__ import annotations
import math
import numbers
import operator
from dataclasses import dataclass
from enum import IntFlag, IntEnum
from typing import Any
import numpy as np
import numpy.typing as npt


def require_finite(name: str, value: Any) -> float:
    """Return value as float; TypeError if not a real number, ValueError if nan/inf.

    Deliberate deviation from the C++, which has no such check: there NaN slips through
    every range comparison and yields nan, a plausible wrong answer, or a crash.
    """
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__} {value!r}")
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{name}={v} must be finite")
    return v


def require_int(name: str, value: Any) -> int:
    """Return value as int; TypeError unless it is an integer (int, IntEnum, numpy int).

    Rejects 2.7 or "2" instead of truncating them, as int() would.
    """
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer or enum member, got bool {value!r}")
    try:
        return operator.index(value)
    except TypeError:
        raise TypeError(
            f"{name} must be an integer or enum member, got {type(value).__name__} {value!r}"
        ) from None


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


class Warnings(IntFlag):
    TX_TERMINAL_HEIGHT = 0x0001
    RX_TERMINAL_HEIGHT = 0x0002
    FREQUENCY = 0x0004
    PATH_DISTANCE_TOO_BIG_1 = 0x0008
    PATH_DISTANCE_TOO_BIG_2 = 0x0010
    PATH_DISTANCE_TOO_SMALL_1 = 0x0020
    PATH_DISTANCE_TOO_SMALL_2 = 0x0040
    TX_HORIZON_ANGLE = 0x0080
    RX_HORIZON_ANGLE = 0x0100
    TX_HORIZON_DISTANCE_1 = 0x0200
    RX_HORIZON_DISTANCE_1 = 0x0400
    TX_HORIZON_DISTANCE_2 = 0x0800
    RX_HORIZON_DISTANCE_2 = 0x1000
    EXTREME_VARIABILITIES = 0x2000
    SURFACE_REFRACTIVITY = 0x4000
    NONE = 0


@dataclass(frozen=True, eq=False)
class TerrainProfile:
    """Terrain elevation profile in PFL format.

    Validated on construction: at least 2 elevation points, every elevation finite
    (DEM no-data cells often arrive as NaN; fill or drop them first), resolution
    finite and > 0. The elevations are stored as a read-only float64 copy, so the
    profile is immutable; it compares and hashes by value.
    """

    elevations: npt.NDArray[np.float64]
    resolution: float

    def __post_init__(self) -> None:
        elevations = np.array(self.elevations, dtype=np.float64)  # copy, never a view
        if elevations.ndim != 1 or elevations.size < 2:
            raise ValueError(
                f"terrain must be a 1-D profile of at least 2 elevation points, got shape {elevations.shape}"
            )
        bad = np.flatnonzero(~np.isfinite(elevations))
        if bad.size:
            raise ValueError(
                f"terrain elevations must be finite: {bad.size} non-finite value(s), "
                f"first at index {int(bad[0])} ({elevations[bad[0]]}); fill DEM no-data cells first"
            )
        resolution = require_finite("resolution", self.resolution)
        if resolution <= 0.0:
            raise ValueError(f"resolution={resolution} must be > 0")
        elevations.setflags(write=False)
        object.__setattr__(self, "elevations", elevations)
        object.__setattr__(self, "resolution", resolution)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TerrainProfile):
            return NotImplemented
        return self.resolution == other.resolution and np.array_equal(self.elevations, other.elevations)

    def __hash__(self) -> int:
        return hash((self.resolution, self.elevations.tobytes()))

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
        header = require_finite("PFL interval count pfl[0]", pfl[0])
        if header != int(header) or header < 1:
            raise ValueError(f"PFL interval count pfl[0]={header} must be a whole number >= 1")
        np_ = int(header)
        available = len(pfl) - 2
        if available < np_ + 1:
            # The C++ would read past the end of the array; computing a shorter path
            # than the caller described is not an answer for their link either.
            raise ValueError(
                f"PFL header declares {np_} intervals ({np_ + 1} elevation points) "
                f"but only {available} values follow"
            )
        # Values beyond np_ + 1 are ignored, as in the C++.
        return cls(elevations=np.asarray(pfl[2 : np_ + 3], dtype=float), resolution=pfl[1])


@dataclass(frozen=True)
class IntermediateValues:
    theta_hzn: tuple[float, float]
    d_hzn__meter: tuple[float, float]
    h_e__meter: tuple[float, float]
    N_s: float
    delta_h__meter: float
    A_ref__db: float
    A_fs__db: float
    d__km: float
    mode: PropMode


@dataclass(frozen=True)
class PropagationResult:
    A__db: float
    warnings: Warnings
    intermediate: IntermediateValues | None = None
