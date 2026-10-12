# HANDOFF

Read this first, then `docs/IMPLEMENTATION_PLAN.md`. Update it at the end of every session
(newest entry on top, keep the "Current state" block current).

## Current state
- Phase: **1 — Verification (Unity)**. Spikes 001-003 are merged into `main` (D12, D17; local only, not pushed). Spikes 002 and 003: the sweep harness (main/render/GPU/feature ms, slope per 1000 instances, run logs) works on a toy rendering feature. Spike 001 merged into `main` (D12); gate skills `unity-wait-ready` + `unity-check` in `skills/unity/`, wired into CLAUDE.md (D11, D13).
- Repo contains: docs, CLAUDE.md, gate skills, perf skill `skills/unity/unity-perf-harness`, `scripts/unity/perf_analyze.py` (+15 tests), Unity test project with the canary `Assets/Kit/Spike/` (3 EditMode tests) and the perf library `Assets/Kit/Perf/` (`Kit.Perf` runner/writer, toy feature, sweep tests).
- **The kit is ready for Trial 001**: build a new rendering feature with another agent following the kit; protocol in `docs/trials/001-rendering-feature.md`.
- The loop edit → refresh → wait → console → tests works through UnityMCP with no human relaying. Biggest gap: `refresh_unity` does not wait for compile; poll `mcpforunity://editor/state`.
- Open (plan §6): the questions still unchecked.

## Next step
1. **Trial 001** (`docs/trials/001-rendering-feature.md`): the human and a second agent build a real rendering feature with the kit; record friction; turn repeats into structure. Fill the task card (feature, sweep points, budget, reference scene) with the agent first.
2. Housekeeping still open: friction #3 of Spike 001 (what rewrote `SpikeMathTests.cs`); review the Editor-made settings changes (list in the 2026-10-12 Spike 002 entry; still uncommitted in the working tree) and decide commit or revert; push `main` when you want it on `origin` (4 commits ahead); the spike branches `spike/002-profiler-harness` and `spike/003-sweep-harness` can be deleted (their commits are in `main`).
3. Spike 003 proposals: loaded reference point for the drift check; `perf_check.py` as a gate over `report.json` and into `unity-check`; per-pass GPU time (`ProfilingSampler`); baselines (`Perf/<feature>/baseline.json`).
4. Kit repo skeleton (§4 layout: `scripts/`, `templates/`, `logs/`), root AGENTS.md, skill template, skill linter.
5. Later: player-build numbers, visual gate (screenshot diff), shader gate.

## Session log
### 2026-10-12 (end) — spike branches merged into main
- `main` fast-forwarded from `70a0071` to `26d3ca3` (history was linear: 002 on top of main, 003 on top of 002), so Spikes 002 and 003 are in `main`: Spike 002 harness, plan §4.4 + D14-D16, `Kit.Perf`, `perf_analyze.py`, skill `unity-perf-harness`, `justfile`, Trial 001 protocol. Done as a local ref update (`git fetch . spike/003-sweep-harness:main`) so the Editor's working files were not swapped. Nothing pushed: `main` is 4 commits ahead of `origin/main`.
- `just check` (new): runs the 15 Python tests, exit 0; Unity is still gated by `unity-check` through UnityMCP.
- Not merged and still in the working tree, uncommitted: Editor-made changes to `Mobile_RPAsset.asset`, `EditorSettings.asset`, `ProjectSettings.asset`, `ShaderGraphSettings.asset`, `EditorBuildSettings.asset`, new `SceneTemplateSettings.json`.
- Next: Trial 001 on a branch `trial/001-<feature>` from `main`.

### 2026-10-12 (later) — Spike 003: sweep harness + analyzer + perf skill
- Branch `spike/003-sweep-harness` (from `spike/002-...`). Plan §4.4 rewritten with the guideline; decisions D14 (guideline defaults: 100 warmup + 300 measured frames, median/p95 in ms, sweep + slope, log every run), D15 (Editor GPU numbers relative-only), D16 (C# collects raw samples, Python analyzes).
- Built `Assets/Kit/Perf/` (runner, writer, toy feature, sweep tests), `scripts/unity/perf_analyze.py` (15 tests, all pass), skill `unity-perf-harness`, `CLAUDE.md` pointer, `Perf/.gitignore` + `Perf/toy-instances/feature.json`. Details, results and friction: `docs/spikes/003-sweep-harness.md`.
- Verified: console 0 errors / 0 warnings; EditMode canary 3/3; Spike 002 PlayMode 1/1; two full sweeps of 20 runs each pass (about 70 s each); analyzer cross-check against the C# stats had no mismatch.
- Findings: Editor gives GPU and render-thread time (FrameTimingManager, 4 frames late); loaded-range slopes reproduce within about 15% across two sweeps (GPU 0.032 vs 0.027 ms per 1000); GPU time at light load is inflated and not monotonic, so the fit supports `fit_min_n`; main-thread time has no signal for this feature; `ProfilerRecorder` resets at capacity and its first sample is partial (handled).
- Not verified: per-pass GPU time, player build, any other machine, a real feature. The drift warning is noisy (baseline is an idle point).
- Trial 001 protocol written (`docs/trials/001-rendering-feature.md`); not started.

### 2026-10-12 — Spike 002 run (Play Mode profiler harness) + housekeeping
- Branch `spike/002-profiler-harness`. Harness under `Assets/Kit/Spike/Perf/` (workload + `ProfilerMarker`, PlayMode test with `ProfilerRecorder`, OFF vs ON, p50/p95, `Perf/spike-002/result.json`). Results, friction and proposals in `docs/spikes/002-profiler-harness.md`.
- Gate: PlayMode 1/1, EditMode canary 3/3, 0 console errors, 0 warnings. Code compiled without edits; the one failure (sample count 30 vs 120) was my buffer assumption, fixed by starting the recorders after warmup.
- Findings: the custom marker is readable by name (in a test and through `get_counters`); `ProfilerRecorder` works with the Profiler off; Editor noise on the marker p50 is about 15% min to max over 5 runs; main-thread time is frame-capped and not a cost metric; whole-frame GC has a 21 KB Editor floor; `manage_editor play` stalls while the Editor is unfocused, use `run_tests`.
- Housekeeping: unity-mcp pinned to `#v10.3.0` (same commit as before, canary passes). Friction #3 (file rewrite) NOT investigated.
- Not done: GPU time, player-build numbers, a render feature. `Perf/` results are not committed (decision pending).
- Left uncommitted on purpose: Editor-made changes (`Mobile_RPAsset.asset` URP upgrade, `EditorSettings.asset` EnterPlayModeOptions 0 to 1, `ProjectSettings.asset`, `ShaderGraphSettings.asset`, `EditorBuildSettings.asset`, `SceneTemplateSettings.json`). Review them with the human.

### 2026-10-10 — review of Spike 001 (Cowork)
- Reviewed spike results and both gate skills: accepted. Decisions D11 (gates are skills over MCP), D12 (merge; Spike code stays as canary), D13 (CLAUDE.md references skills by path).
- CLAUDE.md: added gate section and rules from proposals 3–5 and friction #11 (no direct bridge connection).

### 2026-10-10 (spike follow-up) — gate skills + profiler rerun
- Profiler rerun, Editor focused: Edit Mode still gives zeros; in Play Mode (profiler on) draw calls 24, triangles 1703, GPU 0.48 ms, CPU main ~1.1 ms. First sample after entering Play is warm-up. Details in the spike doc.
- Decision: `unity_wait_ready` / `unity_check` are **skills over MCP calls**, not Python scripts. Reason: the stdio bridge closes other clients when a new one connects (StdioBridgeHost.cs:605-620), so a script would cut Claude Code's own link. HTTP transport would make scripts possible later.
- Ran the skills as written: PASS 3/3, 0 errors, 0 warnings. Found `stale_status` blocking readiness while focused; cleared by one tool call; documented.
- Not done: CLAUDE.md rules; skill discovery path; nothing pushed.

### 2026-10-10 (spike) — Spike 001, Unity loop
- Ran all 7 steps on branch `spike/001-unity-loop`; results in `docs/spikes/001-unity-loop.md`.
- Worked: compile detection (error with file+line+column), `.meta` generation, `run_tests` + `get_test_job(wait_timeout)`, pass and fail messages, `manage_profiler` reads.
- Friction: `refresh_unity` returns before compile ends; an unexplained rewrite of a test file; profiler values from an idle Editor are zeros; `get_counters` without names returns 87 KB.
- Not verified: reading a custom `ProfilerMarker`, GPU time, multi-frame stats.
- Not done: nothing pushed or merged.

### 2026-10-10 (later) — D7 accepted, D8–D10
- Unity kit first; v1 perf = Editor Profiler; Claude Code + CoplayDev over stdio.
- Test project added (Unity 6000.3.10f1, URP 17.3); unity-mcp installed from `#main` (should be pinned).
- Added root `.gitignore` (Library safety net, Python, .agent/) and an anchored Unity `.gitignore` in the test project; verified on a mock layout.
- The Cowork cloud session cannot see the stdio MCP server — the spike must run from Claude Code on the machine.
- Setup friction #1: "Claude CLI not found" — Claude Code not installed. unity-mcp looks for the CLI via an EditorPrefs override → `CLAUDE_CLI` env var → `%USERPROFILE%\.local\bin\claude.exe` and other common paths → PATH. It needs `uv`/`uvx` for stdio.
- Setup note: unity-mcp registers the server with `claude mcp add --scope local` **in the Unity project folder** by default. The kit runs Claude Code from the **repo root**, so set the client project-dir override in the MCP for Unity window to the repo root (or the server won't appear there).

### 2026-10-10 (later) — D6, D7
- D6: human doesn't use the Editor while an agent runs.
- D7 (proposed): graphics features must ship a perf harness + budget; spec in plan §4.4.
- First-step sequence proposed: test project → bridge spike → repo skeleton → graphics-feature skill + perf harness on one toy feature.

### 2026-10-10 (later) — decision D5
- Unity track: no parallel sandboxes. Single open Editor = source of truth via MCP; one task at a time, agents work sequentially on the same task. Slot pool parked. Plan §4.1, §5, §6 updated.

### 2026-10-10 — Claude + Alexandros
- Read SpaceXAI blueprint and banteg/agents; agreed verification-first, shared core + two tracks.
- Decided D1–D4 (start fresh; engine vs pure-code split due to Unity Library cost; kit repo layout; docs in repo).
- Research pass written to `docs/research/2026-10-10-landscape.md` (WebSearch was disabled; known sources only).
- Proposed slot-pool model for Unity parallelism.
