---
name: unity-perf-harness
description: Measure the cost of a Unity rendering feature with a Play Mode sweep (e.g. 1k to 100k instances), get median/p95 in ms for main thread, render thread, GPU and the feature's own marker, and fit the ms cost per 1000 instances. Use when a graphics feature needs a perf harness, a budget check or a regression check.
---

# unity-perf-harness

## When to use
A graphics feature is done only when its harness runs and is within budget (plan §4.4, D7). Use this skill to build the harness for a feature, run it, and report the cost. The harness is designed **with the human per feature**: the guideline below gives defaults, the human decides what is swept and what the budget is.

## Inputs & access
- Agree with the human first and write it into `Perf/<feature>/feature.json`: the swept parameter and its points, the budget (`per_1000` and/or `total_at` a real in-game count), the reference scene, and `fit_min_n` if light loads are unreliable. Ask; do not invent a budget.
- Library `Assets/Kit/Perf/Runtime` (`Kit.Perf`: `PerfRunner`, `PerfRunWriter`). Working reference: `Assets/Kit/Perf/Tests/PlayMode/ToyInstancesSweepTests.cs` and the toy feature in `Assets/Kit/Perf/Toy/`.
- Skills `unity-wait-ready`, `unity-check`. UnityMCP `run_tests`, `get_test_job`, `read_console`.
- Script `scripts/unity/perf_analyze.py` (Python, reads files only; never connects to the bridge).

## Steps
1. **Instrument the feature.** Wrap its CPU work in a `ProfilerMarker` (category `Scripts`) with a stable name. Pass that name as `PerfRunConfig.FeatureMarker`. (Per-pass GPU time via `ProfilingSampler` is not wired yet.)
2. **Write the sweep test** in a PlayMode test assembly, copying `ToyInstancesSweepTests`: fixed camera, seed and resolution; the swept parameter set per point; baseline point (N = 0, feature on) first and last; the other points repeated 3 times in shuffled order; label `sweep-n<N>-i<index>`. Defaults: `WarmupFrames = 100`, `MeasuredFrames = 300`. Put at least 4 points in the loaded range (GPU time at light load is unreliable, see below). Mark long tests with `[Timeout]`.
3. **Compile.** Run `unity-wait-ready`; fix console errors (`types=["error"]`).
4. **Run the sweep through `run_tests`** (`mode="PlayMode"`, `assembly_names`, `test_names=[<the sweep test>]`, `init_timeout=120000`), then `get_test_job(wait_timeout=60)` until done. Never use `manage_editor play` for measurement: it stalls while the Editor is unfocused.
5. **Analyze:** `python -I scripts/unity/perf_analyze.py Perf/<feature>` (add `--fit-min-n <N>` if the light-load points bend the fit). It analyzes the latest session, writes `Perf/<feature>/report.json`, prints a short summary and exits 0 (ok), 1 (a budget failed) or 2 (bad data).
6. **Read the result critically** (see validate), then report.

## How to validate
- The test passed: every run has `timing_frames == measured_frames` and `recorder_frames == measured_frames`; `gpu_valid` is true.
- `perf_analyze` exit code is 0 and `errors` is empty (it rejects runs that mix commits, machines or settings, and CSV vs `run.json` mismatches).
- Fits: trust a slope only when the verdict is `linear` (R^2 >= 0.98, upper and lower half slopes within 1.5x). If it says `not linear`, report the per-point medians instead of one number, or refit with `--fit-min-n` and say so.
- Check `run_spread_pct` per point and the baseline `drift` warnings: a drift above 10% means the machine state changed; rerun before trusting small differences.
- Known traps (Spike 002/003):
  - Frame time is capped when vsync is on; `PerfRunner` turns vsync off and restores it.
  - GPU time at light load is inflated and unstable (clock ramp), so low-N points can sit above the line. Judge GPU slope from the loaded range.
  - Main-thread time carries no signal for a GPU-bound feature; the feature's own marker is the primary CPU metric.
  - A `ProfilerRecorder` that reaches its capacity resets; `PerfRunner` gives headroom. Do not shorten that.
  - Whole-frame GC has a ~20 KB Editor floor; it cannot prove "0 alloc".
  - Editor numbers are relative only (D15): compare slopes and ON vs OFF on one machine, never to another machine.

## What to return
One block, with real numbers:
`<feature>: <n> runs, sweep <points>. feature_ms 0.019 ms/1k (R^2 0.999, linear); gpu_ms 0.032 ms/1k + 0.88 ms fixed (R^2 1.000, fit n >= 10000); render_ms ...; budget gpu per_1000 <= X: PASS/FAIL; warnings: ...`
Plus the path of `report.json`, the session id, and what was not verified (player build, per-pass GPU).

## Approvals
- Ask the human for the sweep points, the budget and the reference scene before building the harness.
- Do not change `ProjectSettings/` (frame timing is already enabled in the Editor) or edit scene/prefab files as text; follow `unity-scene-safety`.
- Do not commit `Perf/*/runs/`, `index.jsonl` or `report.json` (ignored); commit `feature.json` and accepted baselines only.
