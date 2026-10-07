# pyitm_ng/variability.py
from __future__ import annotations
import math
import numpy as np
import numpy.typing as npt

from pyitm_ng._cfloat import c_exp, c_fdim, c_log, c_pow, c_sqrt, sq
from pyitm_ng._constants import (
    a_9000__meter,
    WN_DENOM,
    THIRD,
    D_SCALE__meter,
    WARN__EXTREME_VARIABILITIES,
)
from pyitm_ng.models import Climate

_ALL_YEAR = (
    (-9.67, -0.62, 1.26, -9.21, -0.62, -0.39, 3.15),
    (12.7, 9.19, 15.5, 9.05, 9.19, 2.86, 857.9),
    (144.9e3, 228.9e3, 262.6e3, 84.1e3, 228.9e3, 141.7e3, 2222.0e3),
    (190.3e3, 205.2e3, 185.2e3, 101.1e3, 205.2e3, 315.9e3, 164.8e3),
    (133.8e3, 143.6e3, 99.8e3, 98.6e3, 143.6e3, 167.4e3, 116.3e3),
)
_BSM1 = (2.13, 2.66, 6.11, 1.98, 2.68, 6.86, 8.51)
_BSM2 = (159.5, 7.67, 6.65, 13.11, 7.16, 10.38, 169.8)
_XSM1 = (762.2e3, 100.4e3, 138.2e3, 139.1e3, 93.7e3, 187.8e3, 609.8e3)
_XSM2 = (123.6e3, 172.5e3, 242.2e3, 132.7e3, 186.8e3, 169.6e3, 119.9e3)
_XSM3 = (94.5e3, 136.4e3, 178.6e3, 193.5e3, 133.5e3, 108.9e3, 106.6e3)
_BSP1 = (2.11, 6.87, 10.08, 3.68, 4.75, 8.58, 8.43)
_BSP2 = (102.3, 15.53, 9.60, 159.3, 8.12, 13.97, 8.19)
_XSP1 = (636.9e3, 138.7e3, 165.3e3, 464.4e3, 93.2e3, 216.0e3, 136.2e3)
_XSP2 = (134.8e3, 143.7e3, 225.7e3, 93.1e3, 135.9e3, 152.0e3, 188.5e3)
_XSP3 = (95.6e3, 98.6e3, 129.7e3, 94.2e3, 113.4e3, 122.7e3, 122.9e3)
_C_D = (1.224, 0.801, 1.380, 1.000, 1.224, 1.518, 1.518)
_Z_D = (1.282, 2.161, 1.282, 20.0, 1.282, 1.282, 1.282)
_BFM1 = (1.0, 1.0, 1.0, 1.0, 0.92, 1.0, 1.0)
_BFM2 = (0.0, 0.0, 0.0, 0.0, 0.25, 0.0, 0.0)
_BFM3 = (0.0, 0.0, 0.0, 0.0, 1.77, 0.0, 0.0)
_BFP1 = (1.0, 0.93, 1.0, 0.93, 0.93, 1.0, 1.0)
_BFP2 = (0.0, 0.31, 0.0, 0.19, 0.31, 0.0, 0.0)
_BFP3 = (0.0, 2.00, 0.0, 1.79, 2.00, 0.0, 0.0)


def iccdf(q: float) -> float:
    """Inverse complementary CDF (Abramowitz & Stegun 26.2.23).

    Input q is a probability in (0, 1).
    Returns Q^-1(q): positive for q < 0.5, negative for q > 0.5.
    Error |epsilon(p)| < 4.5e-4.
    No domain check, as in the C++: q == 0 (reachable when time/location/situation
    is small enough that x / 100 underflows) gives log(0) = -inf and returns nan,
    which Variability() then discards or propagates exactly as the C++ does.
    """
    C_0, C_1, C_2 = 2.515516, 0.802853, 0.010328
    D_1, D_2, D_3 = 1.432788, 0.189269, 0.001308

    x = q if q <= 0.5 else 1.0 - q
    # C log(): log(0) = -inf, log(<0) = nan; math.log raises on both.
    # C log()/sqrt(): log(0) = -inf -> T_x = inf; a negative x gives nan.
    T_x = c_sqrt(-2.0 * c_log(x))
    zeta_x = ((C_2 * T_x + C_1) * T_x + C_0) / (
        ((D_3 * T_x + D_2) * T_x + D_1) * T_x + 1.0
    )
    Q_q = T_x - zeta_x
    return -Q_q if q > 0.5 else Q_q


def terrain_roughness(d__meter: float, delta_h__meter: float) -> float:
    """Compute delta_h_d: terrain roughness at distance d. [ERL 79-ITS 67, Eqn 3]"""
    return delta_h__meter * (1.0 - 0.8 * c_exp(-d__meter / 50e3))


def sigma_h_function(delta_h__meter: float) -> float:
    """RMS deviation of terrain within first Fresnel zone. [ERL 79-ITS 67, Eqn 3.6a]"""
    return 0.78 * delta_h__meter * c_exp(-0.5 * c_pow(delta_h__meter, 0.25))


def linear_least_squares_fit(
    elevations: npt.NDArray[np.float64],
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

    i_start = int(c_fdim(d_start / resolution, 0.0))
    i_end = np_ - int(c_fdim(np_, d_end / resolution))

    if i_end <= i_start:
        i_start = int(c_fdim(i_start, 1.0))
        i_end = np_ - int(c_fdim(np_, i_end + 1.0))

    x_length = float(i_end - i_start)
    mid_shifted_index = -0.5 * x_length
    mid_shifted_end = i_end + mid_shifted_index

    sum_y = 0.5 * (float(elevations[i_start]) + float(elevations[i_end]))
    scaled_sum_y = 0.5 * (float(elevations[i_start]) - float(elevations[i_end])) * mid_shifted_index

    # C++ loop (LinearLeastSquaresFit.cpp): for i = 2..x_length { i_start++;
    # mid_shifted_index++; sum_y += y; scaled_sum_y += y * mid_shifted_index; }.
    # np.add.accumulate adds strictly left to right, so it reproduces the sequential
    # += bit for bit (np.sum / np.dot are pairwise and do not). mid_shifted_index
    # stays a half-integer, so m0 + k is exact, and the products are elementwise.
    n_inner = int(x_length) - 1
    if n_inner > 0:
        inner = np.asarray(elevations[i_start + 1 : i_start + 1 + n_inner], dtype=float)
        shifted = mid_shifted_index + np.arange(1.0, n_inner + 1.0)
        sum_y = float(np.add.accumulate(np.concatenate(([sum_y], inner)))[-1])
        scaled_sum_y = float(
            np.add.accumulate(np.concatenate(([scaled_sum_y], inner * shifted)))[-1]
        )

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
    return (c1 + c2 / (1.0 + sq((d_e__meter - x2) / x3))) * (r * r) / (1.0 + r * r)


def variability(
    time: float,
    location: float,
    situation: float,
    h_e__meter: list[float],
    delta_h__meter: float,
    f__mhz: float,
    d__meter: float,
    A_ref__db: float,
    climate: Climate | int,
    mdvar: int,
) -> tuple[float, int]:
    """Compute variability loss adjustment.

    time, location, situation are percentages 0 < x < 100.
    Returns (F_db, warnings_bits).
    """
    z_T = iccdf(time / 100.0)
    z_L = iccdf(location / 100.0)
    z_S = iccdf(situation / 100.0)

    ci = int(climate) - 1

    wn = f__mhz / WN_DENOM

    d_ex__meter = (
        c_sqrt(2 * a_9000__meter * h_e__meter[0])
        + c_sqrt(2 * a_9000__meter * h_e__meter[1])
        + c_pow(575.7e12 / wn, THIRD)
    )
    d_e__meter = (
        130e3 * d__meter / d_ex__meter
        if d__meter < d_ex__meter
        else 130e3 + d__meter - d_ex__meter
    )

    warnings = 0
    mdvar_internal = mdvar

    plus20 = mdvar_internal >= 20
    if plus20:
        mdvar_internal -= 20

    sigma_S = 0.0 if plus20 else 5.0 + 3.0 * c_exp(-d_e__meter / D_SCALE__meter)

    plus10 = mdvar_internal >= 10
    if plus10:
        mdvar_internal -= 10

    V_med__db = curve(
        _ALL_YEAR[0][ci],
        _ALL_YEAR[1][ci],
        _ALL_YEAR[2][ci],
        _ALL_YEAR[3][ci],
        _ALL_YEAR[4][ci],
        d_e__meter,
    )

    SINGLE_MESSAGE, ACCIDENTAL, MOBILE = 0, 1, 2
    if mdvar_internal == SINGLE_MESSAGE:
        z_T = z_S
        z_L = z_S
    elif mdvar_internal == ACCIDENTAL:
        z_L = z_S
    elif mdvar_internal == MOBILE:
        z_L = z_T

    if math.fabs(z_T) > 3.10 or math.fabs(z_L) > 3.10 or math.fabs(z_S) > 3.10:
        warnings |= WARN__EXTREME_VARIABILITIES

    sigma_L = 0.0
    if not plus10:
        delta_h_d__meter = terrain_roughness(d__meter, delta_h__meter)
        sigma_L = 10.0 * wn * delta_h_d__meter / (wn * delta_h_d__meter + 13.0)
    Y_L = sigma_L * z_L

    q = c_log(0.133 * wn)
    g_minus = _BFM1[ci] + _BFM2[ci] / (sq(_BFM3[ci] * q) + 1.0)
    g_plus = _BFP1[ci] + _BFP2[ci] / (sq(_BFP3[ci] * q) + 1.0)

    sigma_T_minus = (
        curve(_BSM1[ci], _BSM2[ci], _XSM1[ci], _XSM2[ci], _XSM3[ci], d_e__meter)
        * g_minus
    )
    sigma_T_plus = (
        curve(_BSP1[ci], _BSP2[ci], _XSP1[ci], _XSP2[ci], _XSP3[ci], d_e__meter)
        * g_plus
    )

    sigma_TD = _C_D[ci] * sigma_T_plus
    tgtd = (sigma_T_plus - sigma_TD) * _Z_D[ci]

    if z_T < 0.0:
        sigma_T = sigma_T_minus
    elif z_T <= _Z_D[ci]:
        sigma_T = sigma_T_plus
    else:
        sigma_T = sigma_TD + tgtd / z_T
    Y_T = sigma_T * z_T

    Y_S_temp = sq(sigma_S) + sq(Y_T) / (7.8 + sq(z_S)) + sq(Y_L) / (24.0 + sq(z_S))

    if mdvar_internal == SINGLE_MESSAGE:
        Y_R = 0.0
        Y_S = c_sqrt(sq(sigma_T) + sq(sigma_L) + Y_S_temp) * z_S
    elif mdvar_internal == ACCIDENTAL:
        Y_R = Y_T
        Y_S = c_sqrt(sq(sigma_L) + Y_S_temp) * z_S
    elif mdvar_internal == MOBILE:
        Y_R = c_sqrt(sq(sigma_T) + sq(sigma_L)) * z_T
        Y_S = c_sqrt(Y_S_temp) * z_S
    else:
        Y_R = Y_T + Y_L
        Y_S = c_sqrt(Y_S_temp) * z_S

    result = A_ref__db - V_med__db - Y_R - Y_S

    if result < 0.0:
        result = result * (29.0 - result) / (29.0 - 10.0 * result)

    return result, warnings
