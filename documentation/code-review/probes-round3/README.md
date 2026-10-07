# Probes for `04-audit-round3.md` / `05-verification-round3.md`

Run from the **repo root**, with the reference library built first
(`tools/build_itm_reference.sh`) and the repo importable (`PYTHONPATH=.`). Every
reference call goes through `build/itm-reference/libitm.so` (NTIA/itm `183ad95`).

| Probe | What it establishes |
|---|---|
| `divisions.py` | static inventory of every `/` site in `pyitm_ng/` (comments/docstrings stripped) — the list the fix was taken from |
| `probe_f1.py` | F1: the reproducer's traceback, the true threshold pair (bisection to adjacent floats), the input-dependence scan, and the `d_hzn`/`theta_hzn` values either side of the underflow |
| `probe_cpp_side.py` | what the C++ returns for the F1/F2 inputs (finite, `rc=1`, warnings `0x780` / `0x1998`) — the evidence that the port, not the C++, is the one that fails |
| `probe_f2.py` | F2: C++ vs port bit-for-bit on absurd profile distances, with the correct PFL header |
| `probe_p2p_extreme_resolution.py` | the same defect class reached through `predict_p2p` (finite resolution, huge implied distance) and the next site past a two-site patch |
| `battery.py` | 166 hostile-but-accepted inputs through all four entry points, reporting the traceback site of every raise (ValueErrors excluded as documented deviations) |
| `fuzz_hunt.py` | 10,000 randomized wide draws (seeds 1-3) vs the C++, classifying every exception as missed site / documented / divergence |
| `preflight_extended_draws.py` | runs the differential's new draws through the C++ **only** — the reference casts distances to `int` and SIGSEGVs on `d__meter == inf`, so this is run standalone before the ranges are committed to `tests/` |
| `bench_ieee_div.py` | timing, run in one state at a time with the states interleaved from the shell |

`fuzz_hunt.py` and `preflight_extended_draws.py` print progress as they go, so a crash is
attributable to the case that was running.
