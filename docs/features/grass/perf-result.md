# Grass perf result (Trial 001, perf stage)

Session `20261012T172446`, commit `fa3790e` (git dirty), RTX 3070, 1920x1080, Editor, Scene view closed, warmup 100, measured 300, 20 sweep runs (6 points x 3 + N=0 first and last). `perf_analyze.py` exit 0. Raw: `Perf/grass/report.json` (git-ignored). Editor numbers are relative only.

| N | gpu_ms median | gpu run spread | render_ms | feature_ms (CPU, pass recording) | main_ms |
|---|---|---|---|---|---|
| 0 (2 runs) | 0.381 | 5.1% | 0.844 | 0.0167 | 0.791 |
| 1000 | 0.382 | 74.0% | 0.878 | 0.0165 | 0.806 |
| 3000 | 0.389 | 76.1% | 0.860 | 0.0162 | 0.788 |
| 6000 | 0.514 | 41.4% | 0.872 | 0.0164 | 0.800 |
| 10000 | 0.677 | 47.4% | 0.869 | 0.0163 | 0.796 |
| 50000 | 0.746 | 2.4% | 0.868 | 0.0162 | 0.801 |
| 100000 | 0.791 | 0.26% | 0.887 | 0.0167 | 0.818 |

- Fit gpu_ms, N >= 10000: 0.00125 ms per 1000 blades, intercept 0.671 ms, R^2 0.964, verdict **not linear** (half-slopes 0.00174 and 0.00089). Low-N points are bimodal (clock ramp, known trap), so only N >= 50000 is stable.
- Budget `gpu_ms per_1000 <= 0.05`: headline **about 0.004 ms per 1000 blades** ((0.791 at N=100000 minus 0.381 at N=0) / 100), PASS by a factor of 12. The fit number 0.0013 (R^2 0.964, tool verdict not linear) understates it and is driven by the 10k point with a 47% spread; it is not used as the headline (code review finding 2). Budget `gpu_ms total_at 100000 <= 3.0`: 0.791 measured, PASS. 
- Feature OFF at N=100000 (one run): gpu 0.357 ms. So the feature adds about 0.43 ms at 100,000 blades (0.791 vs 0.357) and about 0.02 ms fixed (N=0 on 0.381 vs off 0.357).
- Half-view pose at N=100000 (one run): gpu 0.7926 ms vs whole-view 0.7910 ms. **No culling gain was measured.** The two poses also differ in camera distance, so the comparison is confounded. Culling correctness (not performance) is proven by the T4 readback test (10000 / 0 / 5033 of 10000). The perf test itself does not read back the drawn count. An away pose with 3 repeats would separate the draw cost; not run (open decision for the human).
- GC: 18,417 B per frame at every N > 0 (18,296 at N=0), below the ~21 KB Editor floor, same as the empty scene.
- Drift N=0 first vs last: gpu -4.97%, no drift above 10%.
- Not verified: player build, per-pass GPU time, repeats of the half-view and OFF runs (one run each).

## Million-blade sweep from a ground view (card 012, commit 8916ef3)

Sessions `20261012T174232` (ground sweep, 23 runs), `...174255` (whole-patch comparison, 7 single runs), `...174303` (feature off at 1M, 1 run). Ground camera (0, 1.5, -12), level, 1920x1080, RTX 3070, Editor, Scene view closed. `perf_analyze` exit 0, no errors, all runs `gpu_valid`, 300/300/300 frames. The sweep test ran 32.5 s.

| N | visible (culler) | gpu_ms ground | gpu_ms whole (all visible) | whole minus ground | gpu spread |
|---|---|---|---|---|---|
| 0 | 0 | 0.478 | | | 1.9% |
| 20000 | 9978 | 0.527 | 0.616 | +0.089 | 0.2% |
| 40000 | 20085 | 0.580 | 0.744 | +0.164 | 3.0% |
| 80000 | 39958 | 0.669 | 0.751 | +0.082 | 0.0% |
| 160000 | 80049 | 0.849 | 1.022 | +0.173 | 0.2% |
| 320000 | 160105 | 1.194 | 1.658 | +0.464 | 0.2% |
| 640000 | 319834 | 1.889 | 2.937 | +1.048 | 0.2% |
| 1000000 | 500099 | 2.686 | 4.357 | +1.671 | 0.3% |

- Culler keeps 49.8 to 50.1% of the blades in the ground pose at every N, identical across repeats.
- Fit gpu_ms vs N (n >= 20000): **0.0022 ms per 1000 blades** placed, intercept 0.491 ms, R^2 0.99996, **linear**, half-slopes 0.00228 and 0.00219. Hand-computed vs visible blades: about 0.0044 ms per 1000 visible (the tool does not produce this). Budget `gpu_ms per_1000 <= 0.05`: PASS (about 23x margin).
- **Culling gain is visible here:** at 1M, 2.686 ms ground (half the blades kept) vs 4.357 ms with all blades visible, 1.67 ms less. The two camera poses still differ in distance, so part of the difference is fragment cost, not only blade count; the visible count and the near-exact 2x relation of the slopes (0.0044 per visible vs 0.0022 per placed) support culling as the main cause.
- Feature off at 1M: gpu 0.461 ms; feature on with N=0: 0.478 ms (fixed cost about 0.02 ms). So the feature costs about 2.2 ms at 1M from the ground view.
- feature_ms (CPU recording) stays 0.016 to 0.022 ms at every N; the CPU side does not grow with blade count. main_ms jumps from 0.89 ms (640k) to 1.58 ms (1M) with an unexplained rise, not examined (at 1M the whole-pose main_ms is 3.2 ms).
- GC 18,417 B per frame at every N (Editor floor). N=0 drift under 5%.
- Open: no total budget for 1M blades has been given (not invented). Buffers at 1M: 64.8 MiB on the GPU plus a 64 MB transient CPU array when placing. Whole-pose runs are single runs. Not verified: player build, per-pass GPU time.

## Repeatability check: 5 runs per blade amount (commit 42fd6f9)

Session `20261012T174704`, 37 sweep runs (7 points x 5 + 2 at N=0), ground pose, same machine and conditions as above. `Sweep_Grass` 47.6 s, `perf_analyze` exit 0. Fit gpu_ms: 0.0022 ms per 1000, intercept 0.489 ms, R^2 1.000, linear; budget per_1000 PASS.

| N | 5 run medians gpu_ms | spread (max-min)/median |
|---|---|---|
| 0 (2 runs) | 0.4813, 0.4710 | 2.2% drift |
| 20000 | 0.5253, 0.5263, 0.5263, 0.5263, 0.5263 | 0.2% |
| 40000 | 0.5755, 0.5755, 0.5745, 0.5734, 0.5755 | 0.4% |
| 80000 | 0.6666, 0.7491, 0.6697, 0.6687, 0.6717 | 12.3% (one outlier, 0.7491) |
| 160000 | 0.8499, 0.8479, 0.8479, 0.8489, 0.8509 | 0.4% |
| 320000 | 1.2093, 1.193, 1.1955, 1.1981, 1.2037 | 1.4% |
| 640000 | 1.8908, 1.8964, 1.8985, 1.9016, 1.8985 | 0.6% |
| 1000000 | 2.6839, 2.7034, 2.7003, 2.6993, 2.6993 | 0.7% |

- At 20,000 blades the five runs agree within 0.2% (0.5253 to 0.5263 ms). No run-order trend (first runs are not slower).
- Old 3-repeat session vs this one, gpu_ms median per N: within -0.8% to +0.5% at every N.
- Not explained: the 80,000 outlier (one run, 0.7491 ms; the median ignores it) and the 11% main_ms spread at 320,000. main_ms is context only for this GPU-bound feature.

## Baseline
Accepted by Alexandros in chat on 2026-10-12: session `20261012T174704` (5 repeats per point, ground pose, commit 42fd6f9) is the baseline for `grass`, stored in `Perf/grass/baseline.json`. No script compares against it yet; the plan's baseline comparison is still open.
