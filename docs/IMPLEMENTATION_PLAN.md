# Implementation Plan — Agentic Coding Kit for Game & Graphics

Owner: Alexandros · Living document: every decision we make lands here.
Agents: read this, then `docs/HANDOFF.md`, before doing anything.

## 1. Goal
A kit (skills, rules, Python scripts, logs) that lets AI coding agents design, implement,
debug, optimize and maintain game and graphics code — Unity/C# first, C++/Vulkan alongside,
Unreal and Godot later — and **verify their own work**.

Not a general coding assistant. Not a set of "be a good Unity dev" prompts.

## 2. Principles
1. **Verification first.** A capability doesn't exist until the agent can check it and get pass/fail.
2. **Deterministic steps live in scripts**, not in prompts. Judgment is for the agent; plumbing is for Python.
3. **Fix the environment, not the agent.** A mistake seen twice becomes a script, lint, test or hook (logged in the friction log).
4. **One-way doors need approval:** deleting data, touching scenes/prefabs outside the editor, pushing, publishing, changing shared settings.
5. **Small, fast, quiet tools.** Short output, logs to files, never hang.
6. **Engine-agnostic core, engine adapters at the edge.** Unity now; Unreal/Godot plug in later.

## 3. Decisions log
| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-10-10 | Start from scratch; don't copy existing skill sets (read them for ideas only). | Own the standard; avoid inherited assumptions. |
| D2 | 2026-10-10 | Two workflows: **Engine** track and **Pure-code** track, on a shared core. | Per-task worktrees of a Unity project copy `Library/` → too slow and too big. Pure code can use cheap worktrees. |
| D3 | 2026-10-10 | This repo holds the kit: skills, rules, Python scripts, logs, docs. Target game projects stay separate repos. | Kit is reusable across projects. |
| D4 | 2026-10-10 | Plan + handoff live in the repo as Markdown (`docs/`). | Agents read files in the repo. |
| D6 | 2026-10-10 | While an agent runs a Unity task, the human does not use the Editor. Editor lock is enough; no pause/hand-back protocol for now. | Simplest model; revisit if it gets in the way. |
| D7 | 2026-10-10 | Every graphics feature ships with a **perf harness** and a **budget**; the feature isn't done until the harness runs and the result is within budget (see §4.4). **v1 uses the Unity Profiler in the Editor only**; player builds later. | Performance is part of correctness for graphics work. |
| D8 | 2026-10-10 | **Unity kit first**, finished before starting the pure-code (C++/Vulkan) kit. | Focus. |
| D9 | 2026-10-10 | Kit runs in **Claude Code**; Unity bridge = **CoplayDev/unity-mcp over stdio**. | Claude Code supports skills, hooks, subagents; stdio keeps it local. |
| D11 | 2026-10-10 | Unity gates are **skills over UnityMCP calls** (`unity-wait-ready`, `unity-check`), not Python scripts. | The stdio bridge closes other clients when a new one connects, so a script would cut Claude Code's link. Revisit with HTTP transport if script gates become necessary. |
| D12 | 2026-10-10 | Spike 001 merged into `main`. `Assets/Kit/Spike` stays in the test project as the **canary** fixture: the known-good reference for `unity-check` (3 EditMode tests). | The gate needs a fixture that must always pass. |
| D13 | 2026-10-10 | Until we package the kit (plugin vs `.claude/skills`, open question), `CLAUDE.md` points to skills by path, so they are followed every time instead of relying on auto-discovery. | Deterministic for now; packaging decided later. |
| D14 | 2026-10-12 | **Perf harness guideline** (plan §4.4): each rendering feature gets a harness designed with the human; the guideline gives the defaults: 100 warmup + 300 measured frames, median and p95 in ms for main thread, render thread and GPU, a sweep over instance count, and a linear fit giving ms per 1000 instances. Every run writes a log. | The cost of a feature is its slope, not one number. The human chooses the sweep per feature; the kit supplies the machinery. |
| D15 | 2026-10-12 | **Editor GPU numbers are relative-only** (Editor Profiler GPU module). Good enough to compare ON vs OFF and slopes on one machine; real numbers need a development player build (later). | Spike 002: Editor numbers are noisy (marker p50 spread ~15%) and frame-capped unless vsync is off. |
| D16 | 2026-10-12 | **Harness split:** a C# runner (Play Mode test) only collects raw per-frame samples and writes files; a **Python script** reads them and does medians, p95, regression and the budget check. | Python reading files never touches the bridge, so D11 allows it. The math is testable without Unity. |
| D10 | 2026-10-10 | Test project: `Test Enviroments/Unity Agentic Kit test` — Unity **6000.3.10f1**, **URP 17.3**, Test Framework 1.6.0. Root `.gitignore` always ignores `Library/`; each Unity project has its own anchored `.gitignore`. | Reproducible sandbox for the kit. |
| D5 | 2026-10-10 | **Unity: no parallel sandboxes.** One open Editor is the single source of truth, driven through an MCP bridge. Agents work **one task at a time**, in sequence, on the same checkout; the next task starts only after the current one is verified. Slot pool / Accelerator / Dev Drive ideas are parked. | Parallel Unity environments are a lot of work and may perform poorly. Serial work on one live editor is simpler and keeps one truth. |

## 4. Architecture (draft)

```
<kit repo>
├── AGENTS.md / CLAUDE.md        rules for agents working ON the kit
├── docs/
│   ├── IMPLEMENTATION_PLAN.md   this file
│   ├── HANDOFF.md               current state, next step (updated every session)
│   ├── research/                dated research notes
│   └── decisions/               longer write-ups when a decision needs one
├── skills/
│   ├── core/                    process: plan, handoff, verify-gate, review, friction-to-structure
│   ├── unity/                   engine track
│   └── native/                  C++/C#/Vulkan track
├── scripts/                     Python (uv), each a CLI with short output + exit code
│   ├── core/  unity/  native/
├── templates/                   AGENTS.md, task card, handoff for TARGET projects
└── logs/
    ├── friction-log.md          repeated mistakes → what structure fixed them
    └── sessions/                optional per-session notes
```

Skill standard: six parts — when to use · inputs & access · steps · how to validate · what to return · approvals.

### 4.1 Engine track (Unity first) — single live Editor (D5)
Model: **one project checkout, one open Editor, one task at a time.**
- The agent drives the Editor through an MCP bridge (candidate: CoplayDev/unity-mcp) wrapped by our skills:
  refresh/compile → read console → run tests (async job) → inspect scene/profiler.
- Multiple agents may work on the **same task in sequence** (e.g. planner → implementer → reviewer), never on different tasks at once.
- Task flow: clean tree check → branch for the task → work → gate passes → commit → handoff updated → next task.
- **Editor lock:** a small lock file (`.agent/editor.lock`: owner, task, start time) so only one agent sends Editor commands; stale-lock rule.
- **Human + agent share the Editor:** agent checks for uncommitted human changes before starting and stops if found; the human doesn't edit while a task runs (or pauses the agent).
- **Domain reload / compile waits:** every script change is followed by refresh → wait for compile to finish → read console; a script handles the waiting and returns a short result.
- Batchmode can't open the project while the Editor has it open → the gate runs **through the bridge**; the batchmode test wrapper is only for CI or when the Editor is closed.
- Scene/prefab/asset safety rules: no YAML hand-edits, changes through the Editor only, `.meta` always moves with its asset.

### 4.2 Pure-code track (C++ / C# / Vulkan)
- Plain git worktrees per task; shared compiler cache.
- Gate: configure/build (CMake presets) → unit tests → sanitizers → clang-tidy → **validation-layer errors = failure** → golden-image diff.
- Frame inspection: RenderDoc capture + Python replay → JSON summary the agent can read.

### 4.4 Graphics feature perf harness (D7, D14-D16)
Enforced in three layers, weakest to strongest:
1. **Rule** (AGENTS.md, one line): "A graphics feature is done only when its perf harness runs and is within budget."
2. **Skill** `graphics-feature`: *agree the sweep with the human -> declare budget -> instrument -> generate harness from template -> record baseline -> run -> analyze -> compare*.
3. **Gate** `perf_check.py` (part of `check`): fails if a feature folder has no `perf/feature.json`, no result, or the result is over budget / regressed vs baseline.

**The harness is designed per feature, with the human.** What follows is the guideline and the defaults, not a fixed recipe. Which parameter is swept (instances, resolution, shadow cascades, samples), the budget and the reference scene are decided in the conversation and written into `perf/feature.json`.

#### Measurement rules (defaults, overridable per feature)
- **Frames:** discard the first **100** (warmup), record the next **300**, per sweep point. Recorders start after warmup (Spike 002: recorders started earlier did not hold the expected sample count).
- **Metrics, all in ms** (convert from ns once, when writing the result; fields named `main_ms`, `render_ms`, `gpu_ms`, `feature_ms`): main thread, render thread, GPU frame, and the feature's own marker/pass. Per metric: **median and p95** over the 300 frames. Whole-frame GC bytes are recorded as context.
- **Unfreeze the frame rate:** `vSyncCount = 0`, `targetFrameRate = -1`, fixed resolution and quality level, so main-thread and GPU time are not capped (Spike 002: main thread sat at ~16.5 ms, the frame cap).
- **Deterministic scene:** fixed camera or scripted path, fixed random seed, fixed time/wind/animation, same camera at every sweep point.
- **Feature ON vs OFF** in the same run; the **N = 0 point with the feature on** gives its fixed cost.
- **Editor numbers are relative only** (D15): compare inside one run or against a baseline from the same machine.

#### Sweep and slope
- Sweep a quality parameter N over a list chosen with the human, e.g. `[1000, 3000, 6000, 10000, 50000, 100000]` instances. Always include the baseline point (N = 0 or feature off) first and last (drift check). Repeat each point (default 3 runs) in randomized order for an error bar.
- **Fit each metric separately** (least squares of the per-point median against N). Report **ms per 1000 instances** (slope x 1000), the **intercept** (fixed cost), **R^2**, and the slopes of the lower and upper halves of the sweep.
- Frame time is about max(CPU, GPU): fitting only frame time hides GPU cost in a CPU-bound scene. Treat the feature's own pass/marker as the primary metric and the thread times as context.
- If R^2 is low or the half-slopes disagree, the report says "not linear in this range" and gives the points, not one number. Small N may sit below the noise floor (Spike 002: ~15% spread on a 12 ms marker); trust the slope from the large counts over the cost at the small ones.

#### Logs and files (D16)
Per run, in `perf/<feature>/runs/<timestamp>-<n>/`:
- `run.json`: config (frames, sweep point, seed), git commit, Unity version, machine id, GPU name, resolution, quality level, Editor or player, and per-metric median/p95 in ms.
- `frames.csv`: raw per-frame samples in ms, so the analysis can be redone without Unity.
- One line appended to `perf/<feature>/index.jsonl` (timestamp, N, path, key numbers).
The **C# runner** (Play Mode test through `run_tests`; do not use `manage_editor play`, Spike 002 friction #2) writes these files and returns one summary line. The **Python script** (`perf_analyze.py`) reads them and writes `perf/<feature>/report.json` with per-point stats, the fits, the budget verdicts, and a short text summary. Each result is baselined once accepted; later runs compare against it, with 10-15% tolerance in the Editor (Spike 002 spread), tighter with a player build.

#### Budgets
Declared in the task card and `feature.json`: a per-1000-instances cost, a total at the real in-game count, and optional GC limits (whole-frame GC has a ~21 KB Editor floor; per-marker GC needs a different measure or a player build).

#### Open
- GPU and render-thread timing API in the Editor: unverified (Spike 003 probes it).
- GPU cost per pass: `ProfilingSampler`/`ScriptableRenderPass` scope vs frame GPU time.
- Player-build numbers (later phase).

### 4.5 Unity gate ladder (proposed, 2026-10-10)
`unity-check` becomes a list of gates, run cheapest first, stop at the first FAIL. Gates that only read files on disk (format, metas, scope, banned APIs) may be plain Python scripts: D11 only forbids scripts that talk to the bridge.

| Tier | Gate | How | Status |
|---|---|---|---|
| Every iteration | **Format** | `.editorconfig` + `dotnet format --verify-no-changes` on changed files (uses Unity-generated `.sln`) | to build |
| | **Compile + console** | `unity-wait-ready` + console errors | built |
| Before "done" | **Analyzers** | Roslyn analyzers (incl. Microsoft.Unity.Analyzers) as Unity RoslynAnalyzer DLLs; severities in `.editorconfig`; their warnings show in the console | to build |
| | **Code rules** | script: no `UnityEditor` in runtime asmdefs without `#if UNITY_EDITOR`, banned APIs in hot paths (`GameObject.Find`, `FindObjectOfType`, LINQ/allocations in `Update`), no leftover `Debug.Log` | to build |
| | **Asset integrity** | script: every file under `Assets/` has a `.meta`, no orphan `.meta`, no duplicate GUIDs; MCP: no missing scripts in changed scenes/prefabs | to build |
| | **Scope** | script on `git diff`: only files the task card allows; no test deleted/weakened; `ProjectSettings/` and `Packages/` changes need approval | to build |
| | **Tests** | EditMode (built) + PlayMode; new code has new tests | partly built |
| Graphics feature | **Shader** | shader compile errors/warnings via console/MCP | to build |
| | **Perf** | harness exists, runs in Play Mode, sweep slope and totals within budget (D7, D14-D16 / §4.4) | Spike 003 |
| | **Visual** | fixed-camera screenshot vs reference image with tolerance | later |
| Before merge | **Player build** | development build compiles (catches Editor-only code in runtime) + full test suite | later |

Pipeline per task: task card (goal, scope, budget, acceptance) → **implementer** works and loops on the gate until PASS (give up after N tries → report BLOCKED with evidence) → **reviewer** agent in a fresh context checks the diff against the task card (the gate proves it works, the reviewer checks it is what was asked) → report to human with the PASS line, evidence and review notes.

### 4.3 Shared core
Single gate command per project (`check`), progress/handoff protocol, task cards, friction log,
review pack (repo zip for a bigger model), approval list.

## 5. Phases
| Phase | Outcome | Exit criterion |
|---|---|---|
| 0 Foundation | Repo layout, AGENTS.md, skill standard + linter, handoff protocol | A fresh agent can pick up work from HANDOFF.md alone |
| 1 Verification | Unity: MCP bridge installed, editor lock, compile-wait + console parser, test-run via bridge. Native: build+test+validation gate | Each track has one command returning pass/fail with a short summary |
| 2 Skills | Common jobs: fix compile error, write+run test, profile a frame, shader change, asset-safe refactor | Each skill passes its own validation on a sample project |
| 3 Coordination | Unity: planner → implementer → reviewer in sequence on one task. Native: parallel worker agents in worktrees | Unity: a task passes review without human relaying. Native: two tasks run in parallel and merge cleanly |
| 4 Routines | Triggered runs (CI failure, bug report) with approval stops | Unattended run ends in a reviewed draft PR |

## 6. Open questions
- [x] First track → Unity (D8).
- [x] Harness → Claude Code (D9). Codex support: later, maybe.
- [x] Unity version / pipeline for the test project → 6000.3.10f1, URP (D10).
- [x] MCP bridge → CoplayDev/unity-mcp, stdio (D9). Pin to a release tag instead of `#main`.
- [ ] Git LFS + Unity YAML merge (`.gitattributes`) for binary assets and scenes?
- [ ] Rename folders without spaces/typos (`Test Enviroments`) before scripts depend on the paths?
- [ ] Unity branching: one branch per task, or work on a single feature branch with a commit per task?
- [x] While an agent runs, does the human keep using the Editor? → No, human steps away (D6).
- [ ] Reference machine + resolution for perf budgets; render pipeline (URP/HDRP/custom SRP).
- [ ] Test project: brand-new small Unity project, or a copy of a real one?
- [ ] Distribution of the kit into target projects: Claude Code plugin, git submodule, or copy script?
- [ ] Sample projects for testing the kit (small Unity project, small Vulkan renderer).
