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
7. **Catch problems early and cheaply.** A flaw found in the brief or plan costs lines; the same flaw found after coding costs a rewrite plus gate loops. Spend review effort before code, and spend tokens only where a fresh context helps.
8. **Tokens and time are a budget.** Match the pipeline to the size of the change (§4.6 tiers); every agent loads only its role file, its style guide and its input file; no new gate until a mistake has repeated (principle 3).

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
| D12 | 2026-10-10 | Spike 001 merged into `main` (done 2026-10-11, fast-forward). `Assets/Kit/Spike` stays in the test project as the **canary** fixture: the known-good reference for `unity-check` (3 EditMode tests). | The gate needs a fixture that must always pass. |
| D13 | 2026-10-10 | Until we package the kit (plugin vs `.claude/skills`, open question), `CLAUDE.md` points to skills by path, so they are followed every time instead of relying on auto-discovery. | Deterministic for now; packaging decided later. |
| D14 | 2026-10-11 | **Merge routine:** agents finish on a task branch and never push or merge. Alexandros reviews and merges into `main` (GitHub PR preferred, local merge allowed), then `unity-check` must PASS on `main`. | One human gate on what lands in `main`. |
| D10 | 2026-10-10 | Test project: `Test Environments/Unity Agentic Kit test` — Unity **6000.3.10f1**, **URP 17.3**, Test Framework 1.6.0. Root `.gitignore` always ignores `Library/`; each Unity project has its own anchored `.gitignore`. | Reproducible sandbox for the kit. |
| D15 | 2026-10-11 | **Feature pipeline** (§4.6): Architect → Director → plan reviewers → **human approves the plan** → coders (task cards) → gate → code reviewer. Brief, plan and task card have fixed formats checked by script. | Moves review before code; each stage hands a file to the next so no agent needs the whole conversation. |
| D16 | 2026-10-11 | **Three tiers** by change size: small (coder + gate only), medium (short brief, plan, 1–2 plan reviewers), large (full pipeline). Most features are expected to be medium. | A full pipeline on a small change costs more than the change. |
| D17 | 2026-10-11 | **Plan review = 2–3 reviewers with different lenses and a veto** (any one can block a critical error, with evidence). No percentage vote. Add reviewers only on large plans. | Same-model reviewers make correlated mistakes; five agreeing is not five opinions; cost is 5x. |
| D18 | 2026-10-11 | **Rules in three layers:** process rules (all agents), **style guides** (one short page per role: C# architecture, shader), **behavior rule** (Ponytail ladder, minimum code). Each agent loads only its layers. Priority: plan and style guide decide structure; Ponytail only decides how much code goes inside it. | Token cost and clashing styles. |
| D19 | 2026-10-11 | **Ponytail** (github.com/dietrichgebert/ponytail) is adopted as an idea only: its "does it need to exist → reuse → stdlib → native → dependency → one line → minimum code" ladder goes into the coder, Director and reviewer role files. We do not install its plugin or commands. Its benchmark numbers (−45% tokens) are the project's own and unverified for us. | Avoid carrying extras; verify the claim on our own tasks. |
| D20 | 2026-10-11 | **Freeze the gate ladder** (§4.5) until a mistake repeats. Style rules that can be checked mechanically become code-rules checks (e.g. KIT005 methods with more than N parameters → use a struct); the rest are left to the reviewer. | Avoid overengineering; scripts cost no tokens. |
| D21 | 2026-10-12 | **Perf harness guideline** (plan §4.4): each rendering feature gets a harness designed with the human; the guideline gives the defaults: 100 warmup + 300 measured frames, median and p95 in ms for main thread, render thread and GPU, a sweep over instance count, and a linear fit giving ms per 1000 instances. Every run writes a log. | The cost of a feature is its slope, not one number. The human chooses the sweep per feature; the kit supplies the machinery. |
| D22 | 2026-10-12 | **Editor GPU numbers are relative-only** (Editor Profiler GPU module). Good enough to compare ON vs OFF and slopes on one machine; real numbers need a development player build (later). | Spike 002: Editor numbers are noisy (marker p50 spread ~15%) and frame-capped unless vsync is off. |
| D23 | 2026-10-12 | **Harness split:** a C# runner (Play Mode test) only collects raw per-frame samples and writes files; a **Python script** reads them and does medians, p95, regression and the budget check. | Python reading files never touches the bridge, so D11 allows it. The math is testable without Unity. |
| D24 | 2026-10-12 | Spikes 002 and 003 merged into `main`. `Assets/Kit/Perf` (`Kit.Perf` library, `Kit.Perf.Toy`, sweep tests) stays in the test project as the **perf canary**: the known-good reference for `unity-perf-harness` and `perf_analyze.py`. `just check` is the shell-side gate; Unity stays with `unity-check`. | Same reasoning as D12: the harness needs a fixture that must always run. |
| D25 | 2026-10-12 | **Keep the feature pipeline as it is** after Trial 001 (human decision, 2026-10-12): the structure stays, the friction list drives improvements. | Trial 001 showed the evidence-producing parts (plan review, code review, readback test, perf harness) earn their cost; the cost and the console-only shader gate are the weak parts. |
| D26 | 2026-10-12 | **Shaders in Trial 001 were allowed by the human** (GPU culling needs a compute shader and an indirect-draw shader) although the shader gate does not exist; the baseline for a feature is stored as `Perf/<feature>/baseline.json` (accepted by the human, no script reads it yet). | The first graphics feature needed both; the gate and baseline comparison remain to build. |
| D27 | 2026-10-12 | **Out of scope (human decision):** the shader gate (including a screenshot check for new shaders), a total budget for the 1M-blade grass sweep, and a control run of Trial 001 without the kit. Removed from the plan and the open lists. | Focus on the friction fixes first. Shaders are still written; their only gate is the console. |
| D28 | 2026-10-12 | **Gate plumbing (friction T1-8 to T1-12):** one base for all file gates (`--base`, else the rev recorded by `file_gates.py begin`, else `main`); one command, `scripts/unity/file_gates.py`, runs the file gates and `finish` composes the PASS line (it refuses if files changed after `run`); `unity-wait-ready` has a fallback that needs no resource reader. | The PASS line was the coder's claim; subagents had no resource reader; every gate except scope listed earlier tasks' files. |
| D29 | 2026-10-13 | **Git attributes (human decision, 2026-10-13):** `.gitattributes` forces LF on Unity YAML and text sources (stops Unity's line-ending-only changes in `ProjectSettings/`), merges Unity YAML with UnityYAMLMerge, and puts new binaries (textures, models, audio, `.dll`, archives) in Git LFS. Binaries already committed (one analyzer DLL, one tutorial PNG) stay plain blobs, marked `-filter`; migrating them would rewrite pushed history. The merge driver is per-machine git config, so `scripts/core/setup_git.py` registers it (with `scripts/core/unity_merge.py`, a wrapper that restores the file extension git's temp files lack) and turns on LFS hooks. Run once per clone. | Merge conflicts in scenes and prefabs need a YAML-aware merge; binaries bloat history; the driver cannot live in a committed file. Tried: two branches editing neighbouring lines of one scene object conflict in plain git and merge cleanly with the driver. |
| D30 | 2026-10-13 | **Branching (human decision, 2026-10-13):** one branch per **feature** (`feature/<name>`), **one commit per task card**; a standalone task (gate fix, spike) gets `task/<NNN>-<name>`. `file_gates.py begin` runs at the start of each card, after the previous card's commit, so the scope gate sees only that card. Agents still never push or merge (D14). | Work is serial on one Editor (D5). A branch per card means a merge, a `unity-check` and a Unity reimport per switch. Trial 001 already ran this way (22 commits on one branch); the task-base record (task 014) and `begin` already support it. |
| D31 | 2026-10-13 | **Packaging (human decision, 2026-10-13; the kit is for the human's own projects only):** the kit repo **is** a Claude Code plugin (`agentic-kit`, `.claude-plugin/plugin.json`) carrying skills, roles, style guides, scripts and later hooks; project-owned files (`CLAUDE.md`, `.gitattributes`, `justfile`, `templates/`, `docs/HANDOFF.md`, `logs/friction-log.md`) are written into a target project by an `init` script, because a plugin cannot ship `CLAUDE.md` or project templates. Skills name bundled files as `${CLAUDE_PLUGIN_ROOT}/...`, which Claude Code substitutes in skill text (it is **not** set in the Bash environment). Spike (branch `task/016-plugin-spike`): `claude plugin validate` passes; from a second project, `--plugin-dir` listed the roles and unity skills (nested `skills/roles/` and `skills/unity/` via the manifest `skills` key), `unity-check` showed absolute script paths, and `file_gates.py` ran from there against that project's repo. | One source, versioned, updated in one place; submodules and copy scripts drift or add friction. Local `--plugin-dir` loads in place, so edits apply on `/reload-plugins`. Open: full conversion of the skills, the `init` script, and how the kit repo's own sessions load itself. |
| D5 | 2026-10-10 | **Unity: no parallel sandboxes.** One open Editor is the single source of truth, driven through an MCP bridge. Agents work **one task at a time**, in sequence, on the same checkout; the next task starts only after the current one is verified. Slot pool / Accelerator / Dev Drive ideas are parked. | Parallel Unity environments are a lot of work and may perform poorly. Serial work on one live editor is simpler and keeps one truth. |

## 4. Architecture (draft)

```
<kit repo>
├── AGENTS.md / CLAUDE.md        rules for agents working ON the kit
├── docs/
│   ├── IMPLEMENTATION_PLAN.md   this file
│   ├── HANDOFF.md               current state, next step (updated every session)
│   ├── features/                one folder per feature: feature.md (brief), implementation-plan.md
│   ├── tasks/                   task cards (NNN-name.md: goal, scope block, steps, acceptance)
│   ├── research/                dated research notes
│   └── decisions/               longer write-ups when a decision needs one
├── skills/
│   ├── core/                    process: plan, handoff, verify-gate, review, friction-to-structure
│   ├── roles/                   one short file per agent role (§4.6)
│   ├── style/                   one-page style guides: csharp-architecture, shader
│   ├── unity/                   engine track
│   └── native/                  C++/C#/Vulkan track
├── scripts/                     Python (uv), each a CLI with short output + exit code
│   ├── core/  unity/  native/
├── templates/                   feature.md, implementation-plan.md, task card, AGENTS.md, handoff for TARGET projects
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

### 4.4 Graphics feature perf harness (D7, D21-D23)
Enforced in three layers, weakest to strongest:
1. **Rule** (AGENTS.md, one line): "A graphics feature is done only when its perf harness runs and is within budget."
2. **Skill** `graphics-feature`: *agree the sweep with the human -> declare budget -> instrument -> generate harness from template -> record baseline -> run -> analyze -> compare*.
3. **Gate** `perf_check.py` (part of `check`): fails if a feature folder has no `perf/feature.json`, no result, or the result is over budget / regressed vs baseline.

**The harness is designed per feature, with the human.** What follows is the guideline and the defaults, not a fixed recipe. Which parameter is swept (instances, resolution, shadow cascades, samples), the budget and the reference scene are decided in the conversation and written into `perf/feature.json`.

#### Measurement rules (defaults, overridable per feature)
- **Frames:** discard the first **100** (warmup), record the next **300**, per sweep point. Recorders start after warmup and have headroom in capacity: a `ProfilerRecorder` that reaches its capacity resets (Spike 002 and 003), and its first sample is the partial frame in which it started, so it is dropped.
- **Metrics, all in ms** (convert from ns once, when writing the result; fields named `main_ms`, `render_ms`, `gpu_ms`, `cpu_ms`, `feature_ms`): main thread, render thread, GPU frame, CPU frame, and the feature's own marker. Per metric: **median and p95** over the 300 frames (median = mean of the two middle values for an even count; p95 = nearest rank). Whole-frame GC bytes are recorded as context.
- **Where they come from (verified in the Editor, Spike 003):** `FrameTimingManager` (`CaptureFrameTimings` each frame, `GetLatestTimings(1, ...)`; `FrameTiming.cpuMainThreadFrameTime`, `cpuRenderThreadFrameTime`, `gpuFrameTime`, `cpuFrameTime`, all ms). Results arrive 4 frames late, so the runner de-duplicates by `frameStartTimestamp`, drains 8 extra frames and drops the first 4 records. The feature marker and GC come from `ProfilerRecorder`. `FrameTimingManager.IsFeatureEnabled()` was true in the Editor with no settings change. Per-pass GPU time (`ProfilingSampler.gpuElapsedTime`) exists but is not wired yet.
- **Unfreeze the frame rate:** `vSyncCount = 0`, `targetFrameRate = -1`, fixed resolution and quality level, so main-thread and GPU time are not capped (Spike 002: main thread sat at ~16.5 ms, the frame cap).
- **Deterministic scene:** fixed camera or scripted path, fixed random seed, fixed time/wind/animation, same camera at every sweep point.
- **Feature ON vs OFF** in the same run; the **N = 0 point with the feature on** gives its fixed cost.
- **Editor numbers are relative only** (D22): compare inside one run or against a baseline from the same machine.

#### Sweep and slope
- Sweep a quality parameter N over a list chosen with the human, e.g. `[1000, 3000, 6000, 10000, 50000, 100000]` instances. Always include the baseline point (N = 0 or feature off) first and last (drift check). Repeat each point (default 3 runs) in randomized order for an error bar.
- **Fit each metric separately** (least squares of the per-point median against N). Report **ms per 1000 instances** (slope x 1000), the **intercept** (fixed cost), **R^2**, and the slopes of the lower and upper halves of the sweep. A fit may start at `fit_min_n` (set in `feature.json`) because light loads sit in a different hardware state: on the test machine GPU time at 1k-6k instances was inflated and not monotonic, while from 10k up it was linear (R^2 0.99-1.00). Excluded points stay in the report. Put at least 4 sweep points in the loaded range.
- Frame time is about max(CPU, GPU): fitting only frame time hides GPU cost in a CPU-bound scene. Treat the feature's own pass/marker as the primary metric and the thread times as context.
- If R^2 is low or the half-slopes disagree, the report says "not linear in this range" and gives the points, not one number. Small N may sit below the noise floor (Spike 002: ~15% spread on a 12 ms marker); trust the slope from the large counts over the cost at the small ones.

#### Logs and files (D23)
Per run, in `Perf/<feature>/runs/<timestamp>-<label>/` (in the Unity project, next to `Assets/`):
- `run.json`: config (frames, sweep point, seed, session id), git commit and dirty flag, Unity version, machine, GPU name, resolution, quality level, Editor or player, and per-metric median/p95/min/max with units.
- `frames_timing.csv` (main, render, gpu, cpu; same row = same frame) and `frames_recorders.csv` (feature marker, GC; a separate series), so the analysis can be redone without Unity.
- One line appended to `Perf/<feature>/index.jsonl`.
Committed: `Perf/<feature>/feature.json` (sweep points, `fit_min_n`, budgets) and accepted baselines. Ignored: `runs/`, `index.jsonl`, `report.json` (`Perf/.gitignore`).
The **C# runner** (`Assets/Kit/Perf/Runtime`, `Kit.Perf`; a Play Mode test through `run_tests`; do not use `manage_editor play`, Spike 002 friction #2) writes these files. The **Python script** (`scripts/unity/perf_analyze.py`, 15 unit tests in `test_perf_analyze.py`) reads them, recomputes every median/p95 from the CSV and refuses a run whose `run.json` disagrees, rejects sessions that mix commits, machines or settings, analyzes the latest session by default, and writes `Perf/<feature>/report.json` with per-point stats, fits, drift, budget verdicts and a short summary. Exit 0 ok, 1 a budget failed, 2 bad data. Each result is baselined once accepted; later runs compare against it. **Tolerance in the Editor: 10-15%.** Two full sweeps of the toy feature on one machine gave loaded-range slopes within about 15% of each other (GPU 0.032 vs 0.027, feature marker 0.019 vs 0.022 ms per 1000); tighter needs a player build.

#### Budgets
Declared in the task card and `feature.json`: a per-1000-instances cost, a total at the real in-game count, and optional GC limits (whole-frame GC has a ~21 KB Editor floor; per-marker GC needs a different measure or a player build).

#### Open
- GPU cost per pass: `ProfilingSampler`/`ScriptableRenderPass` scope vs frame GPU time (not wired).
- Drift check: the baseline (N = 0) is an idle-GPU point and drifts 27-90% between first and last run, so the warning is noisy. Proposal: repeat a **loaded reference point** first and last, set in `feature.json`.
- Main-thread time carries no signal for a GPU-bound feature (flat about 5 ms); keep it as context only.
- Player-build numbers (later phase).

### 4.5 Unity gate ladder (proposed 2026-10-10; frozen by D20 except Shader and Perf, which the first graphics feature needs)
`unity-check` becomes a list of gates, run cheapest first, stop at the first FAIL. Gates that only read files on disk (format, metas, scope, banned APIs) may be plain Python scripts: D11 only forbids scripts that talk to the bridge.

| Tier | Gate | How | Status |
|---|---|---|---|
| Every iteration | **Format** | `.editorconfig` + `dotnet format whitespace --folder --verify-no-changes` on changed files, workspace `Assets/` (no `.sln` needed) — `scripts/unity/format_check.py` | built (Task 002) |
| | **Compile + console** | `unity-wait-ready` + console errors | built |
| Before "done" | **Analyzers** | Roslyn analyzers (incl. Microsoft.Unity.Analyzers) as Unity RoslynAnalyzer DLLs; severities in `Assets/Default.ruleset` (Unity's compile ignores `.editorconfig` severities); `UNT` errors fail the compile gate, performance warnings are listed | built (Task 003) |
| | **Code rules** | script: no `UnityEditor` in runtime asmdefs without `#if UNITY_EDITOR`, banned APIs in hot paths (`GameObject.Find`, `FindObjectOfType`, LINQ/allocations in `Update`), no leftover `Debug.Log` — `scripts/unity/code_rules.py`, new violations only | built (Task 003) |
| | **Asset integrity** | script: every file under `Assets/` has a `.meta`, no orphan `.meta`, no duplicate GUIDs, `.meta` staged with its asset (`scripts/unity/asset_check.py`); MCP: no missing scripts in changed scenes/prefabs | script built (Task 002); MCP part to build |
| | **Scope** | script on `git diff`: only files the task card's `scope` block allows; no test deleted/weakened; `ProjectSettings/` and `Packages/` changes need approval (`scripts/unity/scope_check.py`) | built (Task 002) |
| | **Tests** | EditMode (built) + PlayMode; new code has new tests | partly built |
| Graphics feature | **Shader** | shader compile errors/warnings via console only | out of scope (D27) |
| | **Perf** | harness exists, runs in Play Mode, sweep slope and totals within budget (D7, D21-D23 / §4.4) | built (Spike 003): skill `unity-perf-harness`; `perf_check.py` as a gate still to do |
| | **Visual** | fixed-camera screenshot vs reference image with tolerance | later |
| Before merge | **Player build** | development build compiles (catches Editor-only code in runtime) + full test suite | later |

Pipeline per task: task card (goal, scope, budget, acceptance) → **implementer** works and loops on the gate until PASS (give up after N tries → report BLOCKED with evidence) → **reviewer** agent in a fresh context checks the diff against the task card (the gate proves it works, the reviewer checks it is what was asked) → report to human with the PASS line, evidence and review notes.

### 4.6 Feature pipeline (D15–D20)
The gate ladder (§4.5) is the **coding** stage only. It proves code follows rules, not that the right thing was built. The stages before and after it:

```
You ⇄ Architect ──► feature.md ──(you approve)
                         │
                     Director ──► implementation-plan.md + task cards
                         │        (each card names its coder: C# or shader)
                  format-check script (no tokens)
                         │
                  Plan reviewers (2–3 lenses) ──► findings, veto on critical
                         │
                     YOU APPROVE THE PLAN
                         │
        ┌── per task card ───────────────────────────┐
        │ Coder (C# or shader) → gate → PASS         │
        └─────────────────────────────────────────────┘
                         │
                  Code reviewer (once per feature; per task only if risky)
                         │
                  Report to you; repeated mistakes → friction log → script/rule
```

**Roles.** Each is a short file in `skills/roles/`, loaded with its input file only.
| Role | Job | Loads | Output |
|---|---|---|---|
| Architect | Talks with the human, thinks in systems not code | process rules | `feature.md`, approved by the human |
| Director | Brief → plan and task cards; applies the Ponytail ladder to scope ("does it need to exist?") | `style/csharp-architecture.md` | `implementation-plan.md`, task cards |
| Plan reviewers (2–3) | Find design mistakes and bad habits before code exists. Start lenses: architecture and style conformance; performance and GC; unnecessary scope. Add a shader lens only if the plan has shader tasks | plan + style guides | findings; any one may veto a critical error with evidence |
| C# coder | One task card | `style/csharp-architecture.md` + Ponytail ladder | code that passes the gate |
| Shader coder | One shader task card | `style/shader.md` + lighter Ponytail | shader code; console only (D27) |
| Code reviewer | Diff vs plan and style, fresh context | plan + style guides | verdict |

Architect and Director need not be separate agents (Director may be the Architect's session in another mode); reviewers and coders are separate because a fresh context is the point.

**Tiers (D16).** Small: coder + gate. Medium: short brief, plan, 1–2 reviewers, tasks, code reviewer once. Large: full pipeline, more reviewers. The Architect proposes the tier in the first exchange; the human confirms.

**Formats.** `feature.md`, `implementation-plan.md` and task cards use fixed templates in `templates/`. A script (`scripts/core/docs_check.py`, built 2026-10-11, reuses `scope_check.parse_card`) checks structure at no token cost: required sections and table columns, allowed values, unfilled placeholders, task IDs and dependencies, styles listed match the tasks, hot-path tasks have a budget and harness, review verdicts and approval date, and each card matches its plan row. Templates are checked with `--allow-placeholders`. Old-format cards (002, 003) fail it by design.

**Style guides.** One page each, written by the human's preferences, not generic advice. First: `csharp-architecture.md` (Vulkan-style: `CreateInfo` structs in, plain data structs passed around, no long parameter lists, explicit ownership). Second: `shader.md`. Where a style rule is mechanical it becomes a code-rules check (KIT005+), otherwise the reviewer checks it.

**Behavior rule (Ponytail).** Ladder: needs to exist → codebase has it → stdlib → native platform feature → installed dependency → one line → minimum code (plus one small test if the logic is risky). It never cuts validation, error handling or security. Priority: plan and style guide decide structure, the ladder decides how much code goes inside it.

**Mistake log.** Reviewers append findings to `logs/friction-log.md`. A finding that appears twice becomes a template line, a code-rules check or a hook; otherwise the log is not doing its job.

**Files (drafted 2026-10-11).** Roles: `skills/roles/*/SKILL.md`. Styles: `skills/style/` (`csharp-architecture`, `csharp-performance`, `shader`, `minimal-code`; v1, confirmed 2026-10-11: 3 parameters max, result enums for expected failures, MonoBehaviour as thin adapter, shaders for desktop with hand-written HLSL). Templates: `templates/`. Log: `logs/friction-log.md`. Not yet built: KIT005. Not yet run end to end.

**Measure before adding.** Run one real medium feature through the minimal pipeline (templates, format script, one plan reviewer, coders, gate) and record tokens and time per stage. Add reviewers and roles only where plan review is seen catching real problems.

**Result of Trial 001 (grass, 2026-10-12, D25).** Ran with 2 plan reviewers x 2 rounds, 8 coders, a perf runner and one code reviewer, about 1.5M subagent tokens (`docs/trials/001-rendering-feature.md`). What paid for itself: plan review (caught the seeded per-frame allocation and real design errors: counter reset, cull sphere, ownership), the code reviewer (leaks, shared test state, a misstated perf number), the readback test and the perf harness. What did not: the console-only shader check (black blades reached the screenshots; accepted, D27), hand-assembled PASS lines, `unity-wait-ready` for subagents. Proposed trims, not yet applied: skip separate Architect/Director agents on a medium feature, merge tiny tasks into one coder, repeat plan review only when scope changes. Friction rows T1-1 to T1-18 in `logs/friction-log.md`; the repeated ones are fixed (D28: wait-ready fallback, one base, one gate runner); T1-1 to T1-7 and T1-13 to T1-18 are open.

### 4.3 Shared core
Single gate command per project (`check`), progress/handoff protocol, task cards, friction log,
review pack (repo zip for a bigger model), approval list.

## 5. Phases
| Phase | Outcome | Exit criterion |
|---|---|---|
| 0 Foundation ✅ (mostly) | Repo layout, AGENTS.md, skill standard + linter, handoff protocol | A fresh agent can pick up work from HANDOFF.md alone |
| 1 Verification ⏳ (current) | Unity: MCP bridge installed, editor lock, compile-wait + console parser, test-run via bridge. Native: build+test+validation gate | Each track has one command returning pass/fail with a short summary |
| 1b Pipeline | Templates, docs-check script, style guides (C#, shader), role files, one plan reviewer; one medium feature run end to end with token and time per stage recorded | A medium feature goes brief → approved plan → coded → reviewed with the human only at the two approvals |
| 2 Skills | Common jobs: fix compile error, write+run test, profile a frame, shader change, asset-safe refactor | Each skill passes its own validation on a sample project |
| 3 Coordination | Unity: planner → implementer → reviewer in sequence on one task. Native: parallel worker agents in worktrees | Unity: a task passes review without human relaying. Native: two tasks run in parallel and merge cleanly |
| 4 Routines | Triggered runs (CI failure, bug report) with approval stops | Unattended run ends in a reviewed draft PR |

## 6. Open questions
- [x] First track → Unity (D8).
- [x] Harness → Claude Code (D9). Codex support: later, maybe.
- [x] Unity version / pipeline for the test project → 6000.3.10f1, URP (D10).
- [x] MCP bridge → CoplayDev/unity-mcp, stdio (D9). Pin to a release tag instead of `#main`.
- [x] Git LFS + Unity YAML merge (`.gitattributes`) for binary assets and scenes? → D29.
- [ ] Rename folders without spaces/typos (`Test Environments`) before scripts depend on the paths?
- [x] Unity branching: one branch per task, or work on a single feature branch with a commit per task? → feature branch, commit per card (D30).
- [x] While an agent runs, does the human keep using the Editor? → No, human steps away (D6).
- [ ] Reference machine + resolution for perf budgets; render pipeline (URP/HDRP/custom SRP).
- [ ] Test project: brand-new small Unity project, or a copy of a real one?
- [x] Distribution of the kit into target projects: Claude Code plugin, git submodule, or copy script? → plugin plus `init` script (D31); conversion pending.
- [ ] Sample projects for testing the kit (small Unity project, small Vulkan renderer).
- [x] Which medium feature is the first end-to-end pipeline run → grass (URP renderer feature with GPU culling), Trial 001, D25.
- [ ] Is the Ponytail ladder really cheaper on our tasks? Compare tokens with and without on one task before keeping it everywhere.
