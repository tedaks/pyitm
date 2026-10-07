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

# -ffp-contract=off: never fuse a*b+c into an FMA. GCC defaults to contracting on
# targets with FMA (aarch64 always; x86-64 with -march), and Python never fuses, so
# without this tests/test_differential.py could not demand bit-identical results
# (ITM_DIFF_EXACT=1). No -ffast-math / -march=native for the same reason.
g++ -std=c++17 -O2 -ffp-contract=off -fPIC -shared '-D__declspec(x)=' \
    -I"$src_dir/include" "$src_dir"/src/*.cpp -o "$out_dir/libitm.so"

echo "$(cd "$out_dir" && pwd)/libitm.so"
