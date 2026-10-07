#!/usr/bin/env bash
# Build the NTIA/itm C++ reference as a shared library for tests/test_differential.py.
#
#   tools/build_itm_reference.sh [out_dir]      (default: build/itm-reference)
#   ITM_REFERENCE_LIB=build/itm-reference/libitm.so python3 -m pytest tests/test_differential.py
#
# Needs git and g++. Linux only: the upstream sources use Windows-style include
# paths and __declspec, which are patched/defined away here.
set -euo pipefail

ITM_REPO=https://github.com/NTIA/itm.git
ITM_COMMIT=183ad95bd813a8be11009df396e1c631356864b2  # master, 2024-09-24

out_dir=${1:-build/itm-reference}
src_dir="$out_dir/src"

rm -rf "$src_dir"
mkdir -p "$out_dir"
git init -q "$src_dir"
git -C "$src_dir" fetch -q --depth 1 "$ITM_REPO" "$ITM_COMMIT"
git -C "$src_dir" checkout -q FETCH_HEAD

sed -i 's#\.\.\\include\\#../include/#' "$src_dir"/src/*.cpp

# Plain IEEE evaluation, the same on every architecture (Python never fuses ops):
#   -ffp-contract=off   never fuse a*b+c into an FMA (GCC's default on aarch64).
#   -fcx-fortran-rules  expand std::complex division inline (Smith's method) instead
#                       of calling libgcc's __divdc3; on aarch64 that precompiled
#                       routine uses FMA, which -ffp-contract=off cannot reach, and it
#                       changed the last bit of ~0.02% of p2p results. Identical to
#                       __divdc3 on x86_64 for finite operands (exact differential).
# No -ffast-math / -march=native. tests/test_differential.py (ITM_DIFF_EXACT=1) relies on this.
g++ -std=c++17 -O2 -ffp-contract=off -fcx-fortran-rules -fPIC -shared '-D__declspec(x)=' \
    -I"$src_dir/include" "$src_dir"/src/*.cpp -o "$out_dir/libitm.so"

echo "$(cd "$out_dir" && pwd)/libitm.so"
