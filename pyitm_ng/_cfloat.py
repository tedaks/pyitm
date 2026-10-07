# pyitm_ng/_cfloat.py
"""C floating-point semantics for the scalar model code.

The NTIA C++ never raises: libm returns -inf / nan / +-inf outside a function's
domain, and the MAX / MIN / DIM macros pick an operand by a plain comparison. On
the model's valid input space these cases do occur (e.g. Vogler's B_0 < 0 at high
antennas gives log10 of a negative number), and the C++ carries on, often clamping
the nan away later. Python's math module raises instead, and the builtins max/min
keep a nan in the *other* argument position. Every scalar libm call and min/max in
propagation.py / terrain.py / variability.py goes through these helpers, so the port
follows the C++ on every path, not just the well-conditioned ones.

On finite, in-domain arguments each helper calls exactly the same libm function as
before (math.log, math.pow, ...), so results there are unchanged bit for bit.
"""

from __future__ import annotations

import math

NAN = math.nan
INF = math.inf


# --- comparisons: the C macros (itm.h) and C99 fdim -------------------------------

def c_max(x: float, y: float) -> float:
    """MAX(x, y) = ((x) > (y)) ? (x) : (y). MAX(nan, y) is y; MAX(x, nan) is nan.
    (Python's max() is the mirror image: it keeps a nan in the first position.)"""
    return x if x > y else y


def c_min(x: float, y: float) -> float:
    """MIN(x, y) = ((x) < (y)) ? (x) : (y)."""
    return x if x < y else y


def c_dim(x: float, y: float) -> float:
    """DIM(x, y) = ((x) > (y)) ? (x - y) : (0): a nan operand gives 0."""
    return x - y if x > y else 0.0


def c_fdim(x: float, y: float) -> float:
    """C99 fdim: nan if either operand is nan, else x - y if x > y, else +0."""
    if x != x or y != y:
        return NAN
    return x - y if x > y else 0.0


# --- arithmetic ---------------------------------------------------------------------

def sq(x: float) -> float:
    """C++ pow(x, 2). GCC folds it to x*x; Python's x**2 calls libm pow(), which is
    not correctly rounded and differs from x*x in the last bit for ~0.1% of inputs."""
    return x * x


def ieee_div(a: float, b: float) -> float:
    """a / b with IEEE-754 semantics: x/0 -> +-inf, 0/0 -> nan (no exception)."""
    if b != 0.0:
        return a / b
    if a != a or a == 0.0:
        return NAN
    return math.copysign(INF, a) * math.copysign(1.0, b)


# --- libm ---------------------------------------------------------------------------

def c_log(x: float) -> float:
    """log(): -inf at 0, nan below 0 (math.log raises on both)."""
    if x > 0.0 or x != x:
        return math.log(x)
    return -INF if x == 0.0 else NAN


def c_log10(x: float) -> float:
    """log10(): -inf at 0, nan below 0."""
    if x > 0.0 or x != x:
        return math.log10(x)
    return -INF if x == 0.0 else NAN


def c_sqrt(x: float) -> float:
    """sqrt(): nan below 0 (sqrt(-0.0) is -0.0, as in C)."""
    return NAN if x < 0.0 else math.sqrt(x)


def c_exp(x: float) -> float:
    """exp(): +inf on overflow (math.exp raises OverflowError)."""
    try:
        return math.exp(x)
    except OverflowError:
        return INF


def c_sin(x: float) -> float:
    """sin(): nan for +-inf (math.sin raises)."""
    return NAN if x in (INF, -INF) else math.sin(x)


def c_cos(x: float) -> float:
    """cos(): nan for +-inf (math.cos raises)."""
    return NAN if x in (INF, -INF) else math.cos(x)


def _odd_integer(y: float) -> bool:
    return math.isfinite(y) and y == math.floor(y) and math.fmod(y, 2.0) != 0.0


def c_pow(x: float, y: float) -> float:
    """pow() (C99 Annex F). Builtin pow / ** return a *complex* number for a negative
    base and fractional exponent, and math.pow raises on that, on 0 ** negative and
    on overflow; C returns nan, +-inf and +-inf respectively."""
    try:
        return math.pow(x, y)
    except OverflowError:
        return -INF if x < 0.0 and _odd_integer(y) else INF
    except ValueError:
        if x == 0.0:  # pole: 0 ** negative
            return -INF if math.copysign(1.0, x) < 0.0 and _odd_integer(y) else INF
        return NAN  # finite negative base, non-integer exponent


def c_csqrt(z: complex) -> complex:
    """std::sqrt(std::complex<double>) as glibc's csqrt computes it
    (math/s_csqrt_template.c), line for line.

    CPython's cmath.sqrt uses a different algorithm. The two agree to the bit when
    Re z > 0, but not for a purely imaginary argument (epsilon == 1 makes
    ep_r - 1 purely imaginary): glibc returns equal real and imaginary parts there,
    which the C++ then rejects as ERROR__GROUND_IMPEDANCE (Re <= |Im|), while
    cmath.sqrt's imaginary part can come out one ulp lower and pass.
    """
    re, im = z.real, z.imag
    re_nan, im_nan = re != re, im != im
    re_inf, im_inf = re in (INF, -INF), im in (INF, -INF)
    if re_nan or im_nan or re_inf or im_inf:
        if im_inf:
            return complex(INF, im)
        if re_inf:
            if re < 0:
                return complex(NAN if im_nan else 0.0, math.copysign(INF, im))
            return complex(re, NAN if im_nan else math.copysign(0.0, im))
        return complex(NAN, NAN)
    dbl_min, dbl_max, mant_dig = 2.2250738585072014e-308, 1.7976931348623157e308, 53
    if im == 0.0:
        if re < 0:
            return complex(0.0, math.copysign(math.sqrt(-re), im))
        return complex(math.fabs(math.sqrt(re)), math.copysign(0.0, im))
    if re == 0.0:
        if math.fabs(im) >= 2 * dbl_min:
            r = math.sqrt(0.5 * math.fabs(im))
        else:
            r = 0.5 * math.sqrt(2 * math.fabs(im))
        return complex(r, math.copysign(r, im))
    scale = 0
    if math.fabs(re) > dbl_max / 4:
        scale = 1
        re, im = math.ldexp(re, -2 * scale), math.ldexp(im, -2 * scale)
    elif math.fabs(im) > dbl_max / 4:
        scale = 1
        re = math.ldexp(re, -2 * scale) if math.fabs(re) >= 4 * dbl_min else 0.0
        im = math.ldexp(im, -2 * scale)
    elif math.fabs(re) < 2 * dbl_min and math.fabs(im) < 2 * dbl_min:
        scale = -((mant_dig + 1) // 2)
        re, im = math.ldexp(re, -2 * scale), math.ldexp(im, -2 * scale)
    # libm hypot(), as glibc uses: CPython's abs(complex) calls it directly, while
    # math.hypot is CPython's own vector-norm algorithm and can differ in the last bit.
    d = abs(complex(re, im))
    if re > 0:
        r = math.sqrt(0.5 * (d + re))
        if scale == 1 and math.fabs(im) < 1:
            s = im / r
            r = math.ldexp(r, scale)
            scale = 0
        else:
            s = 0.5 * (im / r)
    else:
        s = math.sqrt(0.5 * (d - re))
        if scale == 1 and math.fabs(im) < 1:
            r = math.fabs(im / s)
            s = math.ldexp(s, scale)
            scale = 0
        else:
            r = math.fabs(0.5 * (im / s))
    if scale:
        r, s = math.ldexp(r, scale), math.ldexp(s, scale)
    return complex(r, math.copysign(s, im))
