# Spike 002 — Play Mode profiler harness

Goal: prove an agent can measure a feature's CPU cost in Play Mode through UnityMCP and get numbers it can trust: a custom `ProfilerMarker`, N measured frames after warmup, **feature ON vs OFF in the same run**, p50/p95, GC alloc per frame, one result file. This is the base of the D7 perf harness (plan §4.4) and of the `perf_check.py` gate.

Branch: `spike/002-profiler-harness` · Project: `Test Environments/Unity Agentic Kit test/`
Time-box: one session. Status: **code written, not yet compiled or run** (see Status).

## Questions this spike answers
1. Can a `ProfilerMarker` be read **by name** per frame? Through `ProfilerRecorder` inside a test, and through UnityMCP `manage_profiler get_counters`.
2. Does `ProfilerRecorder` need the Profiler window/recording to be on?
3. Is the first-frames warm-up visible, and how many frames until the numbers settle?
4. How noisy are p50/p95 in the Editor between repeated runs (needed to choose a tolerance)?
5. Does a PlayMode test run through `run_tests` (`mode="PlayMode"`) behave with the domain reload and Play Mode enter, and how long does it take?
6. Are `GC Allocated In Frame` and `Main Thread` readable by name with `ProfilerRecorder` (valid=true)?
7. Not in scope: GPU time per pass, the Performance Testing package, player builds, recording `.raw` files.

## What was built (all plain-text sources)
Under `Assets/Kit/Spike/Perf/`:
- `Runtime/Kit.Spike.Perf.asmdef`, `Runtime/SpikeWorkload.cs`: a MonoBehaviour. When `FeatureEnabled`, `Update` runs a fixed loop (`200_000` x `Mathf.Sin`, no allocation) inside `ProfilerMarker "Kit.Spike.Workload"` (category Scripts).
- `Tests/PlayMode/Kit.Spike.Perf.Tests.PlayMode.asmdef`, `SpikeWorkloadPerfTests.cs`: one `[UnityTest]`. For OFF, then ON: start three `ProfilerRecorder`s (the marker, `GC Allocated In Frame`, `Main Thread`) with capacity 120, wait 30 warmup + 120 measured frames, summarize the 120 samples (nearest-rank p50/p95). Writes `Perf/spike-002/result.json` next to `Assets/` and logs it.
- No new packages: the Performance Testing package is not installed (installing is a one-way door, ask first); `ProfilerRecorder` ships with the engine.

Decisions made while writing, each to be checked by running it:
- The recorder runs for warmup + measured frames with capacity = measured frames, so the buffer keeps the last 120 samples (assumes the buffer wraps; if `Count` is not 120, that assumption is wrong).
- The asserts have first-guess thresholds: ON p50 > 0.1 ms, OFF p50 < ON p50 / 10. They are placeholders to be set from the first real numbers, not tolerances to loosen later.

## Steps (agent)
Record tool, wall time, first try and surprises for every step, as in Spike 001.
1. **Baseline.** Tree clean except this work. Run `unity-wait-ready`, then `unity-check` on the canary: expect `PASS 3/3 EditMode`. If the pin in `Packages/manifest.json` (`#v10.3.0`) changed `packages-lock.json`, note it.
2. **Compile.** `unity-wait-ready`. Expect `.meta` files for the new folders, asmdefs and scripts. Fix compile errors in the sources (they were never compiled); log each in Friction.
3. **Run the harness.** `run_tests` with `mode="PlayMode"`, `assembly_names=["Kit.Spike.Perf.Tests.PlayMode"]`, `init_timeout=120000`, then `get_test_job(wait_timeout=30)`. Read `Perf/spike-002/result.json`.
4. **Check the numbers.** `marker.valid` true and `count` 120 for both runs? ON p50 plausible for 200k sin calls (about 0.5 to 3 ms)? OFF p50 about 0? `gc_alloc_bytes` ON equals OFF? `main_thread` valid?
5. **Repeat 5 times** (same Editor session, no other work). Record ON p50 of each run and the spread. This gives the noise level for question 4.
6. **MCP read by name.** In Play Mode with the workload running (a scene with `SpikeWorkload` enabled, set up through the Editor via UnityMCP, **not** by editing a `.unity` file as text), call `manage_profiler get_counters` with explicit names only: `counters=["Kit.Spike.Workload"]` under the category the marker was registered in (Scripts). Note whether it returns a value and whether `profiler_start` is needed first.
7. **Does it need the Profiler?** Repeat step 3 once with `profiler_status` showing the profiler off, once with it on. Same numbers?
8. **Wrap up.** Fill Results, Friction, Proposals; update `docs/HANDOFF.md`; run `unity-check` (EditMode canary plus this PlayMode test); commit on the branch.

## Results
Times are Unity-side (job timestamps). `ProfilerRecorder` values for the marker are nanoseconds.

| Step | Tools used | Wall time | First try? | Notes |
|---|---|---|---|---|
| 1 | `refresh_unity`, `editor/state`, `run_tests` EditMode | compile+reload ~10 s; run 5.9 s | yes | Pin `#v10.3.0` resolved: canary PASS 3/3. |
| 2 | `refresh_unity`, `editor/state`, `read_console` | compile 0.13 s | yes | All new code compiled with no edits: the API names written from memory were all valid. 0 errors, 0 warnings. `.meta` generated for the new folders, asmdefs and scripts. |
| 3 | `run_tests` PlayMode (`init_timeout=120000`), `get_test_job(wait_timeout=60)` | 4-10 s per run | **no**, see below | First run FAILED: marker `count` was 30, expected 120. Cause: my assumption that a recorder started before warmup keeps only the last 120 samples was wrong (not explained further; 150 frames passed, `Count` was 30 for all three recorders). Fix: start the recorders after warmup. Then count = 120 in every run. |
| 4 | file read | n/a | yes | Marker, `GC Allocated In Frame` and `Main Thread` all `valid: true`, count 120. Marker OFF p50 = 0, ON p50 = 11.3 ms (200k `Mathf.Sin` in the Editor, Mono). GC alloc 21129 B per frame in **both** runs (Editor overhead, not the workload). |
| 5 | 5 x `run_tests` | 4-6 s each | yes | Table below. |
| 6 | `manage_editor play`, `manage_gameobject`, `manage_profiler get_counters` | n/a | **no** | Works only while a test holds Play Mode: 9,819,700 ns read by name, `valid: true`, unit `TimeNanoseconds`. See friction #3-#5. |
| 7 | `profiler_status`, `profiler_start`, `profiler_stop` | n/a | yes | Profiler was **off** during runs 1-5 and the recorders were valid. One run with it on: ON p50 10.7 ms (inside the off range). |

### Step 5 - noise (5 runs, same Editor session, Profiler off)
| Run | Editor focused | ON marker p50 (ms) | ON marker p95 (ms) | OFF main thread p50 (ms) | ON main thread p50 (ms) |
|---|---|---|---|---|---|
| 1 | no | 11.34 | 12.35 | 8.60 | 15.77 |
| 2 | yes | 11.30 | 12.46 | 16.65 | 17.50 |
| 3 | yes | 11.48 | 14.22 | 16.00 | 16.73 |
| 4 | yes | 12.88 | 15.32 | 16.49 | 17.32 |
| 5 | yes | 13.03 | 16.06 | 16.50 | 17.60 |

- Marker ON p50 spans 11.30-13.03 ms: about 15% min to max, about 7% either side of the middle (12.1). This is the noise to budget for in the Editor; a 5% tolerance would fail on noise alone, so compare ON vs OFF in the same run and use a wider tolerance (10-15%) until a player build exists.
- Marker OFF = 0 in all runs; ON/OFF difference is unmistakable.
- **Main Thread is not a usable cost metric here:** when the Editor is focused it sits at about 16.5 ms in OFF too (frame cap/vsync, 60 Hz), and 8.6 ms unfocused. The feature's own marker is the metric; frame time only shows whether the budget is blown.
- GC alloc per frame p50 was 21129 B in almost every run, ON equal to OFF; p95 varies (25-36 KB). A "0 GC alloc" budget cannot be checked from the whole-frame counter in the Editor; it needs a per-marker GC measure (or a player build).

## Friction log
1. **`ProfilerRecorder` buffer assumption was wrong.** Starting recorders before warmup gave `Count` 30, not the last 120. Start them after warmup. Cause of 30 not established.
2. **`manage_editor play` entry stalls while the Editor is unfocused.** After `play`, `editor/state` stayed in `phase: playmode_transition`, `is_changing: true` for 25+ s and `Update` never ran (`Sink` stayed 0). The test runner's Play Mode does not stall: `run_tests` works unfocused. So Play Mode measurements go through `run_tests`, not `manage_editor play`.
3. **Bridge unavailable after a Play Mode domain reload:** `manage_gameobject` returned "No Unity Editor instances found" twice in a row, then worked on the third try, while `read_console` worked in between. Retry after a reload.
4. **`manage_components set_property` is refused in Play Mode** ("This cannot be used during play mode"). `manage_gameobject create` with `component_properties` did set the field.
5. **`get_counters` returns 0 for a marker that is not running yet, with `valid: true`.** A 0 is not an error. A read taken before Play Mode started gave 0; one during the run gave 9.8 ms. Never treat a single read as a result.
6. **`[Explicit]` does not keep a test out of a whole-assembly `run_tests`** through this bridge: the 25 s hold test ran. The hold test was removed from the repo; the technique is in the Results.
7. **`editor/state` returns an empty placeholder** (`sequence: 0`, null sections) just after a reload. Re-read.
8. **Editor-side changes appeared in the working tree that this spike did not make:** `Assets/Settings/Mobile_RPAsset.asset` (URP asset upgraded 12 to 13 by Unity), `ProjectSettings/EditorSettings.asset` (`m_EnterPlayModeOptions` 0 to 1), `ProjectSettings.asset`, `ShaderGraphSettings.asset` (line endings only), `EditorBuildSettings.asset` (line endings only), and a new `SceneTemplateSettings.json`. Not committed. `m_EnterPlayModeOptions: 1` may relate to friction #2; not established.
9. `editor_is_focused` was `true` in runs 2-5 (the human or a nudge focused the Editor), contradicting D6. Numbers in focused runs differ for main thread; the marker did not change visibly.

## Proposals
1. **Harness shape confirmed.** Keep: warmup N, recorders started after warmup, M measured frames, OFF then ON in one run, p50/p95 per metric, one `result.json`. Promote this to the shared schema in plan §4.4 and template it.
2. **Gate on the marker, not on frame time.** Budget the feature's own marker (p50 and p95 ns); report main thread only as context.
3. **Tolerance:** compare ON vs OFF inside one run; if comparing to a baseline across runs, use 10-15% in the Editor (measured spread, step 5), tighter only with a player build.
4. **Run Play Mode measurements through `run_tests`** only; add a line to `unity-check` / a perf skill: do not use `manage_editor play` for measurement (friction #2).
5. **Results location:** `Perf/spike-002/result.json` is generated and not committed in this spike; decide in the perf skill whether baselines live in the project (`Perf/<feature>/baseline.json`) and results are ignored.
6. **GC budgets** need a per-marker allocation measure or a player build; the whole-frame counter has a 21 KB Editor floor.
7. **Next:** the `graphics-feature` skill and `perf_check.py` (which reads `result.json`, compares ON/OFF and budget), proved on one toy feature (a full-screen URP effect), with GPU time as the open question (this spike measured CPU only).

## Status
- 2026-10-12: **done**. Compiled with no edits, gate PASS: PlayMode 1/1 (`Kit.Spike.Perf.Tests.PlayMode`), EditMode canary 3/3, 0 console errors, 0 warnings. Not verified: GPU time, p50/p95 on a player build, whether the harness works for a render feature, why the recorder count was 30 (friction #1), friction #3 of Spike 001 (file rewrite; not investigated).
- Housekeeping: unity-mcp pinned to `v10.3.0` and verified by the canary run. Friction #3 experiment not done.
