# itm/variability.py
from __future__ import annotations
import math
import numpy as np


def iccdf(q: float) -> float:
    """Inverse complementary CDF (Abramowitz & Stegun 26.2.23).

    Input q is a probability in (0, 1).
    Returns Q^-1(q): positive for q < 0.5, negative for q > 0.5.
    Error |epsilon(p)| < 4.5e-4.
    """
    C_0, C_1, C_2 = 2.515516, 0.802853, 0.010328
    D_1, D_2, D_3 = 1.432788, 0.189269, 0.001308

    x = q if q <= 0.5 else 1.0 - q
    T_x = math.sqrt(-2.0 * math.log(x))
    zeta_x = ((C_2 * T_x + C_1) * T_x + C_0) / (
        ((D_3 * T_x + D_2) * T_x + D_1) * T_x + 1.0
    )
    Q_q = T_x - zeta_x
    return -Q_q if q > 0.5 else Q_q


def terrain_roughness(d__meter: float, delta_h__meter: float) -> float:
    """Compute delta_h_d: terrain roughness at distance d. [ERL 79-ITS 67, Eqn 3]"""
    return delta_h__meter * (1.0 - 0.8 * math.exp(-d__meter / 50e3))


def sigma_h_function(delta_h__meter: float) -> float:
    """RMS deviation of terrain within first Fresnel zone. [ERL 79-ITS 67, Eqn 3.6a]"""
    return 0.78 * delta_h__meter * math.exp(-0.5 * delta_h__meter**0.25)


def linear_least_squares_fit(
    elevations: np.ndarray,
    resolution: float,
    d_start: float,
    d_end: float,
) -> tuple[float, float]:
    """Fit a line to terrain elevations between d_start and d_end (in meters).

    elevations: 1-D array of elevation values, elevations[i] = height at index i.
                len(elevations) - 1 is the number of intervals (pfl[0]).
    resolution: spacing between elevation points in meters (pfl[1]).
    d_start, d_end: distance bounds in meters.

    Returns (fit_y1, fit_y2): fitted elevation at TX end and RX end respectively.
    """
    np_ = len(elevations) - 1  # number of intervals

    # fdim(x, y) = max(x - y, 0)
    i_start = int(max(d_start / resolution - 0.0, 0.0))
    i_end = np_ - int(max(np_ - d_end / resolution, 0.0))

    if i_end <= i_start:
        i_start = int(max(i_start - 1.0, 0.0))
        i_end = np_ - int(max(np_ - (i_end + 1.0), 0.0))

    x_length = float(i_end - i_start)
    mid_shifted_index = -0.5 * x_length
    mid_shifted_end = i_end + mid_shifted_index

    sum_y = 0.5 * (elevations[i_start] + elevations[i_end])
    scaled_sum_y = 0.5 * (elevations[i_start] - elevations[i_end]) * mid_shifted_index

    for i in range(2, int(x_length) + 1):
        i_start += 1
        mid_shifted_index += 1.0
        sum_y += elevations[i_start]
        scaled_sum_y += elevations[i_start] * mid_shifted_index

    sum_y /= x_length
    scaled_sum_y = scaled_sum_y * 12.0 / ((x_length * x_length + 2.0) * x_length)

    fit_y1 = sum_y - scaled_sum_y * mid_shifted_end
    fit_y2 = sum_y + scaled_sum_y * (np_ - mid_shifted_end)

    return fit_y1, fit_y2


def curve(
    c1: float,
    c2: float,
    x1: float,
    x2: float,
    x3: float,
    d_e__meter: float,
) -> float:
    """Curve helper for TN101v2 Eqn III.69 & III.70."""
    r = d_e__meter / x1
    return (c1 + c2 / (1.0 + ((d_e__meter - x2) / x3) ** 2)) * (r * r) / (1.0 + r * r)
