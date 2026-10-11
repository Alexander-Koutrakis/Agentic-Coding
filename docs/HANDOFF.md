# HANDOFF

Read this first, then `docs/IMPLEMENTATION_PLAN.md`. Update it at the end of every session
(newest entry on top, keep the "Current state" block current).

## Current state
- Phase: **1 — Verification (Unity)**. Branch `main` contains Spike 001, the gate skills `unity-wait-ready` + `unity-check` (`skills/unity/`), CLAUDE.md rules and the canary fixture `Assets/Kit/Spike/` (3 EditMode tests).
- The loop edit → refresh → wait → console → tests works through UnityMCP with no human relaying. `refresh_unity` does not wait for compile; the `unity-wait-ready` skill handles it.
- Gate ladder (plan §4.5): built = format, asset integrity (disk + git), scope (Task 002, on branch `task/002-cheap-gates`), compile + console, EditMode tests. `unity-check` step 0 runs the three file gates (`scripts/unity/*.py`) before compiling.
- Task cards live in `docs/tasks/`; each has a machine-readable `scope` block. Branches: `task/002-cheap-gates` (done, reviewed, awaiting merge) → `task/003-code-rules-analyzers` (card only, stacked on 002).
- Open (plan §6): packaging of the kit (plugin vs `.claude/skills`), LFS/.gitattributes, folder renames.

## Next step
1. Alexandros: review and merge `task/002-cheap-gates` into `main` (it is stacked on `docs/handoff-2026-10-11`, so one merge brings both). Then run `unity-check` on `main` (expect `scope: no card`).
   - Fast-forward or merge commit: `task/003-code-rules-analyzers` already sits on top of those commits; nothing to do.
   - **Squash merge:** first move the card commit onto the new `main`: `git rebase --onto main task/002-cheap-gates task/003-code-rules-analyzers`.
2. **Task 003 — code rules + Roslyn analyzers**, handed to a **fresh agent session** (decided 2026-10-11: tests that HANDOFF + card are enough, keeps the context clean, one task per review). Card: `docs/tasks/003-code-rules-analyzers.md` on branch `task/003-code-rules-analyzers`. Alexandros reviews the card first. Part A needs no approvals; Part B needs a yes for the NuGet download of Microsoft.Unity.Analyzers 1.28.0, so stay reachable. Start the session at the repo root with:
   > Switch to branch task/003-code-rules-analyzers. Read docs/HANDOFF.md and docs/IMPLEMENTATION_PLAN.md, then implement docs/tasks/003-code-rules-analyzers.md. Do Part A first. Ask me before the NuGet download in step B1.
   - The implementing agent: check `git log main..HEAD` shows only the card commit (plus Task 002 if it is not merged yet), and that `uv run --no-project --with pytest pytest scripts/unity/tests -q` passes (61) before changing anything.
3. Housekeeping: pin unity-mcp to a release tag; investigate what rewrote `SpikeMathTests.cs` (friction #3 — IDE format-on-save?).
4. Spike 002: perf harness in Play Mode with a custom `ProfilerMarker` (proposal 5).
5. Build `graphics-feature` skill + perf harness template + `perf_check.py`; prove it on one toy feature with ON/OFF numbers.

## Session log
### 2026-10-11 — Task 003 card (Claude Code)
- Wrote `docs/tasks/003-code-rules-analyzers.md`: Part A = `code_rules.py` (KIT001 `UnityEditor` in runtime code, KIT002 scene searches/`SendMessage` in per-frame methods, KIT003 LINQ there, KIT004 `Debug.Log`; new violations only; `// kit-allow` with a reason); Part B = Microsoft.Unity.Analyzers in Unity's compile, severities in `.editorconfig`.
- Research (Unity 6.3 manual, NuGet, the analyzers' `doc/index.md`):
  - Unity loads an analyzer only from a DLL in `Assets/` with the asset label `RoslynAnalyzer` and all platforms off (both `.meta` data → Editor only).
  - The two manual pages disagree on scope: "analyzers in the root of Assets apply to all predefined assemblies" vs "Unity considers all files in the project to be in scope". Our code is in custom asmdefs, so the card starts with a probe (B1).
  - Severity: `Default.ruleset` in `Assets/` for all assemblies, or `.editorconfig` `dotnet_diagnostic.<id>.severity` (documented with an example).
  - UNT rules are mostly IDE suggestions by default, so without severities they would not show as warnings or errors.
  - The generated `.csproj` already references VS 2022's bundled `Microsoft.Unity.Analyzers.dll`; that is IDE-only, Unity's compile does not use it.
  - Microsoft.Unity.Analyzers 1.28.0 (nuget.org, 164.76 KB, released ~12 days ago), 46 UNT rules + 23 suppressors.
- Not done: the implementation. Decided to hand Task 003 to a fresh session after Task 002 is merged (Next step 1–2 has the steps and the start prompt). Rebase not run: `main` does not have Task 002 yet, and after a fast-forward or merge-commit merge it is not needed.

### 2026-10-11 — Task 002 implemented (Claude Code)
- Built `scripts/unity/` (`gate_common.py`, `changed_files.py`, `format_check.py`, `asset_check.py`, `scope_check.py`) + 42 pytest tests; `.editorconfig` in the test project; `unity-check` step 0.
- Acceptance evidence:
  1. `uv run --no-project --with pytest pytest scripts/unity/tests -q` → `42 passed in 22.06s` (format tests ran `dotnet format`, none skipped).
  2. On the real project: `PASS format: 0 files` · `PASS assets: 29 assets, 29 .meta, 0 changed in git` · `PASS scope: 15 changed files in scope, tests may-not-change` (all exit 0).
  3. Full `unity-check`: `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope ok, 0 errors, 0 warnings, ~11s` (wait-ready: compile 1.15 s, reload 3.1 s; job 5.4 s, tests 0.67 s).
  4. Negative run: trailing whitespace in `SpikeMath.cs` → `FAIL format: Test Enviroments/Unity Agentic Kit test/Assets/Kit/Spike/Runtime/SpikeMath.cs(9,36): error WHITESPACE: Fix whitespace formatting. Replace 12 characters with '\r\n\s\s\s\s\s\s\s\s'.` exit 1, no `refresh_unity` call. Restored from a backup (`cmp` identical), re-ran: PASS.
  5. File gates: 1.3 s with no changed `.cs`, 2.25 s for the format gate alone with one changed file (budget 15 s).
  6. The scope gate passes on this branch's own diff (above).
  7. No changes under `Library/`, `Temp/`, `Logs/`, `UserSettings/`, `ProjectSettings/`, `Packages/`; no `.meta` in the diff.
- Findings: the bridge's console line is `<b><color=#cc3333>MCP-FOR-UNITY</color></b>: Client handler error: A task was canceled.` (as an **error**, right after a refresh): the prefix sits inside rich-text tags, so CLAUDE.md and `unity-check` now say so, and step 2 ignores these lines. `TutorialInfo/Scripts/Editor/ReadmeEditor.cs` (Unity template) has trailing whitespace on lines 13 and 26; only flagged if a task touches it. Git Bash `sed -i` turned CRLF into LF in the test file (restored from backup); prefer the Edit tool for `.cs` edits.
- Deviation from the card: the format gate prints the file path repo-relative and drops dotnet's trailing `[workspace]` suffix; the rest of the line is dotnet's text unchanged.
- **Review (fresh-context subagent): CHANGES REQUESTED, 5 bugs, all fixed with regression tests:**
  1. `--project "./X"`, an absolute path or a different letter case gave a **silent PASS** in all three gates, which also skipped the ProjectSettings/Packages protection. `resolve_project` now resolves against the file system; a path outside the repo is exit 2.
  2. Commented-out `[Test]`/`Assert` still counted; comments are now stripped (strings kept) before counting.
  3. An `.asmdef` with a UTF-8 BOM was not seen as a test assembly.
  4. Dropping `UNITY_INCLUDE_TESTS` from an `.asmdef` in the same change unlocked its tests; test-ness is now checked on disk **and** at the merge-base.
  5. A folder removed in git while its folder `.meta` stays staged passed.
  - Nits fixed: details capped at 10 lines including the "... N more" line; `#` inside a glob is not a comment; `allow: x` on one line is rejected; a card that is not UTF-8 gives exit 2; `void Test()` no longer counts as an attribute; SKILL step 0 now states the no-card rule, what to return on `ERROR` (exit 2), and how the summaries map into the PASS line.
  - **Re-review: APPROVE** (all 5 verified fixed with the reviewer's own probes, no false positives found for the folder `.meta` rule). Its two small nits are also fixed: fully qualified `[UnityEngine.TestTools.UnityTest]` now counts; the BOM in `scope_check.py` is now the escape `"﻿"`, not an invisible literal (the edit tool had written the raw character). 61 tests pass.
  - Not changed (by design, noted): a card glob like `Assets/Kit/**/*.cs` does not allow a new folder's `.meta` (write `Assets/Kit/**` instead); with no .NET SDK the format tests show as skipped in pytest (the gate itself still FAILs).
- After the fixes: `60 passed in 28.26s`; the reviewer's probe scripts now FAIL as they should; file gates `PASS format: 0 files` · `PASS assets: 29 assets, 29 .meta, 0 changed in git` · `PASS scope: 16 changed files in scope, tests may-not-change`; full gate `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope ok, 0 errors, 0 warnings, ~11s` (compile 0.06 s, reload 4.5 s, job 5.3 s).

### 2026-10-11 — Task 002 card (Claude Code)
- Wrote `docs/tasks/002-cheap-gates.md` on `task/002-cheap-gates` (stacked on `docs/handoff-2026-10-11`). It defines the machine-readable `scope` block that the scope gate reads; the card uses one itself.
- Found while scoping: no .NET SDK on the machine (`dotnet --info`: "No SDKs were found", runtimes 6.0.11/8.0.13 only). C# files are mixed CRLF/no-BOM (`Kit/Spike`) vs LF/BOM (`TutorialInfo`), and `core.autocrlf=true`, so the card leaves `end_of_line`/`charset` out of `.editorconfig` v1.
- Installed .NET SDK 8.0.425 with winget (at the user's request). `dotnet format whitespace --folder --verify-no-changes` on the 2 Spike files: exit 0, 9.1 s with the project root as workspace vs 1.3 s with `Assets/` (the root includes `Library/PackageCache`, 6,684 `.cs` files). The card now requires `Assets/`.
- Not done: the implementation itself.

### 2026-10-11 — unity-check on main (Claude Code)
- Committed the pending Cowork doc edits (D14, gate-ladder status) on branch `docs/handoff-2026-10-11`; merged the duplicate gate-ladder log entry. Code is identical to `main` (`70a0071`).
- Ran `unity-check` as written: `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), 0 errors, 0 warnings`. Wait-ready: compile 0.27 s, reload 4.3 s, no `stale_status`. Tests 0.67 s, job 5.4 s.
- Not done: Task 002 card not written yet.

### 2026-10-11 — merge (Cowork)
- Alexandros merged `spike/001-unity-loop` into `main` (fast-forward). Recorded D14 (merge routine: agents never push/merge; human merges, then `unity-check` on `main`).

### 2026-10-10 — gate ladder proposed (Cowork)
- Proposed the Unity gate ladder and the implementer → gate → reviewer → report pipeline (plan §4.5). Alexandros wants a language-format gate (`.editorconfig` + `dotnet format`).
- Format, asset-integrity and scope gates may be plain Python scripts (they only read files; D11 only forbids scripts that talk to the bridge).
- Note: HANDOFF.md had reverted to the pre-review version on disk (CLAUDE.md and the plan had not); re-applied.

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
