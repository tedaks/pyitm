# tests/test_reference_build.py
"""The fidelity policy assumes what GCC does with pow() under the reference build flags:
pow(x, 2) becomes one multiply (so Python's sq() = x * x is bit-identical), and every
other exponent, integral or not, stays a libm pow() call (so Python must call pow too).
A compiler upgrade that changed either would break bit-identity in ways the CSVs can't
see; this pins the assumption. Needs g++ and objdump (Linux), else skipped."""

import pathlib
import platform
import re
import shlex
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD_SCRIPT = ROOT / "tools" / "build_itm_reference.sh"

pytestmark = pytest.mark.skipif(
    platform.system() != "Linux" or not shutil.which("g++") or not shutil.which("objdump"),
    reason="needs Linux g++ and objdump (the reference build is Linux-only)",
)

SOURCE = """#include <cmath>
using namespace std;
double f2(double x) { return pow(x, 2); }
double f3(double x) { return pow(x, 3); }
double f4(double x) { return pow(x, 4); }
double f6(double x) { return pow(x, 6); }
double ft(double x) { return pow(x, 1.0 / 3.0); }
double fq(double x) { return pow(x, 0.25); }
"""


def _reference_flags():
    """The code-generation flags of the g++ line in tools/build_itm_reference.sh."""
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    line = re.search(r"^g\+\+ (.*?)\\$", text, re.M)
    assert line, "g++ command not found in tools/build_itm_reference.sh"
    flags = [f for f in shlex.split(line.group(1)) if f.startswith(("-O", "-f", "-std", "-m"))]
    assert "-ffp-contract=off" in flags and "-O2" in flags, flags
    return [f for f in flags if f != "-fPIC"]


def _pow_calls(tmp_path):
    src = tmp_path / "p.cpp"
    obj = tmp_path / "p.o"
    src.write_text(SOURCE, encoding="utf-8")
    subprocess.run(["g++", *_reference_flags(), "-c", str(src), "-o", str(obj)], check=True)
    dump = subprocess.run(
        ["objdump", "-dr", "--no-show-raw-insn", str(obj)], check=True, capture_output=True, encoding="utf-8"
    ).stdout
    calls, current = {}, None
    for line in dump.splitlines():
        m = re.match(r"^[0-9a-f]+ <_Z2(\w+)d>:", line)
        if m:
            current = m.group(1)
            calls[current] = 0
        elif current and re.search(r"R_\w+\s+pow\b", line):
            calls[current] += 1  # a call or a tail jump (x86_64 emits jmp pow for these)
    return calls


def test_pow_x_2_is_a_multiply_and_other_exponents_call_pow(tmp_path):
    calls = _pow_calls(tmp_path)
    assert set(calls) == {"f2", "f3", "f4", "f6", "ft", "fq"}, calls
    assert calls["f2"] == 0, "pow(x, 2) no longer folds to x*x: sq() is not bit-identical"
    for name in ("f3", "f4", "f6", "ft", "fq"):
        assert calls[name] == 1, f"{name}: pow() is inlined now; the port's c_pow no longer matches"
