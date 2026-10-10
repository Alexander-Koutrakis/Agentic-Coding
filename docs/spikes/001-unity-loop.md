# Spike 001 — Unity agent loop

Goal: prove that an agent in Claude Code can run the full loop **edit → refresh/compile → wait → read console → run tests → read results** through UnityMCP, with no human relaying anything. Record every friction point; they become the kit's first scripts and rules.

Branch: `spike/001-unity-loop` · Project: `Test Enviroments/Unity Agentic Kit test/`
Time-box: one session.

## Steps (agent)
For **every** step, record in the Results table: tool(s) used, wall time, whether it worked first try, and anything surprising.

1. **Baseline.** `git status` is clean (if not, stop and tell the human). Create the branch. Read the Unity console via UnityMCP; note any pre-existing messages.
2. **Runtime code.** Create `Assets/Kit/Spike/Runtime/` with an asmdef `Kit.Spike` and a small class `SpikeMath` (e.g. `static float Lerp01(float a, float b, float t)` clamping `t`).
3. **Compile.** Refresh + compile through UnityMCP. Find out how to know compiling has *finished* (does the tool block? does it return early? does the domain reload drop the MCP connection?). Read the console. Confirm `.meta` files were generated.
4. **Detect a compile error.** Introduce a deliberate syntax error. Refresh, wait, read console. Confirm the agent sees the error with file + line. Fix it, confirm the console is clean.
5. **EditMode tests.** Create `Assets/Kit/Spike/Tests/EditMode/` with asmdef `Kit.Spike.Tests.EditMode` (Editor-only, test assembly, references `Kit.Spike`) and 3 tests for `SpikeMath`. Compile, then run only these tests through `run_tests` and poll `get_test_job` until done.
6. **Detect a failing test.** Break one assertion on purpose. Run, confirm the failure and message are visible. Fix, re-run, all green.
7. **Profiler probe (prep for D7).** Using UnityMCP's profiler tool, find out what you can read in the Editor: frame CPU/GPU time? a custom `ProfilerMarker`'s timing? Just discover and note capabilities; don't build anything.
8. **Wrap up.** Fill in Results + Friction + Proposals below, update `docs/HANDOFF.md`, commit on the branch.

## Results
Times are Unity-side, from `editor/state` timestamps and test-job timestamps (agent turn overhead not included).

| Step | Tools used | Wall time | First try? | Notes |
|---|---|---|---|---|
| 1 | `git`, `read_console` | <1 s | yes | Tree clean, branch `spike/001-unity-loop` created. Console empty (0 entries) at first read; the MCP "bridge started" line only appeared later. |
| 2 | file tools (Write) | n/a | yes | `Kit.Spike.asmdef` + `SpikeMath.Lerp01` written as plain text. |
| 3 | `refresh_unity` (compile=request, force), resource `editor/state`, `read_console`, Glob | ~11 s to ready (compile 5.6 s, domain reload ends +5.7 s later) | yes, but see friction #1 | `refresh_unity` returned at once with `resulting_state: "compiling"` even with `wait_for_ready=true`. Had to poll `mcpforunity://editor/state` until `compilation.is_compiling=false` and `advice.ready_for_tools=true`. MCP connection survived the reload. `.meta` files generated for asmdef, .cs, and the folders (Kit.meta, Spike.meta, Runtime.meta). |
| 4 | file tools, `refresh_unity`, `editor/state`, `read_console(types=error)` | ~1 s (compile failed, no domain reload) | yes | Console showed `Assets\Kit\Spike\Runtime\SpikeMath.cs(9,35): error CS1002: ; expected`. File, line and column available. Fixed; the console then showed 0 errors/warnings. |
| 5 | file tools, `refresh_unity`, `editor/state`, `run_tests(assembly_names)`, `get_test_job(wait_timeout=30)` | compile+reload ~6 s, run ~5.4 s | yes | 3/3 passed, run reported 0.67 s. `get_test_job` with `wait_timeout` blocked until done: one poll was enough. |
| 6 | same as 5 | ~5.3 s run | yes (after one retry on my side, see friction #3) | Failure visible in `failures_so_far`: `Expected: 6.0d +/- 9.99e-06d But was: 5.0d` plus the full test name. After the fix: 3/3 green, console clean. |
| 7 | `manage_profiler`: `profiler_status`, `get_frame_timing`, `get_counters` | ~1 s each | yes | See capabilities below. |

### Step 7 — profiler capabilities (discovery only)
- `profiler_status`: reports enabled/recording and areas. CPU and GPU areas were **off**, profiler not enabled.
- `get_frame_timing`: works synchronously and returns 12 `FrameTimingManager` fields. In this idle, unfocused Editor the values were not usable: `cpu_frame_time_ms` 109.8, main thread 0.0004, render thread 0, `gpu_frame_time_ms` 0.
- `get_counters(category, counters[])`: reads by category. Without a `counters` list the Render category returned 2,049 keys (87 KB, over the tool-result token limit). With names it is small: `Batches Count`, `Draw Calls Count`, `SetPass Calls Count` = 0 (nothing rendering). `Memory`: `GC Allocated In Frame` = 10192 B, `GC Allocation In Frame Count` = 130.
- The Render category lists many URP marker names (e.g. `AddActiveLocalLights`), each as a time in nanoseconds. This suggests a custom `ProfilerMarker` could be read by name, **but I did not verify it**: no custom marker exists yet and no frames were rendering.
- Not tried: `profiler_start` recording to a `.raw` file, the Frame Debugger, memory snapshots, running the profiler during Play Mode. Not confirmed: GPU time per pass, p50/p95 over N frames (the tool reads one frame).

### Step 7 rerun — Editor focused, profiler on, Play Mode (SampleScene)
Sequence: `profiler_start` → `manage_editor play` → read → `manage_editor stop` → `profiler_stop`. Console stayed free of errors and warnings.

| Reading | Edit Mode, focused, profiler off | Play Mode, profiler on |
|---|---|---|
| `Batches / Draw Calls / SetPass Count` | 0 / 0 / 0 | 24 / 24 / 24 |
| `Triangles Count` | not read | 1703 |
| `GC Allocated In Frame` (bytes / count) | not read | 24871 / 409 (first sample, right after entering Play) |
| `cpu_frame_time_ms` | 0.32 | 0.24 (first sample), then 3.37 and 2.80 |
| `cpu_main_thread_frame_time_ms` | 0.0002 | 1.10 and 1.21 |
| `cpu_render_thread_frame_time_ms` | 0 | 1.04 and 1.05 |
| `gpu_frame_time_ms` | 0 | 0 (first sample), then **0.481 and 0.476** |
| URP marker `AddActiveLocalLights` | n/a | 300 ns (single frame, by name) |

Conclusions:
- Focus alone is not enough: **Edit Mode shows zeros even when focused**. Rendering has to be running (Play Mode).
- The first sample right after entering Play Mode is warm-up and unusable. Samples taken a moment later gave consistent numbers (GPU 0.481 vs 0.476 ms, CPU main 1.10 vs 1.21 ms). `FrameTimingManager` GPU time works on this machine in Play Mode.
- Markers are readable by name through `get_counters` (URP's `AddActiveLocalLights` returned a nanosecond value). A **custom** `ProfilerMarker` is still unverified.
- Each read is one frame; two reads are only a rough check. A harness needs its own N-frame sampling inside the player loop, not tool calls.
- Still not tried: `.raw` recording, Frame Debugger, memory snapshots.

## Friction log
1. **`refresh_unity` does not wait.** `wait_for_ready=true` returned `resulting_state: "compiling"` immediately. Every compile needs a separate poll of `editor/state` (resource, not a tool). The compile was often already finished by the time of my first poll, so one poll was enough here, but nothing guarantees that.
2. **A compile error leaves no domain reload**, so `last_domain_reload_after` does not change; "finished" must be read from `compilation.last_compile_finished_unix_ms` and `is_compiling`, not from reload timestamps. After the fix the old error was gone from the console with no explicit clear.
3. **File changed under me.** After I introduced the failing assertion, the test file on disk read `Assert.AreEqual(6f,SpikeMath...` (space after the comma removed) instead of what I wrote, so my first `Edit` back failed with "String to replace not found". I do not know what rewrote it (Unity or MCP script tooling, an editor/formatter, or something else). I re-read and fixed it. Lesson: re-read before editing a file that Unity has compiled. This is unexplained and worth watching.
4. **Console noise:** the first non-empty console read contained MCP-for-Unity's own lines (bridge started; "Suppressed duplicate command resent on a new connection"). Filtering by `types=["error"]` avoids it, but a "clean console" check must ignore those.
5. **`get_counters` without names is huge** (87 KB), exceeds the tool-result limit and gets dumped to a file. Always pass counter names.
6. **Profiler numbers from the Edit Mode Editor are zeros, focused or not** (GPU time 0, draw calls 0). Rendering must be running: Play Mode works, and the first sample after entering it is warm-up. See the step 7 rerun.
7. `refresh_unity` with `scope=scripts` reported `refresh_triggered: false` while still compiling; harmless, but the field is confusing.
8. The Test Runner job reported success/fail in status only; the passed tests list was empty unless `include_details=true` (I used it once to see all 3 names).
9. The Unity-side `git status` afterwards shows `Assets/Kit.meta` and `Assets/Kit/` as untracked: `.meta` files must be committed together with the assets (done in the commit).

## Proposals
1. **Script `unity_wait_ready`** (Python or an MCP-side skill step): poll `editor/state` until `is_compiling=false` and `ready_for_tools=true`, with a timeout, and print one line (`compiled in 5.6s, ready`). Rule in CLAUDE.md: "after `refresh_unity`, always run the wait step; do not trust the refresh return value."
2. **Script `unity_check`** (the first gate, ties into §4.1): refresh → wait → read console errors only → `run_tests` → `get_test_job(wait_timeout)` → one-line summary `PASS 3/3` or the failure messages with file:line. This is the building block for `check`.
3. **Console rule:** read with `types=["error"]` (and warnings separately) and ignore lines starting with `MCP-FOR-UNITY`. A task is not done while errors exist (already in CLAUDE.md).
4. **Rule:** re-read a source file before editing it after any compile, because something may rewrite it (friction #3). Find out what does it (open question; try changing the same file and compare bytes after a compile).
5. **Profiler skill step:** always call `get_counters` with explicit counter names; never a whole category. The perf harness (D7) must render frames itself (Play Mode run or scripted renders) and cannot rely on the idle Editor. Next spike: a Performance Test that wraps a `ProfilerMarker`, runs N frames in Play Mode, and checks the marker can be read by name through `get_counters` or the Performance Testing package.
6. **Test project hygiene:** commit `.meta` files with their assets; consider a pre-commit check that every file under `Assets/` has a `.meta`.
