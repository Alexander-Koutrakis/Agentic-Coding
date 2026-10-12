# Spike 003 — sweep harness (GPU/render/main time, slope per 1000 instances)

Goal: turn Spike 002's CPU-marker harness into the reusable sweep harness described in plan §4.4 (D14-D16): 100 warmup + 300 measured frames per point, median and p95 in ms for main thread, render thread, GPU and the feature's own marker, a sweep over an instance count, a fit that gives ms per 1000 instances, and a log for every run. Prove it on a toy rendering feature so another agent can use it on a real one.

Branch: `spike/003-sweep-harness` (from `spike/002-profiler-harness`) · Project: `Test Enviroments/Unity Agentic Kit test/`

## What was built
- `Assets/Kit/Perf/Runtime` (`Kit.Perf`): `PerfRunner` (warmup, recorders, FrameTiming collection), `PerfRunWriter` (run folder, CSVs, `index.jsonl`), `PerfStats`, `GitInfo`, types.
- `Assets/Kit/Perf/Toy` (`Kit.Perf.Toy`): `ToyInstances`, N GPU-instanced quads (`Graphics.RenderMeshInstanced`, URP Unlit, runtime material, fixed seed) with a `ProfilerMarker`. A stand-in for a rendering feature.
- `Assets/Kit/Perf/Tests/PlayMode`: `Probe_FrameTimingAvailable` (2 points) and `Sweep_ToyInstances` (baseline N=0 first and last, 6 points x 3 repeats shuffled; 20 runs, about 70 s).
- `scripts/unity/perf_analyze.py` + `test_perf_analyze.py` (15 tests): recompute stats from CSV, cross-check `run.json`, refuse mixed conditions, per-point aggregation, OLS fit per metric (slope per 1000, intercept, R^2, half slopes, verdict), optional `fit_min_n`, drift, budgets, exit codes.
- Skill `skills/unity/unity-perf-harness`, pointer in `CLAUDE.md`, plan §4.4 and D14-D16.
- `Perf/.gitignore` (results ignored) and `Perf/toy-instances/feature.json` (placeholder budgets).
All Unity API names were checked against the live Editor with `unity_reflect` / `unity_docs` before use.

## Results
| Question | Answer |
|---|---|
| Does the Editor give GPU and render-thread time? | Yes. `FrameTimingManager.IsFeatureEnabled()` was true with no settings change; `gpuFrameTime`, `cpuRenderThreadFrameTime`, `cpuMainThreadFrameTime` all returned values that respond to load. Results arrive 4 frames late (handled). |
| Does the full chain run without a human? | Yes: compile, `run_tests` (PlayMode), files, `perf_analyze`. 20 runs in about 70 s. |
| Is the analysis correct? | 15 unit tests with known slopes (exact line, quadratic, mismatch, drift, budgets, sessions). On real data the recomputed medians matched the C# ones in all 40 runs (no mismatch errors). |
| Reproducible? | Two full sweeps, loaded-range fit (n >= 10000): GPU 0.0322 and 0.0272 ms per 1000, feature marker 0.0190 and 0.0217, render 0.0391 and 0.0439. About 15% apart. |

Sweep 2 (session `20261012T084041`), medians over 3 runs per point:
| N | gpu_ms | feature_ms | render_ms | main_ms |
|---|---|---|---|---|
| 0 | 1.073 (p95 2.288) | 0.000 | 1.186 | 3.485 |
| 1000 | 1.421 (p95 2.610) | 0.046 | 1.628 | 2.978 |
| 3000 | 1.184 (p95 2.109) | 0.103 | 1.837 | 3.418 |
| 6000 | 1.308 (p95 2.210) | 0.126 | 1.442 | 2.574 |
| 10000 | 1.417 (p95 2.298) | 0.195 | 1.372 | 3.490 |
| 50000 | 2.286 (p95 3.089) | 0.981 | 2.994 | 4.346 |
| 100000 | 3.849 (p95 4.567) | 2.139 | 5.314 | 7.196 |

Fit on n >= 10000 (sweep 2): feature 0.0217 ms/1k (R^2 0.998), GPU 0.0272 ms/1k + 1.07 ms fixed (R^2 0.990), render 0.0439 ms/1k (R^2 0.999); main thread not linear (flat about 5 ms). Fit on all points: GPU R^2 0.93 (session 1) and 0.98 with a half-slope ratio of 1.58 (session 2): reported "not linear".
Budgets from `feature.json` evaluated: 3 of 3 PASS (placeholders).

## Friction log
1. **`ProfilerRecorder` resets at capacity** (again, see Spike 002 #1): Count fell to 1 at capacity 300 after 300 frames. Fixed with headroom. **Sample 0 is a partial frame** (feature 0 ms, GC about half): dropped.
2. **FrameTimingManager is 4 frames late**; element 0 is the last finished frame, so the same frame can be returned twice. De-duplicate on `frameStartTimestamp`, drain, drop the first 4.
3. **GPU time at light load is unreliable.** At 1k-6k instances GPU time was inflated and not monotonic (10k was lower than 6k in session 1); the N=0 baseline moved 0.55 to 1.02 ms inside a run. Likely GPU clock ramp (not verified). Handled by `fit_min_n`; the harness cannot lock clocks.
4. **Baseline drift warning is noisy** because the baseline is the idle point. Proposal in plan §4.4: loaded reference point first and last.
5. **Main-thread time is flat (about 5 ms) for this feature**: no signal; keep as context.
6. **Editor focus changes mid-run** (`editor_is_focused` true at the end of session 2), against D6.
7. `editor/state` returned the empty placeholder (`sequence: 0`) right after a reload again; re-read. The language-server diagnostics lagged one edit behind the compiler; the Unity compile is the authority.
8. One test run (the sweep) takes 70 s; `run_tests` plus `get_test_job(wait_timeout=90)` handled it in one wait.

## Not verified
- GPU time per pass (`ProfilingSampler.gpuElapsedTime` in a `ScriptableRenderPass`); this spike measures frame GPU time.
- Player-build numbers; any other machine or GPU.
- A real feature with overdraw, shaders, LODs or culling; the toy only scales instance count.
- Whether lower GPU time at light load is clock ramp (assumed, not shown).
- Friction #3 of Spike 001 (file rewrite) is still uninvestigated.

## Proposals
1. Loaded reference point for the drift check (`drift_point_n` in `feature.json`).
2. `perf_check.py` as the gate over `report.json` (exists, runs, within budget, no errors), then add it to `unity-check` for graphics features.
3. Wire per-pass GPU time with `ProfilingSampler` once a real feature has a render pass.
4. Baselines: `Perf/<feature>/baseline.json` written from an accepted report; regression check against it with 10-15% Editor tolerance.
5. Trial the kit on a real rendering feature (`docs/trials/001-rendering-feature.md`).
