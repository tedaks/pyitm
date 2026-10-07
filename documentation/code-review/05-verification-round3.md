# Verification of `04-audit-round3.md` + the division-by-zero fix

Independent verification of each claim in [`04-audit-round3.md`](04-audit-round3.md), against the
tree at `8fc1826` (2026-10-07 11:34 +0800, `audit/round2-fixes`). Nothing here re-reads the audit's
reasoning: every number below came from a run.

**Reproduce:** probes in [`probes-round3/`](probes-round3/) (run from the repo root, with the
reference library built by `tools/build_itm_reference.sh`). Venv used: uv CPython 3.12.14 + numpy
2.5.3, glibc libm.

## Baseline re-derived

| Claim in 04 | Result |
|---|---|
| full suite 227 passed, 7 skipped | CONFIRMED (`227 passed, 7 skipped in 0.65s`) |
| `ITM_DIFF_EXACT=1` differential 7 passed | CONFIRMED (`7 passed`, default 1000 cases/entry point) |
| differential samples resolution ∈ [1, 2000] m, d__km ∈ [0.001, 2000], delta_h ∈ [0, 3000] | CONFIRMED (`tests/test_differential.py:107,123,124` before the change) |

## F1 — `predict_area` with a huge `delta_h__meter`: CONFIRMED, argument wrong

The exception is real and reproduces. The write-up is wrong in five ways.

1. **Two mechanisms with two thresholds are presented as one chain.** The `Reproduce` traceback
   (`terrain.py:249`) and the "root cause chain" + measured threshold (`propagation.py:129`) are
   different events:
   - Δh ≈ 1.4768e8 (h_e ≤ 5): `a__meter[2] = 0.5*sq(d_hzn[1])/h_e[1]` — the *squaring* underflows to
     0.0 (`d_hzn[1] ≈ 5e-162`, not 0.0), so `(4/3)*a_0/a__meter[i]` divides by zero at
     `propagation.py:129` (= C++ `SmoothEarthDiffraction.cpp:48`). This is the threshold the report measured.
   - Δh ≳ 5.6655e8: `d_hzn[1]` is *exactly* 0.0, so `d_Ls__meter / d_hzn__meter[i]` raises at
     `terrain.py:249` (= `InitializeArea.cpp:53`). This is the traceback the report quotes.
   The quoted threshold cannot produce the quoted traceback: with `H_3__meter = 5`, `max(h_e, 5) = 5`
   for any h_e ≤ 5, so the `terrain.py:249` site needs Δh > 5·(745.1332/0.07)² = 5.6655e8 m.
   Third observation: the transition at 5.6655e8 is *not* monotone — over a ~4e4-ulp band
   (≈566554606.335 ± 2.6e-3 m) the failing site alternates between the two (glibc `exp` denormal
   rounding at the underflow edge, visible in `probes-round3/probe_f1.py`).

2. **The "~26.6" exponent figure is wrong by ~200×.** `c_exp(-x) → 0.0` needs
   0.07·sqrt(Δh/max(h_e,5)) > 745.1332, i.e. sqrt(·) > 10645. The *first* failure (squaring
   underflow, `d_hzn < 2^-537`) needs 0.07·sqrt(Δh/max(h_e,5)) ≳ 380.6, i.e. sqrt(Δh/max(h_e,5)) ≳ 5437.
   The report also drops the `c_max(h_e__meter[i], H_3__meter)` clamp — that clamp is why every
   h_e ≤ 5 shares one threshold.

3. **The threshold pair is not the boundary.** Measured: last ok `147682446.6732504`, first fail
   `147682446.67325044` (4e-8 m apart, ~1.3 ulp). The report's `…667e8` / `…668e8` differ by 0.01 m,
   and the second is merely *a* value that raises, not the first.

4. **"depends on h_e, a_e" is wrong on `a_e`.** Measured (bracket scan, 1.06× grid): h_rx = 1, 2, 5,
   h_tx = 0.5/10/3000, N_0 = 250/301/400, f = 20/230/20000 MHz, d = 0.001/50/2000 km, climate 1/3 →
   identical bracket (1.4185e8, 1.5036e8]. h_rx = 8 → (2.26e8, 2.40e8]; h_rx = 10 → (2.85e8, 3.03e8];
   siting 2/2 (h_e raised) → (2.40e8, 2.54e8]. So: h_e only, clamped at 5. `gamma_e` depends on
   `N_s = N_0` only (`propagation.py:373`), not on f, so f/d__km/N_0 cannot move it.

5. **Both recommended fixes are the wrong class.** The policy is to match the C++ *including its
   numeric quirks*; at both sites the C++ performs an IEEE division by zero and returns a finite
   value — no UB, no crash. Measured C++ `ITM_AREA_TLS` for the report's own parameters:
   Δh = 1e6 / 1.4768e8 / 5.6655e8 / 1e9 / 1e12 / 1e300 → all `rc=1`,
   `A__db = 112.82307201162544`, `warnings = 0x780`. The port already ships `ieee_div` for exactly
   this (and already used it for `M_d - M_s`). Replacing the `/` with `ieee_div(...)` at the two
   sites gives bit-identical `A__db` *and* warning bits at every one of those Δh values, is a no-op
   whenever the divisor ≠ 0, and keeps the exact differential green. Option A pins a crash as
   intended behaviour of a port whose selling point is bit-identity; Option B adds a deviation where
   the C++ has none, which the policy does not allow and the differential would flag the moment it
   samples that Δh range.

## F2 — CONFIRMED value, REFUTED "no warning", and it misses the real defect

- Verified with the correct header (`np = 9` intervals, 10 points): C++ `A__db = 5214464815.792534`,
  `warnings = 0x1998`, `rc = 1`; the port returns the same value and the same mask. Reporting that
  number is right. (Passing `np = 10` with 10 elevations makes the C++ read past the array and print a
  different number — a precondition of the comparison, not a finding.)
- **REFUTED:** "no warning bit set that would alert the caller" is false. `0x1998` contains
  `WARN__PATH_DISTANCE_TOO_BIG_1` (0x8) and `_2` (0x10), set in `LongleyRice.cpp:104/106` for
  `d__meter > 1000 km` / `> 2000 km` in *both* modes. The parenthetical "the C++ sets such warnings
  for `d__km` in area mode but not for p2p distance derived from the profile" is also false.
- **MISSED — same class as F1, on this very path.** The port *raises* where the C++ returns a finite
  value, for a resolution that `TerrainProfile` accepts (finite, > 0):

  | profile | implied d | C++ | port before the fix |
  |---|---|---|---|
  | 10 pts × 3e9 m | 2.7e10 | A = 5214464815.792534, w = 0x1998 | same (match) |
  | 10 pts × 1e12 m | 9e12 | A = 277.8528761359173, w = 0x1998 | same (match) |
  | 10 pts × 1e30 m | 9e30 | A = 637.8528761359174, w = 0x1998 | `ZeroDivisionError @ propagation.py:129` |
  | 10 pts × 1e100 m | 9e100 | A = 2037.85…, w = 0x1998 | `ZeroDivisionError @ propagation.py:129` |
  | 600 pts × 1e300 m | 5.99e302 | A = nan, w = 0x1998 | `ZeroDivisionError @ propagation.py:129` |
  | 3 pts × 1e308 m | inf | **SIGSEGV** | `OverflowError @ terrain.py:88` (C++ UB: a guard is legitimate) |

  Patching only F1's two sites moves the same failure to the next unguarded division
  (`propagation.py:480` = C++ `LongleyRice.cpp:94`). So this is a family of plain-`/` sites reachable
  on accepted input, not two sites: the differential's resolution range (≤ 2000 m) never gets near
  them. F2's "Low / no crash / no fix recommended" therefore understates it, and its suggested remedy
  (a profile-level `PATH_DISTANCE_TOO_BIG` warning) would add a deviation the C++ does not have.

## F3 — CONFIRMED

`dist/pyitm_ng-0.3.0-py3-none-any.whl` + `.tar.gz` present and ignored (`.gitignore:10` = `dist/`);
`e6c4bb5` = `Revert "release: v0.3.0"` with "PyPI publishing is on hold; keep the 0.3.0 entries under
[Unreleased]"; `CHANGELOG.md` has `## [Unreleased]` at line 7 with the 0.3.0 entries under it. The
`Date: 2026-10-06 (approximate)` header is off: the file postdates HEAD (`8fc1826`, 2026-10-07 11:34).

## F4 — CONFIRMED

`documentation/todo.md:19-20`: unchecked, files `pyitm_ng/models.py`, `pyitm_ng/itm.py` — accurate;
no antenna/gain parameters anywhere in `pyitm_ng/` (the only hits are the Vogler "height gain
function" and troposcatter "frequency gain" docstrings).

## Verdicts

| ID | Verdict |
|---|---|
| F1 | CONFIRMED (reproduces); ARGUMENT WRONG — mechanism/site conflated, "~26.6" wrong by ~200×, threshold pair not the boundary, `a_e` dependence wrong; both recommended fixes are the wrong class |
| F2 | PARTLY CONFIRMED — value matches the C++; "no warning bit" REFUTED (`0x1998` holds `PATH_DISTANCE_TOO_BIG_1/_2`); the real defect on that path (raise vs finite C++ value) is missed |
| F3 | CONFIRMED |
| F4 | CONFIRMED |

The audit's framing — "the differential cannot see this" — is right, and F1 is a genuine fidelity
bug. But it is one instance of a class (unguarded `/` where the C++ divides by zero in IEEE and
computes on), that class has an existing bit-exact remedy in `pyitm_ng/_cfloat.ieee_div`, and the
report instead offers a new documented deviation or a new input bound. Grading it Medium-as-a-policy-
choice and F2 Low-with-no-fix misplaces both: same bug, two triggers, one fix.

---

# The fix

Routed every division whose divisor can be `0.0` on accepted input through `ieee_div`:
`propagation.py` (`smooth_earth_diffraction`'s `a__meter[0]` and `C_0`, `h0_curve`, the `H_0`
expression, `sin_psi/q` and `delta_phi`, `1/gamma_e`, `theta_los`, `M_d`, `d_1`, the three `kHat`
denominators), `terrain.py` (`find_horizons`'s `a_e` term, `quick_pfl`'s `a_e`, `q` and `theta_hzn`,
`initialize_area`'s `theta_hzn`), `variability.py` (`x_length` in the least-squares fit). Each is a
no-op unless the divisor is exactly 0.0, so valid input is untouched — proven by the exact
differential below, not by inspection.

## Reachability (how the list was derived)

`probes-round3/battery.py` sweeps 166 hostile-but-accepted inputs through all four entry points;
`probes-round3/fuzz_hunt.py` runs 10,000 randomized cases (3 seeds) with every parameter drawn from
decades either side of the documented range, comparing value **and** warning mask against the
reference and classifying every exception:

| state | battery | fuzz (10,000 cases) |
|---|---|---|
| before | 85 raised, at `propagation.py:129`, `terrain.py:249`, `terrain.py:32`, `propagation.py:119`, `propagation.py:296` | — |
| after | **0 raised** | 5,960 bit-identical, 4,040 documented `ValueError` (the C++ returns an error code in every one), **0 missed sites, 0 divergences** |

## RED → GREEN (the gate can see it)

`tests/test_differential.py` now draws `delta_h__meter` (area) and the profile resolution (p2p) from
the decades past the documented range in every fourth case, plus two focused tests for the extremes.

| run | unfixed port | fixed |
|---|---|---|
| `ITM_DIFF_EXACT=1`, 1000 cases/entry point | **6 failed**, 3 passed (`ZeroDivisionError`) | **9 passed** |
| `ITM_DIFF_EXACT=1`, 5000 cases/entry point | — | **9 passed** |
| `tests/test_edge_cases.py` (pinned C++ values) | **8 failed** | 46 passed |

Gates on the fixed tree: `pytest` 247 passed with the reference library, 238 passed / 9 skipped
without; `ruff check pyitm_ng/ tests/` clean; `mypy --strict` clean.

Timing (`probes-round3/bench_ieee_div.py`, medians of 7 × 400 calls, states interleaved three times):
p2p 50-point 177–186 µs, p2p 600-point 327–345 µs, area 51–62 µs — the same-state repeats swing
±10%, wider than any difference between states, so no measurable cost.

## Not done

- No upper bound was added to `delta_h__meter` or the profile resolution: the C++ accepts them and
  returns a value, so a bound would be a new deviation. `d__meter == inf` (a resolution ≥ ~3e305 m on
  a 600-point profile) still raises where the C++ SIGSEGVs — that is undefined behaviour, so a guard
  is legitimate, and it is left as the `OverflowError` it already was.
- The differential deliberately keeps `d__meter` finite for the same reason (a segfault in the
  reference would take the test process down); `tests/test_differential.py` documents this.
