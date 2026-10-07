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

# -O2 without -march: no FMA contraction, so tests/test_differential.py can demand
# bit-identical results (ITM_DIFF_EXACT=1). Adding -march=native / -ffast-math breaks that.
g++ -std=c++17 -O2 -fPIC -shared '-D__declspec(x)=' \
    -I"$src_dir/include" "$src_dir"/src/*.cpp -o "$out_dir/libitm.so"

echo "$(cd "$out_dir" && pwd)/libitm.so"
