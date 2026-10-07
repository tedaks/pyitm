# pyitm_ng/terrain.py
from __future__ import annotations
import math
import numpy as np
import numpy.typing as npt
from pyitm_ng._cfloat import c_exp, c_fdim, c_max, c_min, c_sin, c_sqrt, sq
from pyitm_ng._constants import PI, H_3__meter
from pyitm_ng.models import TerrainProfile
from pyitm_ng.variability import linear_least_squares_fit


def find_horizons(
    elevations: npt.NDArray[np.float64],
    resolution: float,
    h__meter: tuple[float, float],
    a_e__meter: float,
) -> tuple[list[float], list[float]]:
    """Compute radio horizon angles and distances for both terminals.

    [TN101, Eq 6.15]
    Returns (theta_hzn[2], d_hzn__meter[2]).
    """
    np_ = len(elevations) - 1
    xi = resolution
    d__meter = np_ * xi

    z_tx = float(elevations[0]) + h__meter[0]
    z_rx = float(elevations[np_]) + h__meter[1]

    # Initial horizon angles assuming line-of-sight
    theta_hzn = [
        (z_rx - z_tx) / d__meter - d__meter / (2.0 * a_e__meter),
        -(z_rx - z_tx) / d__meter - d__meter / (2.0 * a_e__meter),
    ]
    d_hzn__meter = [d__meter, d__meter]

    # FindHorizons.cpp: for (i = 1; i < np; i++) runs zero times for a 1-interval
    # (2-point) profile; np.argmax would raise on the empty interior.
    if np_ < 2:
        return theta_hzn, d_hzn__meter

    # Vectorized computation of horizon angles.
    # Distances are built by sequential accumulation (d_tx += xi, d_rx -= xi) as in
    # the C++ reference, not as indices * xi: the two differ in the last bit, and
    # downstream int() truncation in linear_least_squares_fit can turn that into a
    # different index (up to ~0.9 dB in A__db).
    indices = np.arange(1, np_)
    d_tx_arr = np.cumsum(np.full(np_ - 1, xi))
    d_rx_arr = np.subtract.accumulate(np.concatenate(([d__meter], np.full(np_ - 1, xi))))[1:]

    theta_tx_arr = (elevations[indices] - z_tx) / d_tx_arr - d_tx_arr / (2.0 * a_e__meter)
    theta_rx_arr = -(z_rx - elevations[indices]) / d_rx_arr - d_rx_arr / (2.0 * a_e__meter)

    # Find indices of maximum angles
    idx_max_tx = np.argmax(theta_tx_arr)
    idx_max_rx = np.argmax(theta_rx_arr)

    # Update results if horizon angles exceed initial LOS values
    if theta_tx_arr[idx_max_tx] > theta_hzn[0]:
        theta_hzn[0] = float(theta_tx_arr[idx_max_tx])
        d_hzn__meter[0] = float(d_tx_arr[idx_max_tx])

    if theta_rx_arr[idx_max_rx] > theta_hzn[1]:
        theta_hzn[1] = float(theta_rx_arr[idx_max_rx])
        d_hzn__meter[1] = float(d_rx_arr[idx_max_rx])

    return theta_hzn, d_hzn__meter


def compute_delta_h(
    elevations: npt.NDArray[np.float64],
    resolution: float,
    d_start__meter: float,
    d_end__meter: float,
) -> float:
    """Compute terrain irregularity parameter delta_h between d_start and d_end.

    Uses the inter-decile range of deviations from a linear fit. [ERL 79-ITS 67, Eqn 3]
    """
    np_ = len(elevations) - 1

    x_start_idx = d_start__meter / resolution
    x_end_idx = d_end__meter / resolution

    if x_end_idx - x_start_idx < 2.0:
        return 0.0

    p10 = int(0.1 * (x_end_idx - x_start_idx + 8.0))
    p10 = min(max(4, p10), 25)

    n = 10 * p10 - 5
    p90 = n - p10

    np_s = float(n - 1)
    x_step = (x_end_idx - x_start_idx) / np_s

    i = int(x_start_idx)
    x_pos = x_start_idx - float(i + 1)  # in range (-1, 0]

    # C++: while (x_pos > 0 && i + 1 < np) { x_pos -= 1; i++; }. Every subtraction
    # but the last is exact (x_pos > 1 and 1.0 is a multiple of its ulp), so k
    # repeated -= 1.0 equal one x_pos - k: same bits, without a step per point.
    s_elevations = []
    for _ in range(n):
        if x_pos > 0.0 and (i + 1) < np_:
            k = min(math.ceil(x_pos), np_ - 1 - i)
            x_pos -= float(k)
            i += k
        s_elevations.append(
            float(elevations[i + 1]) + (float(elevations[i + 1]) - float(elevations[i])) * x_pos
        )
        x_pos += x_step

    s_arr = np.array(s_elevations)

    # Fit a line to the resampled terrain (resolution=1.0, so d_start=0, d_end=np_s)
    fit_y1, fit_y2 = linear_least_squares_fit(s_arr, 1.0, 0.0, np_s)
    fit_slope = (fit_y2 - fit_y1) / np_s

    # Residuals with the fitted line stepped in C++ order (ComputeDeltaH.cpp:65-70);
    # the closed form y1 + slope*j is not bit-identical to repeated += slope.
    # np.add.accumulate steps fit_y1 += fit_slope strictly in sequence.
    fit_line = np.add.accumulate(np.concatenate(([fit_y1], np.full(n - 1, fit_slope))))
    diffs = s_arr - fit_line

    # q10: p10-th largest value (≈ 90th percentile)
    q10 = float(-np.partition(-diffs, p10 - 1)[p10 - 1])
    # q90: (p90+1)-th largest value (≈ 10th percentile)
    q90 = float(-np.partition(-diffs, p90)[p90])

    delta_h_d__meter = q10 - q90

    return delta_h_d__meter / (
        1.0 - 0.8 * c_exp(-(d_end__meter - d_start__meter) / 50e3)
    )


def quick_pfl(
    terrain: TerrainProfile,
    gamma_e: float,
    h__meter: tuple[float, float],
) -> tuple[list[float], list[float], list[float], float, float]:
    """Extract path parameters from the terrain profile.

    Returns (theta_hzn[2], d_hzn__meter[2], h_e__meter[2], delta_h__meter, d__meter).
    """
    elevations = terrain.elevations
    resolution = terrain.resolution
    np_ = len(elevations) - 1

    d__meter = np_ * resolution
    a_e__meter = 1.0 / gamma_e

    theta_hzn, d_hzn__meter = find_horizons(
        elevations, resolution, h__meter, a_e__meter
    )

    # Start/end of terrain region to analyse (ignore ~15x tower height near each terminal)
    d_start__meter = c_min(15.0 * h__meter[0], 0.1 * d_hzn__meter[0])
    d_end__meter = d__meter - c_min(15.0 * h__meter[1], 0.1 * d_hzn__meter[1])

    delta_h__meter = compute_delta_h(
        elevations, resolution, d_start__meter, d_end__meter
    )

    h_e__meter = [0.0, 0.0]

    if d_hzn__meter[0] + d_hzn__meter[1] > 1.5 * d__meter:
        # Well within line-of-sight: use full-path linear fit
        fit_tx, fit_rx = linear_least_squares_fit(
            elevations, resolution, d_start__meter, d_end__meter
        )
        h_e__meter[0] = h__meter[0] + c_fdim(float(elevations[0]), fit_tx)
        h_e__meter[1] = h__meter[1] + c_fdim(float(elevations[np_]), fit_rx)

        for i in range(2):
            d_hzn__meter[i] = c_sqrt(2.0 * h_e__meter[i] * a_e__meter) * c_exp(
                -0.07 * c_sqrt(delta_h__meter / c_max(h_e__meter[i], 5.0))
            )

        if d_hzn__meter[0] + d_hzn__meter[1] <= d__meter:
            q = sq(d__meter / (d_hzn__meter[0] + d_hzn__meter[1]))
            for i in range(2):
                h_e__meter[i] *= q
                d_hzn__meter[i] = c_sqrt(
                    2.0 * h_e__meter[i] * a_e__meter
                ) * c_exp(
                    -0.07 * c_sqrt(delta_h__meter / c_max(h_e__meter[i], 5.0))
                )

        for i in range(2):
            q = c_sqrt(2.0 * h_e__meter[i] * a_e__meter)
            theta_hzn[i] = (
                0.65 * delta_h__meter * (q / d_hzn__meter[i] - 1.0)
                - 2.0 * h_e__meter[i]
            ) / q
    else:
        # Beyond line-of-sight: fit near each terminal separately
        fit_tx, _ = linear_least_squares_fit(
            elevations, resolution, d_start__meter, 0.9 * d_hzn__meter[0]
        )
        h_e__meter[0] = h__meter[0] + c_fdim(float(elevations[0]), fit_tx)

        _, fit_rx = linear_least_squares_fit(
            elevations, resolution, d__meter - 0.9 * d_hzn__meter[1], d_end__meter
        )
        h_e__meter[1] = h__meter[1] + c_fdim(float(elevations[np_]), fit_rx)

    return theta_hzn, d_hzn__meter, h_e__meter, delta_h__meter, d__meter


def initialize_area(
    site_criteria: tuple[int, int],
    gamma_e: float,
    delta_h__meter: float,
    h__meter: tuple[float, float],
) -> tuple[list[float], list[float], list[float]]:
    """Initialize area mode: compute effective heights, horizon distances, horizon angles.

    Returns (h_e__meter[2], d_hzn__meter[2], theta_hzn[2]).
    """
    h_e__meter = [0.0, 0.0]
    d_hzn__meter = [0.0, 0.0]
    theta_hzn = [0.0, 0.0]

    for i in range(2):
        if site_criteria[i] == 0:  # RANDOM
            h_e__meter[i] = h__meter[i]
        else:
            B = 4.0 if site_criteria[i] == 1 else 9.0  # CAREFUL vs VERY_CAREFUL

            if h__meter[i] < 5.0:
                B = B * c_sin(0.1 * PI * h__meter[i])

            # [Algorithm, Eqn 3.2]
            h_e__meter[i] = h__meter[i] + (1.0 + B) * c_exp(
                -c_min(20.0, 2.0 * h__meter[i] / c_max(1e-3, delta_h__meter))
            )

        d_Ls__meter = c_sqrt(2.0 * h_e__meter[i] / gamma_e)

        # [Algorithm, Eqn 3.3]
        d_hzn__meter[i] = d_Ls__meter * c_exp(
            -0.07 * c_sqrt(delta_h__meter / c_max(h_e__meter[i], H_3__meter))
        )

        # [Algorithm, Eqn 3.4]
        theta_hzn[i] = (
            0.65 * delta_h__meter * (d_Ls__meter / d_hzn__meter[i] - 1.0)
            - 2.0 * h_e__meter[i]
        ) / d_Ls__meter

    return h_e__meter, d_hzn__meter, theta_hzn
