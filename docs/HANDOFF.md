# HANDOFF

Read this first, then `docs/IMPLEMENTATION_PLAN.md`. Update it at the end of every session
(newest entry on top, keep "Current state" and "Next step" current).

## Current state
- Phase: **1 — Verification (Unity)**. The repo is the kit only: no Unity project inside (D32). It is a Claude Code plugin (`agentic-kit`, D31) plus `scripts/core/init_project.py` for target projects; `README.md` has the install steps.
- Built and exercised on the old test project (tag `test-project-snapshot`): the loop edit → refresh → wait → console → tests through UnityMCP (`unity-wait-ready`, `unity-check`), the file gates (`scripts/unity/file_gates.py`: format, assets, scope, code rules; one recorded base per card, D28), the perf harness (`unity-perf-harness`, `perf_analyze.py`), and the feature pipeline (role skills, style guides, templates, `docs_check.py`; run end to end once, D25).
- Git: `.gitattributes` (LF, UnityYAMLMerge, LFS for new binaries) with `setup_git.py` + `unity_merge.py` (D29); one branch per feature, one commit per task card (D30).
- Script tests: `pytest scripts` (254 passed). Unity-side behaviour is checked only inside a real Unity project.
- Not pushed: the human pushes (`main` and tag `test-project-snapshot`).

## Next step
1. **Prove the kit on a real Unity project** (the human's): `init_project.py`, `setup_git.py`, then `agentic-kit:unity-check` on the clean tree. Expect rough edges: the gates assume a branch named `main`; `csharp-coder` loads but is missing from the model's skill listing; nothing was run with the plugin loaded against a live Editor yet. Fix what breaks, log repeats in `logs/friction-log.md`.
2. Open friction items: T1-1 to T1-7 and T1-13 to T1-18 in `logs/friction-log.md` (rows about grass or paths in the old test project are history).
3. Gate follow-ups: KIT005 (max 3 parameters); fail on `UNT` performance warnings in changed files only; new-violations check counts per file and rule; `unity-check` does not verify the analyzer DLL's `RoslynAnalyzer` label.
4. Perf harness follow-ups: `perf_check.py` as a gate over `report.json`; loaded reference point for the drift check; per-pass GPU time; baselines (`Perf/<feature>/baseline.json`).
5. A canary fixture: `unity-check` and the perf harness have none until a small Unity test project exists again (outside this repo; the old one is in the tag).
6. Open questions: reference machine for perf budgets; Ponytail ladder worth measured; kit for C++/Vulkan later (D8). See plan §6.
7. Later: player-build numbers, visual gate (screenshot diff).

## Session log

### 2026-10-13 (LFS/merge, branching, plugin, cleanup) — tasks 015-018
- 015 (D29, D30): `.gitattributes`, `setup_git.py`, `unity_merge.py` (git hands merge drivers extension-less temp files, which UnityYAMLMerge rejects; the wrapper restores the extension), feature-branch rule. Scratch-repo proof: two branches editing neighbouring lines of one scene object conflict in plain git and merge cleanly with the driver.
- 016 (D31): kit as a Claude Code plugin; every kit path in skills, roles and templates is `${CLAUDE_PLUGIN_ROOT}/...`; `init_project.py` + `templates/project/`. A marketplace install copies the whole repo into the plugin cache, so it is not used; load with the env var `CLAUDE_CODE_PLUGIN_DIRS` (a `settings.json` `env` entry is read too late) or `claude --plugin-dir`.
- 017 (D32): Unity test project removed from the repo, tagged `test-project-snapshot`.
- 018: cleanup for public use. Removed spike and trial write-ups, old task cards, grass feature docs, research note, the archived log, and the unrelated Grok document; added `README.md`; rewrote this file. One test that copied an old card now builds it inline. Not done: a LICENSE (the human chooses one).
