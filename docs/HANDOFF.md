# HANDOFF

Read this first, then `docs/IMPLEMENTATION_PLAN.md`. Update it at the end of every session
(newest entry on top, keep the "Current state" block current).

## Current state
- Phase: **1 — Verification (Unity)**. `main` (local) holds two lines of work merged on 2026-10-12 after they were developed on two machines: (a) Spike 001, Tasks 002 and 003, gate skills, folder rename to `Test Environments`, pipeline redesign (roles, style guides, templates, `docs_check.py`); (b) Spikes 002 and 003, the perf harness, `just check`, Editor-made settings. Not pushed.
- The loop edit → refresh → wait → console → tests works through UnityMCP with no human relaying. `refresh_unity` does not wait for compile; the `unity-wait-ready` skill handles it.
- Gate ladder (plan §4.5): built = format, asset integrity (disk + git), scope, code rules (KIT001-004), analyzers, compile + console, EditMode tests. `unity-check` step 0 runs the four file gates (`scripts/unity/*.py`) before compiling. Frozen (D20).
- Perf harness (plan §4.4, D21-D24): skill `skills/unity/unity-perf-harness`, `scripts/unity/perf_analyze.py` (+15 tests), perf library `Assets/Kit/Perf/` (`Kit.Perf`, toy feature, sweep tests) as the perf canary. `just check` runs the Python tests; Unity stays with `unity-check`.
- Feature pipeline (plan §4.6, D15-D20): role skills, style guides v1, templates, `scripts/core/docs_check.py`. **Run end to end once: Trial 001 (grass), branch `trial/001-grass`, not merged, not pushed** (see the top log entry and `docs/trials/001-rendering-feature.md`).
- Task cards live in `docs/tasks/`; each has a machine-readable `scope` block.
- **Trial 001 done (human keeps the pipeline as is, D25); open follow-ups below:** grass as a URP renderer feature with GPU frustum culling (compute shader + indirect draw), 22 commits on `trial/001-grass`. Feature in `Assets/Kit/Grass/`, brief/plan/cards/perf result in `docs/features/grass/` and `docs/tasks/004-011`.
- Open (plan §6): packaging of the kit (plugin vs `.claude/skills`), LFS/.gitattributes.

## Next step
1. ~~Check the merge~~ done 2026-10-12 (see the top log entry). `main` is already on `origin` (pushed by the human with the merge commit).
2. **Trial 001 follow-ups** (human decides): merge `trial/001-grass` or not; buffers on a disabled feature (brief says released, code releases only on removal); away-pose perf run to show the culling gain (and a visible-count readback in the perf test); SSAO still renders after Unity reserialized `PC_Renderer.asset`; baseline accepted 2026-10-12 (`Perf/grass/baseline.json`, session 20261012T174704; no script compares against it yet); apply the friction proposals T1-1 to T1-18 (`logs/friction-log.md`), first the repeated ones: unity-wait-ready for subagents (T1-9, T1-11), one scope base for all gates (T1-8, T1-12), single gate runner for the PASS line (T1-10).
3. Housekeeping: friction #3 of Spike 001 (what rewrote `SpikeMathTests.cs`); what set `EditorSettings.m_EnterPlayModeOptions` to 1 (committed as found).
4. Task 003 follow-ups: fail the gate on `UNT` performance warnings in changed files only; the new-violations check counts per file and rule; `unity-check` does not verify the analyzer DLL `RoslynAnalyzer` label. KIT005 (max 3 parameters) when built.
5. Spike 003 proposals: loaded reference point for the drift check; `perf_check.py` as a gate over `report.json` and into `unity-check`; per-pass GPU time; baselines (`Perf/<feature>/baseline.json`).
6. Later: player-build numbers, visual gate (screenshot diff), shader gate.

## Session log
Older entries (2026-10-10 to 2026-10-12, Spikes 001-003, Tasks 002-003, rename, pipeline): `docs/archive/HANDOFF-log-2026-10.md`.

### 2026-10-12 (Trial 001: grass, full pipeline) — branch `trial/001-grass`
- Ran Architect, Director (two plan revisions), 2 plan reviewers x2 rounds, 6 coders + 2 fix coders, perf harness runner and code reviewer, each as a fresh subagent. Ledger with tokens and times: `docs/trials/001-rendering-feature.md`. Subagent tokens about 1.28M in total (main session not countable).
- Result: feature builds and renders; culling counts proven by GPU readback (10000 / 0 / 5033 of 10000). Perf: gpu 0.791 ms at 100k blades (budget 3.0), about 0.004 ms per 1000 (budget 0.05), feature adds about 0.43 ms at 100k vs OFF; **no culling gain visible in GPU time** (`docs/features/grass/perf-result.md`).
- Seeded flaw (LINQ and a list per frame in the pass): found by both plan reviewers as critical.
- Escapes: black blades from back-face lighting (found at T5 screenshots, fixed in card 010); code review found 6 majors the plan review missed (leaks on partial failure, shared test fixture, buffers not released on disable, perf test cannot show gain, perf headline understated).
- Final gates on the branch: `just check` 227 passed; unity-check `PASS 18/18 EditMode + 6/6 PlayMode readback + Smoke_OnePoint, format 16 files, assets ok (85 assets, 85 .meta), scope: no card, code-rules ok, 0 errors, 0 warnings`. The full `Sweep_Grass` was not re-run after the last fix commit.
- Human decisions during the trial: tier medium, no tint, budget 0.05 ms per 1000 and 3 ms at 100k, patch 50 x 50 m, scene component cut, GPU culling with shaders allowed, sweep run confirmed.
- Later the same day, at the human's request: sweep raised to 20k doubling to 640k then 1M, from a ground-level camera (card 012, commit 8916ef3). Result: linear 0.0022 ms per 1000 blades placed, 2.686 ms at 1M (500,099 visible, culler keeps ~50%), vs 4.357 ms with the whole patch in view: culling gain now visible (`perf-result.md`). No total budget for 1M has been set (human to give one). Not run again after this: the full unity-check EditMode gate (the final gate above predates card 012; PlayMode 8/8 passed in the coder's run).
- Review with the human after the trial: the human keeps the kit as is (D25). Plan updated (decisions D25 and D26, Trial 001 result under §4.6, open questions). Baseline accepted (`Perf/grass/baseline.json`). Open: control run with a plain prompt, shader screenshot check, friction fixes.
- Three `ProjectSettings/*.asset` files stay modified (line endings only, made by Unity); not committed.

### 2026-10-12 (unity-check on merged main) — PASS
- `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok (55 assets, 55 .meta), scope: no card, code-rules ok (0 new violations), analyzers on, 0 errors, 0 warnings`, on `main` at `c2718c1`. Compile 0.5 s, reload 5.4 s.
- Extra, not part of the gate: PlayMode 3/3 in 36.6 s (perf canary, includes `SpikeWorkloadPerfTests.Marker_OnVsOff_IsReadableByName`). `just check`: 15 tests OK; pytest over `scripts/`: 227 passed.
- Not run: the full `Kit.Perf` sweep (needs sweep points and budget agreed first).
- `just check` now runs pytest over `scripts/` (227 passed, about 70 s), so it covers the pipeline and gate suites too. `just` 1.58.0 installed via winget on this PC; justfile sets `windows-shell` to PowerShell because there is no `sh`.
- HANDOFF trimmed: older log entries moved to `docs/archive/HANDOFF-log-2026-10.md`.

### 2026-10-12 (merge) — reconciled two machines
- Alexandros developed on two machines without pulling: `origin/main` (Spikes 002/003, perf harness, 7 commits, still under the old path `Test Enviroments`) and local `main` (Tasks 002/003, rename to `Test Environments`, pipeline redesign, 20 commits). Merged `origin/main` into local `main`; harness files moved to `Test Environments/`.
- Decision numbering collided (both used D14-D17). Kept the pipeline numbers (D14-D20, dated 2026-10-11) and renumbered the perf-harness decisions to **D21-D24**; references updated in the plan, spike 003, `perf_analyze.py`, the perf skill and `PerfTypes.cs`. Entries below that say D14-D17 for the harness mean D21-D24.
- Stale `Test Enviroments` path in harness-side docs (spike 002/003, trial 001, old log entries) is historical; fixed where it was a live reference.

### 2026-10-12 (end) — spike branches merged into main, cleaned up
- Then: spike branches `spike/002-...` and `spike/003-...` deleted (`git branch -d`, merged). The Editor-made settings were committed (`781ed5d`): `Mobile_RPAsset.asset` (URP upgrade 12 to 13), `EditorSettings.asset` (`m_EnterPlayModeOptions` 0 to 1, origin unknown), new `SceneTemplateSettings.json`. `ProjectSettings.asset`, `ShaderGraphSettings.asset`, `EditorBuildSettings.asset` had line-ending-only changes and add nothing. Working tree clean; `main` is 6 commits ahead of `origin/main`, not pushed.
- `main` fast-forwarded from `70a0071` to `26d3ca3` (history was linear: 002 on top of main, 003 on top of 002), so Spikes 002 and 003 are in `main`: Spike 002 harness, plan §4.4 + D14-D16, `Kit.Perf`, `perf_analyze.py`, skill `unity-perf-harness`, `justfile`, Trial 001 protocol. Done as a local ref update (`git fetch . spike/003-sweep-harness:main`) so the Editor's working files were not swapped. Nothing pushed: `main` is 4 commits ahead of `origin/main`.
- `just check` (new): runs the 15 Python tests, exit 0; Unity is still gated by `unity-check` through UnityMCP.
- Next: Trial 001 on a branch `trial/001-<feature>` from `main`.
