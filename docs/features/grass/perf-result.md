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
- Budget `gpu_ms per_1000 <= 0.05`: 0.0013 PASS. Budget `gpu_ms total_at 100000 <= 3.0`: 0.791 measured, PASS. Caveat: the per-1000 figure rests on a fit the tool calls not linear.
- Feature OFF at N=100000 (one run): gpu 0.357 ms. So the feature adds about 0.43 ms at 100,000 blades (0.791 vs 0.357) and about 0.02 ms fixed (N=0 on 0.381 vs off 0.357).
- Half-view pose at N=100000 (one run): gpu 0.7926 ms vs whole-view 0.7910 ms. **No culling gain is visible in frame GPU time.** Culling correctness is proven by the T4 readback test (10000 / 0 / 5033 of 10000), not by this number.
- GC: 18,417 B per frame at every N > 0 (18,296 at N=0), below the ~21 KB Editor floor, same as the empty scene.
- Drift N=0 first vs last: gpu -4.97%, no drift above 10%.
- Not verified: player build, per-pass GPU time, repeats of the half-view and OFF runs (one run each).
