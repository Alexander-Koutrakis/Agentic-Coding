# HANDOFF

Read this first, then `docs/IMPLEMENTATION_PLAN.md`. Update it at the end of every session
(newest entry on top, keep the "Current state" block current).

## Current state
- Phase: **1 — Verification (Unity)**. `main` (local) holds two lines of work merged on 2026-10-12 after they were developed on two machines: (a) Spike 001, Tasks 002 and 003, gate skills, folder rename to `Test Environments`, pipeline redesign (roles, style guides, templates, `docs_check.py`); (b) Spikes 002 and 003, the perf harness, `just check`, Editor-made settings. Not pushed.
- The loop edit → refresh → wait → console → tests works through UnityMCP with no human relaying. `refresh_unity` does not wait for compile; the `unity-wait-ready` skill handles it.
- Gate ladder (plan §4.5): built = format, asset integrity (disk + git), scope, code rules (KIT001-004), analyzers, compile + console, EditMode tests. `unity-check` step 0 runs the four file gates (`scripts/unity/*.py`) before compiling. Frozen (D20).
- Perf harness (plan §4.4, D21-D24): skill `skills/unity/unity-perf-harness`, `scripts/unity/perf_analyze.py` (+15 tests), perf library `Assets/Kit/Perf/` (`Kit.Perf`, toy feature, sweep tests) as the perf canary. `just check` runs the Python tests; Unity stays with `unity-check`.
- Feature pipeline (plan §4.6, D15-D20): role skills, style guides v1, templates, `scripts/core/docs_check.py`. Nothing run end to end yet.
- Task cards live in `docs/tasks/`; each has a machine-readable `scope` block.
- **Ready for Trial 001** (`docs/trials/001-rendering-feature.md`): build a real rendering feature with the kit.
- Open (plan §6): packaging of the kit (plugin vs `.claude/skills`), LFS/.gitattributes.

## Next step
1. ~~Check the merge~~ done 2026-10-12 (see the top log entry). `main` is already on `origin` (pushed by the human with the merge commit).
2. **Trial 001**: run one medium feature through the pipeline (templates, one plan reviewer, coders, gate, perf harness) and record tokens and time per stage; fill the task card (feature, sweep points, budget, reference scene) with the agent first. Trim this HANDOFF log (move old entries to `docs/archive/`).
3. Housekeeping: friction #3 of Spike 001 (what rewrote `SpikeMathTests.cs`); what set `EditorSettings.m_EnterPlayModeOptions` to 1 (committed as found).
4. Task 003 follow-ups: fail the gate on `UNT` performance warnings in changed files only; the new-violations check counts per file and rule; `unity-check` does not verify the analyzer DLL `RoslynAnalyzer` label. KIT005 (max 3 parameters) when built.
5. Spike 003 proposals: loaded reference point for the drift check; `perf_check.py` as a gate over `report.json` and into `unity-check`; per-pass GPU time; baselines (`Perf/<feature>/baseline.json`).
6. Later: player-build numbers, visual gate (screenshot diff), shader gate.

## Session log
Older entries (2026-10-10 to 2026-10-12, Spikes 001-003, Tasks 002-003, rename, pipeline): `docs/archive/HANDOFF-log-2026-10.md`.

### 2026-10-12 (unity-check on merged main) — PASS
- `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok (55 assets, 55 .meta), scope: no card, code-rules ok (0 new violations), analyzers on, 0 errors, 0 warnings`, on `main` at `c2718c1`. Compile 0.5 s, reload 5.4 s.
- Extra, not part of the gate: PlayMode 3/3 in 36.6 s (perf canary, includes `SpikeWorkloadPerfTests.Marker_OnVsOff_IsReadableByName`). `just check`: 15 tests OK; pytest over `scripts/`: 227 passed.
- Not run: the full `Kit.Perf` sweep (needs sweep points and budget agreed first).
- `just check` now runs pytest over `scripts/` (227 passed, about 70 s), so it covers the pipeline and gate suites too. `just` itself is not installed on this PC; the recipe's command was run directly.
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
