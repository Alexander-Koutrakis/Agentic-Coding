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

### 4.4 Graphics feature perf harness (D7, proposed)
Enforced in three layers, weakest to strongest:
1. **Rule** (AGENTS.md, one line): "A graphics feature is done only when its perf harness runs and is within budget."
2. **Skill** `graphics-feature`: the steps include *declare budget → instrument → generate harness from template → record baseline → run → compare*.
3. **Gate** `perf_check.py` (part of `check`): fails if a feature folder has no `perf/feature.json`, no result, or the result is over budget / regressed vs baseline.

Per feature, the agent must provide:
- **Budget** in the task card (e.g. "≤ 0.4 ms GPU @1080p on reference machine, 0 GC alloc/frame").
- **Instrumentation:** CPU work wrapped in `ProfilerMarker` (Unity) / Tracy zone or CPU timer (native); GPU work in a named profiling scope (Unity `ProfilingSampler`) / timestamp queries around each pass (Vulkan).
- **Harness:** fixed scene, fixed camera (or scripted path), fixed resolution, warmup frames, N measured frames, **feature ON vs OFF** in the same run.
  - Unity: a performance test using `com.unity.test-framework.performance` (`[Test, Performance]`), run through the bridge; frame CPU/GPU from `FrameTimingManager` + the feature's markers.
  - Native: harness executable/mode `--bench <feature> --frames N --warmup W --out result.json`, headless.
- **Result** in one shared schema (`perf/<feature>/result.json`): feature, scene, resolution, frames, machine id, build config, metrics {cpu_ms, gpu_ms, feature_gpu_ms p50/p95, gc_alloc, draw_calls, memory}, on/off delta.
- **Baseline** committed once accepted; later runs compare against it.

Known caveats: Editor numbers are noisy and unrepresentative → use for quick checks only, compare relative (ON vs OFF, vs baseline on same machine); real numbers come from a development player build (later phase). Use medians of several runs and a tolerance (e.g. 5–10%).

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
| Graphics feature | **Shader** | shader compile errors/warnings via console/MCP | to build |
| | **Perf** | harness exists, runs in Play Mode, within budget, 0 GC alloc in hot path (D7 / §4.4) | next spike |
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
| Shader coder | One shader task card | `style/shader.md` + lighter Ponytail | shader code; shader gate (to build) |
| Code reviewer | Diff vs plan and style, fresh context | plan + style guides | verdict |

Architect and Director need not be separate agents (Director may be the Architect's session in another mode); reviewers and coders are separate because a fresh context is the point.

**Tiers (D16).** Small: coder + gate. Medium: short brief, plan, 1–2 reviewers, tasks, code reviewer once. Large: full pipeline, more reviewers. The Architect proposes the tier in the first exchange; the human confirms.

**Formats.** `feature.md`, `implementation-plan.md` and task cards use fixed templates in `templates/`. A script (`scripts/core/docs_check.py`, built 2026-10-11, reuses `scope_check.parse_card`) checks structure at no token cost: required sections and table columns, allowed values, unfilled placeholders, task IDs and dependencies, styles listed match the tasks, hot-path tasks have a budget and harness, review verdicts and approval date, and each card matches its plan row. Templates are checked with `--allow-placeholders`. Old-format cards (002, 003) fail it by design.

**Style guides.** One page each, written by the human's preferences, not generic advice. First: `csharp-architecture.md` (Vulkan-style: `CreateInfo` structs in, plain data structs passed around, no long parameter lists, explicit ownership). Second: `shader.md`. Where a style rule is mechanical it becomes a code-rules check (KIT005+), otherwise the reviewer checks it.

**Behavior rule (Ponytail).** Ladder: needs to exist → codebase has it → stdlib → native platform feature → installed dependency → one line → minimum code (plus one small test if the logic is risky). It never cuts validation, error handling or security. Priority: plan and style guide decide structure, the ladder decides how much code goes inside it.

**Mistake log.** Reviewers append findings to `logs/friction-log.md`. A finding that appears twice becomes a template line, a code-rules check or a hook; otherwise the log is not doing its job.

**Files (drafted 2026-10-11).** Roles: `skills/roles/*/SKILL.md`. Styles: `skills/style/` (`csharp-architecture`, `csharp-performance`, `shader`, `minimal-code`; the first three have `(confirm)` items for the human). Templates: `templates/`. Log: `logs/friction-log.md`. Not yet built: the shader gate, KIT005. Not yet run end to end.

**Measure before adding.** Run one real medium feature through the minimal pipeline (templates, format script, one plan reviewer, coders, gate) and record tokens and time per stage. Add reviewers and roles only where plan review is seen catching real problems.

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
- [ ] Git LFS + Unity YAML merge (`.gitattributes`) for binary assets and scenes?
- [ ] Rename folders without spaces/typos (`Test Environments`) before scripts depend on the paths?
- [ ] Unity branching: one branch per task, or work on a single feature branch with a commit per task?
- [x] While an agent runs, does the human keep using the Editor? → No, human steps away (D6).
- [ ] Reference machine + resolution for perf budgets; render pipeline (URP/HDRP/custom SRP).
- [ ] Test project: brand-new small Unity project, or a copy of a real one?
- [ ] Distribution of the kit into target projects: Claude Code plugin, git submodule, or copy script?
- [ ] Sample projects for testing the kit (small Unity project, small Vulkan renderer).
- [ ] Content of `style/csharp-architecture.md` (the human's Vulkan-style preferences) and `style/shader.md`.
- [ ] Which medium feature is the first end-to-end pipeline run (ideally a small graphics feature, so the perf harness and shader gate are exercised).
- [ ] Is the Ponytail ladder really cheaper on our tasks? Compare tokens with and without on one task before keeping it everywhere.
- [ ] Shader gate: how to read shader compile errors and warnings through the bridge.
