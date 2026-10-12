# Trial 001 — build a rendering feature with the kit

Purpose: find out where the kit helps and where it fails when an agent builds a **new rendering feature** end to end. The agent follows the kit; the human watches and records. The goal is the friction list, not the feature.

## Setup
- Branch from `spike/003-sweep-harness` (or `main` once merged): `trial/001-<feature-name>`.
- Unity Editor open on `Test Environments/Unity Agentic Kit test/`, UnityMCP connected from Claude Code started at the repo root. The human does not touch the Editor during a task (D6).
- One agent, one task at a time (D5).

## Task card (fill in with the agent before it starts)
- **Feature:** what it renders and why.
- **Sweep:** the parameter and its points (e.g. blade count 1k, 3k, 6k, 10k, 50k, 100k; at least 4 in the loaded range).
- **Budget:** ms per 1000 and a total at the real in-game count, for which metric. The agent asks; it does not invent them.
- **Reference scene:** camera, resolution, seed, anything animated (wind, time) fixed.
- **Acceptance:** compiles with no errors or warnings, tests pass, harness within budget, visual check (screenshot) of the feature.

## What the agent must follow
`CLAUDE.md` (read first), then `docs/HANDOFF.md`. Gates: `skills/unity/unity-wait-ready`, `skills/unity/unity-check`. Perf: `skills/unity/unity-perf-harness`. Scene and asset edits only through UnityMCP (`unity-scene-safety`).

## What the human records (copy into a "Trial log" section here)
| When | What happened | Kit part involved | Human had to step in? | Fix (script, rule, skill text) |
|---|---|---|---|---|
- Every point where the agent was blocked, guessed an API, ignored a rule, or needed a human decision.
- Every number it reported: was it from a run, and did the evidence (PASS line, `perf_analyze` output) match?
- Time from task card to PASS line, and the number of harness runs.

## Success
- The agent reaches a PASS line from `unity-check` and a `perf_analyze` report with exit 0 (or a reported budget failure with evidence) **without the human relaying output**.
- No rule in `CLAUDE.md` was broken; no scene/prefab/asset text edit; no invented API names.
- Every friction item has a proposed structural fix (script, lint, test or skill step), following "encode repeated mistakes in structure".

## After the trial
Update `docs/HANDOFF.md`, add the friction to `docs/spikes` or a new trial log, and turn the repeats into changes to the skills or scripts.

## Trial 001 — grass (branch `trial/001-grass`)
Feature: GPU-instanced grass as a URP renderer feature. Brief `docs/features/grass/feature.md`, plan `docs/features/grass/implementation-plan.md`, cards `docs/tasks/004` to `007`. Friction: `logs/friction-log.md` (T1-n rows).
Tokens: main-session stages show `n/a`: the session's token counter resets every turn, so only subagent usage (reported by the Agent tool) is exact.

### Seeded flaw
Planted 2026-10-12 in a copy of the plan (scratchpad `plan-under-review.md`, reviewers never saw the real file): the `GrassPass` row of the Data table says that each frame the pass filters batches with `batches.Where(b => b.count > 0).ToList()`. That is LINQ plus a list allocation every frame, a violation of `csharp-performance` (no LINQ, no per-frame allocation) and of the brief (no per-frame allocation). Expected catcher: the performance and GC lens; the architecture lens may also notice. Result: FOUND by both reviewers, each as a critical finding and a veto (performance lens finding 1, architecture lens finding 1), both quoting the `Where(...).ToList()` text and its contradiction with the Approach line. The real plan never contained it, so nothing was removed from it.

### Ledger
| # | Stage / role | Agent / session | Files loaded | Output file | Tokens | Wall time | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Architect | main session (Claude Sonnet 5.5) | `skills/roles/architect/SKILL.md`, `templates/feature.md`, plan §4.6, `docs/trials/001-rendering-feature.md` | `docs/features/grass/feature.md` | n/a | 19:30 to 19:45 incl. human answers | `PASS docs: 1 files`; approved 2026-10-12 |
| 2 | Director | main session | `skills/roles/director/SKILL.md`, `templates/implementation-plan.md`, `templates/task-card.md`, `skills/style/csharp-architecture.md`, `minimal-code.md`, `csharp-performance.md`, plan §4.4, perf skill, toy feature and sweep test | `docs/features/grass/implementation-plan.md`, `docs/tasks/004` to `007` | n/a | 19:45 to 19:48 (3 docs_check fix rounds) | `PASS docs: 5 files`; friction T1-1 to T1-3 |
| 3 | Plan reviewer, lens architecture-style | subagent a5cda75d0f6ff7e7 (general-purpose, fresh) | role file, `csharp-architecture.md`, brief, plan copy with the seeded flaw | review in plan `## Review` table | 63,248 | 33 s | report opened with the role line; veto: seeded flaw + 5 major, 2 minor |
| 4 | Plan reviewer, lens performance | subagent ad6afd0b1cfcf5c6a (general-purpose, fresh) | role file, `csharp-performance.md`, brief, plan copy with the seeded flaw | review in plan `## Review` table | 60,648 | 18 s | report opened with the role line; veto: seeded flaw + 4 major, 3 minor |
| 4b | Director fixes after review | main session | both reports | plan and cards 004, 005, 007 updated | n/a | 19:50 to 19:55 | `PASS docs: 5 files` |
| 5 | Architect (amend) + Director (rev 2) | main session | feature.md, `skills/style/shader.md`, `skills/roles/shader-coder/SKILL.md`, previous plan | feature.md amended (draft), plan rev 2, cards 004-009 | n/a | 19:53 to 19:56 | `PASS docs: 8 files`. Human change request: GPU frustum culling, shaders allowed. Seeded flaw not repeated on rev 2. |
| 6 | Plan reviewer r2, architecture-style (+ shader.md) | subagent ab7a3c81ff5da14f0 (fresh) | role file, `csharp-architecture.md`, `shader.md`, brief, plan rev 2 | plan `## Review` | 68,156 | 37 s | role line present; verdict changes: 0 critical, 3 major, 6 minor |
| 7 | Plan reviewer r2, performance (+ shader.md) | subagent ae129ef33a3716bd1 (fresh) | role file, `csharp-performance.md`, `shader.md`, brief, plan rev 2 | plan `## Review` | 68,960 | 46 s | role line present; verdict changes: 0 critical, 3 major, 6 minor |
| 7b | Director fixes after r2 | main session | both reports | plan rev 2 and cards 005 to 009 updated | n/a | 19:57 | `PASS docs: 8 files` |
| 8 | Coder T1 (csharp, normal) | subagent ab056403acfd87290 (fresh) | CLAUDE.md, csharp-coder role, card 004, `csharp-architecture.md`, `minimal-code.md`, unity-wait-ready, unity-check, two asmdefs | commit df9b352: `Assets/Kit/Grass/Runtime/*`, `Tests/EditMode/*` | 80,188 | 115 s | `PASS 8/8 EditMode (Kit.Grass.Tests.EditMode), format 3 files, assets ok, scope ok (--base HEAD), code-rules ok, 0 errors, 0 warnings`. Assembled by the coder, not one unity-check run; lead re-ran the 4 file gates: format, assets, code-rules PASS, scope PASS with `--base c0b4cea` |
| 9 | Coder T2 (shader, hot-path) | subagent a2883528f88c4fb3a (fresh) | CLAUDE.md, shader-coder role, card 005, `shader.md`, `minimal-code.md`, unity-wait-ready, unity-check, plan rows | commit 176a1fc: `Assets/Kit/Grass/Shaders/GrassCull.compute` | 79,191 | 69 s | `PASS 11/11 EditMode, format 3 files, assets ok, scope ok (base HEAD), code-rules ok, 0 errors, 0 warnings`; console after compile only a bridge line. wait-ready approximated (no resource reader). Not GPU-verified until T4 readback |
| 10 | Coder T3 (shader, hot-path) | subagent affaed50a80a50e83 (fresh) | CLAUDE.md, shader-coder role, card 006, `shader.md`, `minimal-code.md`, `GrassCull.compute`, unity-wait-ready, unity-check, plan rows | commit 5c7e7ec: `Assets/Kit/Grass/Shaders/GrassInstanced.shader` | n/a (usage line not shown) | n/a | `PASS 11/11 EditMode, format 3 files, assets ok, scope ok (base HEAD), code-rules ok, 0 errors, 0 warnings`. No analyzer-load check run; wait-ready approximated; not rendered yet. Caveats: normal transform only right for uniform scale; Cull Off |
| 11 | Coder T4 (csharp, hot-path) | subagent af4414c833e1eb780 (fresh) | CLAUDE.md, csharp-coder role, card 007, 3 style guides, plan, both shaders, T1 code, asmdefs, unity-wait-ready, unity-check | commit ead6739: 11 runtime files, EditMode and PlayMode tests | 176,798 | 439 s, 100 tool calls | `PASS 15/15 EditMode + 6/6 PlayMode, format 15 files, assets ok, scope ok (base HEAD), code-rules ok, 0 errors, 0 warnings`; readback N=10000: whole 10000, away 0, half 5033 (50.3%), sequence 10000/0/5033/10000/0. Lead re-ran the 4 file gates: PASS. Not run: `just check`; no screenshot yet |
