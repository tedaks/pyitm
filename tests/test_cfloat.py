# tests/test_cfloat.py
"""pyitm_ng._cfloat must reproduce C semantics bit for bit, checked against the
platform's libm via ctypes (Linux/glibc; skipped where libm can't be loaded)."""

import ctypes
import ctypes.util
import math
import platform
import random

import pytest

from pyitm_ng._cfloat import (
    c_cos, c_csqrt, c_dim, c_exp, c_fdim, c_log, c_log10, c_max, c_min, c_pow, c_sin, c_sqrt,
)

NAN, INF = math.nan, math.inf
_libm_path = ctypes.util.find_library("m")
libm = ctypes.CDLL(_libm_path) if _libm_path else None
needs_libm = pytest.mark.skipif(libm is None or not hasattr(libm, "csqrt"), reason="no C libm via ctypes")
# c_csqrt ports glibc's algorithm; other libms (macOS, musl) compute csqrt differently.
needs_glibc = pytest.mark.skipif(
    libm is None or platform.libc_ver()[0] != "glibc", reason="c_csqrt mirrors glibc's csqrt"
)


class _C(ctypes.Structure):
    _fields_ = [("re", ctypes.c_double), ("im", ctypes.c_double)]


def _same(a, b):
    return (a != a and b != b) or (a == b and math.copysign(1.0, a) == math.copysign(1.0, b))


EDGES = [0.0, -0.0, 1.0, -1.0, 0.5, -0.5, 2.0, -2.0, 1e-310, -1e-310, 1e300, -1e300, 1e308,
         -1e308, 710.0, -746.0, INF, -INF, NAN, 3.0, -3.0, 1 / 3]


def _values(n=3000, seed=7):
    rng = random.Random(seed)
    vals = list(EDGES)
    for _ in range(n):
        vals.append(rng.choice([1, -1]) * 10 ** rng.uniform(-320, 308))
    return vals


@needs_libm
@pytest.mark.parametrize("name, fn", [("log", c_log), ("log10", c_log10), ("sqrt", c_sqrt),
                                      ("exp", c_exp), ("sin", c_sin), ("cos", c_cos)])
def test_unary_matches_libm(name, fn):
    cf = getattr(libm, name)
    cf.restype, cf.argtypes = ctypes.c_double, [ctypes.c_double]
    bad = [(x, fn(x), cf(x)) for x in _values() if not _same(fn(x), cf(x))]
    assert not bad, bad[:5]


@needs_libm
def test_pow_matches_libm():
    libm.pow.restype, libm.pow.argtypes = ctypes.c_double, [ctypes.c_double, ctypes.c_double]
    xs = _values(400, 1)
    ys = EDGES + [0.25, 1 / 3, -1 / 3, 4.0, 6.0, -2.0, 1e10, 3.5, -0.5]
    bad = [(x, y, c_pow(x, y), libm.pow(x, y)) for x in xs for y in ys
           if not _same(c_pow(x, y), libm.pow(x, y))]
    assert not bad, bad[:5]


@needs_glibc
def test_csqrt_matches_glibc():
    libm.csqrt.restype, libm.csqrt.argtypes = _C, [_C]
    rng = random.Random(11)
    zs = [complex(a, b) for a in EDGES for b in EDGES]
    zs += [complex(0.0, rng.uniform(1e-6, 1e6)) for _ in range(5000)]  # purely imaginary
    zs += [complex(rng.uniform(-1e3, 1e3), rng.uniform(-1e6, 1e6)) for _ in range(20000)]
    zs += [complex(rng.choice([1, -1]) * 10 ** rng.uniform(-320, 308),
                   rng.choice([1, -1]) * 10 ** rng.uniform(-320, 308)) for _ in range(20000)]
    bad = []
    for z in zs:
        c = libm.csqrt(_C(z.real, z.imag))
        p = c_csqrt(z)
        if not (_same(p.real, c.re) and _same(p.imag, c.im)):
            bad.append((z, p, complex(c.re, c.im)))
    assert not bad, bad[:5]


def test_csqrt_pure_imaginary_has_equal_parts():
    # the case that flips ERROR__GROUND_IMPEDANCE (epsilon == 1)
    for b in (0.1, 2.0, 1234.5678, 0.0123):
        z = c_csqrt(complex(0.0, b))
        assert z.real == z.imag


@pytest.mark.parametrize("x, y, mx, mn", [
    (NAN, 0.0, 0.0, 0.0),   # MAX(nan, y) -> y: the C comparison is false
    (0.0, NAN, NAN, NAN),   # MAX(x, nan) -> nan
    (1.0, 2.0, 2.0, 1.0),
])
def test_macros(x, y, mx, mn):
    assert _same(c_max(x, y), mx) and _same(c_min(x, y), mn)


def test_dim_and_fdim():
    assert c_dim(NAN, 1.0) == 0.0 and c_dim(3.0, 1.0) == 2.0 and c_dim(1.0, 3.0) == 0.0
    assert math.isnan(c_fdim(NAN, 1.0)) and math.isnan(c_fdim(1.0, NAN))
    assert c_fdim(3.0, 1.0) == 2.0 and c_fdim(1.0, 3.0) == 0.0
