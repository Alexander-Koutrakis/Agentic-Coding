# HANDOFF

Read this first, then `docs/IMPLEMENTATION_PLAN.md`. Update it at the end of every session
(newest entry on top, keep the "Current state" block current).

## Current state
- Phase: **1 — Verification (Unity)**. `main` (local, not pushed) has Spike 001, Tasks 002 and 003 and the gate skills. Test project folder renamed to `Test Environments` (2026-10-11). Task 003 added the **code-rules gate** (`scripts/unity/code_rules.py`, KIT001-004) and **Microsoft.Unity.Analyzers 1.28.0** inside Unity's compile (`Assets/Kit/Analyzers/`, severities in `Assets/Default.ruleset`).
- The loop edit → refresh → wait → console → tests works through UnityMCP with no human relaying. `refresh_unity` does not wait for compile; the `unity-wait-ready` skill handles it.
- Gate ladder (plan §4.5): built = format, asset integrity (disk + git), scope, code rules, analyzers, compile + console, EditMode tests. `unity-check` step 0 runs the four file gates (`scripts/unity/*.py`) before compiling.
- Task cards live in `docs/tasks/`; each has a machine-readable `scope` block.
- Open (plan §6): packaging of the kit (plugin vs `.claude/skills`), LFS/.gitattributes, folder renames.
- **Pipeline redesign drafted** on `docs/pipeline-redesign` (not merged): plan §4.6 and D15-D20, role skills, style guides, templates, friction log. Nothing in it has been run yet. Gate ladder frozen (D20).

## Next step
0. Pipeline (branch `docs/pipeline-redesign`): Alexandros reviews and merges. Then: answer the `(confirm)` items in the style guides; write `scripts/core/format_check.py`; run one medium feature through the pipeline (templates, one plan reviewer, coders, gate) and record tokens and time per stage. Trim this HANDOFF log (move old entries to `docs/archive/`) so sessions read less.
1. ~~Merge `task/003-code-rules-analyzers` into `main`~~ done 2026-10-11 (fast-forward, `unity-check` on `main` PASS). Alexandros: push `main` when ready (agents never push). Things worth a look in the review: the deviations and decisions in the session log below (ruleset instead of `.editorconfig`, `||` not counted as editor-guarded, kit-allow on the line above must be comment-only, baseline/editor-only handling of moved files).
2. Housekeeping: pin unity-mcp to a release tag; investigate what rewrote `SpikeMathTests.cs` (friction #3 — IDE format-on-save?).
3. Follow-ups noticed in Task 003: fail the gate on `UNT` performance warnings in **changed files only** (needs console parsing matched against `changed_files`; see how noisy they are first); the new-violations check counts per file and rule, so fixing one `Debug.Log` and adding another in the same file passes (accepted in the card); `unity-check` does not yet verify that the analyzer DLL still has its `RoslynAnalyzer` label (CS8032 only covers a DLL that fails to load).
4. Spike 002: perf harness in Play Mode with a custom `ProfilerMarker` (proposal 5).
5. Build `graphics-feature` skill + perf harness template + `perf_check.py`; prove it on one toy feature with ON/OFF numbers.

## Session log
### 2026-10-11 — pipeline redesign (Claude Code)
- Alexandros worried about overengineering and token cost. We agreed: freeze the gate ladder (D20), add a front half to the pipeline (Architect → Director → plan review → human approval → coders → code reviewer), tier by size (D16), 2-3 reviewers with veto instead of a 5-agent vote (D17), rules in layers loaded per role (D18), Ponytail as an idea only (D19; it is a prompt that makes the coder write the minimum, its -45% token claim is its own benchmark).
- Wrote on branch `docs/pipeline-redesign`: plan edits (principles 7-8, D15-D20, §4.6, phase 1b, open questions); `skills/style/` (`csharp-architecture`, `csharp-performance`, `shader`, `minimal-code`); `templates/` (feature, plan, task card with `Coder:` and `Profile:` header fields); `skills/roles/` (6 roles); `logs/friction-log.md`; CLAUDE.md pointer section.
- Shader guide sources: Unity 6.3 manual (shader performance, SRP Batcher, keywords) and, for branching, forum threads and a Vulkan divergence guide (weaker). Three Unity doc URLs returned 404 and were not read in full.
- Not done: `format_check.py`, shader gate, KIT005, an end-to-end run. `(confirm)` items in the style guides: 3-parameter limit, result enums vs exceptions, MonoBehaviour role.
- No Unity work this session, so `unity-check` was not run (docs and markdown only).
### 2026-10-11 — rename merged into main (Claude Code)
- At Alexandros's explicit request in chat, the agent fast-forwarded `main` to `task/rename-test-environments` (`9f7dfd6..2721dd3`, local only, not pushed). Exception to D14 asked for by the human; D14 unchanged.
- `unity-check` on `main` (no card): `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope: no card, code-rules ok, analyzers on (0 warnings), 0 errors, 0 warnings`. File gates `PASS format: 0 files` · `PASS assets: 32 assets, 32 .meta, 0 changed in git` · `PASS code-rules: 0 files, 0 new violations, 0 suppressed`; compile 4.4 s, reload 5.6 s, no CS8032, tests 0.67 s.
- Project path is now `Test Environments/Unity Agentic Kit test`; Unity instance `Unity Agentic Kit test@f7afd68e`.

### 2026-10-11 — folder rename (Claude Code)
- Renamed `Test Enviroments` to `Test Environments` (Editor closed by Alexandros first) on `task/rename-test-environments`: `git mv`, 20 references in 8 files updated, `Library/` moved along with the folder. No scripts referenced the old name.
- Unity not yet reopened and `unity-check` not yet run on the new path: Alexandros reopens the project from `Test Environments/Unity Agentic Kit test`, then the agent runs `unity-check`. Expect a longer first import (Library cache keyed to the old path).
- The file gates (`format_check`, `code_rules`) FAIL on this branch only because git sees every file under the folder as changed (rename), so they pick up pre-existing Unity template files (`TutorialInfo/...`, known trailing whitespace). `asset_check` PASS 32 assets, 32 .meta. Not a regression; do not fix the template files for this.
- Open question closed: chose plain files over a plugin until a second project needs the kit. Git LFS: left to the user of the kit, not the kit's concern.
- `unity-check` run after Unity was reopened on the new path: as written `FAIL format` (ReadmeEditor.cs, template file flagged only because the rename shows every file as changed vs `main`). Extra evidence: file gates with `--base HEAD` all PASS (format 0 files, assets 32/32, code-rules 0), compile 0.07 s + reload ~3 s, analyzers load (no CS8032), console 0 errors / 0 warnings, `3/3 EditMode` in 0.67 s.
- Found: the Unity instance ID hash depends on the project path, so the rename changed `@6b88ab86` to `@f7afd68e`; UnityMCP needed `set_active_instance` and returned a mostly-null editor state until then. Added to `unity-wait-ready` step 3.
- Next: Alexandros merges the branch, then `unity-check` on `main` (no card) should PASS.

### 2026-10-11 — Task 003 merged (Claude Code)
- At Alexandros's explicit request in chat, the agent fast-forwarded `main` to `task/003-code-rules-analyzers` (`548dc8f..16250e1`, local only, not pushed). Exception to D14 asked for by the human; D14 is unchanged.
- `unity-check` on `main` (no card): `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope: no card, code-rules ok, analyzers on (0 warnings), 0 errors, 0 warnings`. File gates `PASS format: 0 files` · `PASS assets: 32 assets, 32 .meta, 0 changed in git` · `PASS code-rules: 0 files, 0 new violations, 0 suppressed` (1.5 s together); script tests `167 passed in 71.01s`; no `CS8032`; tests 0.67 s, job 5.4 s. Compile after the branch switch took ~39 s this time (files changed on disk), reload 5 s.
- This handoff update sits on `docs/handoff-task-003-merged` (one commit on top of `main`), because CLAUDE.md says to work on a branch.

### 2026-10-11 — Task 003 implemented (Claude Code)
- **Part A** (`scripts/unity/code_rules.py`, `unity_assemblies.py`; `scope_check.TestFiles` moved into `Assemblies`, its 61 tests unchanged). KIT001-004 as in the card; PASS/FAIL output, log and exit codes like Task 002; `unity-check` step 0 has a 4th command. Tests: `scripts/unity/tests/test_code_rules.py`.
- **Part B1 probe** (download approved in chat; `microsoft.unity.analyzers.1.28.0.nupkg`, 168,715 bytes = 164.76 KB, `dotnet nuget verify` exit 0: author signature Microsoft Corporation + NuGet.org repository signature; only `analyzers/dotnet/cs/Microsoft.Unity.Analyzers.dll` extracted, 316,216 bytes). Importer set through the Editor (`execute_code`): `RoslynAnalyzer` label, any platform off, Editor off; `.meta` shows both.
  - **DLL copied before the importer settings were set** produced compile errors (`CS0433: The type 'Vector2' exists in both 'Microsoft.Unity.Analyzers' and 'UnityEngine.CoreModule'`, seen in Editor.log) for that one compile; gone once the platforms were off. Set the importer first next time (or copy the DLL together with a pre-made importer state).
  - Probes (temporary, deleted through the Editor): `XProbe` in `Assets/Kit/Spike/Runtime/` (assembly `Kit.Spike`), `XProbe2` in `Assets/Kit/` (`Assembly-CSharp`), each with an empty `Update` and `new X()` on a `MonoBehaviour`.
    - **With `dotnet_diagnostic.UNT0010.severity = error` in `.editorconfig`:** compile ran, console had no UNT line for either probe (`CS0168` for a deliberate unused variable did show, so warnings reach the console). So **Unity's compile does not apply `.editorconfig` severities**.
    - **With `Assets/Default.ruleset` (`<Rule Id="UNT0010" Action="Error" />`), `.editorconfig` line removed:** `Assets\Kit\Spike\Runtime\XProbe.cs(11,17): error UNT0010: Component 'XProbe' should not be instantiated directly.`; after deleting `XProbe`: `Assets\Kit\XProbe2.cs(12,17): error UNT0010: Component 'XProbe2' should not be instantiated directly.` (plus `CS0168`). Both assemblies are covered, so the analyzer in a folder with no asmdef applies to custom asmdefs too (the Unity manual's "predefined assemblies only" reading is not what happens in 6000.3.10f1).
    - `UNT0001` (empty `Update`) did not show at its default severity; with `Action="Warning"` it shows: `AnalyzerProbe.cs(7,14): warning UNT0001: The Unity message 'Update' is empty.`
    - No `CS8032` / "analyzer could not be loaded" at any point after the importer was set.
  - **Decisions:** DLL stays in `Assets/Kit/Analyzers/` (both probes fired). Severity source = `Assets/Default.ruleset` (the card's fallback); `.editorconfig` is unchanged. IDs checked against `doc/index.md` at tag 1.28.0 (the lists in the card match; 23 errors, 18 warnings).
- **Acceptance evidence:**
  1. `uv run --no-project --with pytest pytest scripts/unity/tests -q` → `167 passed in 65.88s` (61 Task 002 tests unchanged + 106 new).
  2. `PASS code-rules: 0 files, 0 new violations, 0 suppressed` (exit 0).
  3. Probe evidence above.
  4. Full gate on this branch with this card: `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope ok, code-rules ok, analyzers on (0 warnings), 0 errors, 0 warnings, ~14s` — file gates `PASS format: 0 files` · `PASS assets: 32 assets, 32 .meta, 5 changed in git` · `PASS scope: 13 changed files in scope, tests may-not-change` · `PASS code-rules: 0 files, 0 new violations, 0 suppressed`; wait-ready: compile 0.05 s, reload 4.1 s; tests 0.67 s, job 5.3 s; no `CS8032`, console errors and warnings empty after the run.
  5. Negative runs:
     - (a) `Debug.Log("x");` added to `SpikeMath.Lerp01` (Edit tool): `FAIL code-rules: Test Environments/Unity Agentic Kit test/Assets/Kit/Spike/Runtime/SpikeMath.cs(7,13): KIT004 Debug.Log left in runtime code` (exit 1, before any compile). Reverted with the Edit tool (`git diff` of the file empty), re-run: `PASS code-rules: 0 files, 0 new violations, 0 suppressed`.
     - (b) `Assets/Kit/Spike/Runtime/AnalyzerProbe.cs`: console after compile: `AnalyzerProbe.cs(13,25): error UNT0010: Component 'AnalyzerProbe' should not be instantiated directly.` → `FAIL compile: ... error UNT0010 ...`. The file gates stop earlier on a probe (`FAIL assets: missing .meta`, then `FAIL scope: outside card scope`), as designed, so the compile run was done with the probe present and the compile steps only. Deleted through the Editor (`delete_script`), console clean afterwards, final gate PASS (4).
  6. File gates (4 scripts) together: 1.9 s (budget 15 s).
  7. No changes under `Library/`, `Temp/`, `Logs/`, `UserSettings/`, `ProjectSettings/`, `Packages/`. New `.meta` files, all created by Unity: `Assets/Kit/Analyzers.meta`, the DLL's, and `Assets/Default.ruleset.meta` (the card expected only the first two; the third comes with the ruleset fallback, which the scope block allows). The DLL's `.meta` shows `labels: - RoslynAnalyzer` and Any/Editor `enabled: 0`.
- **Deviations from the card (all conservative):**
  - Severities in `Assets/Default.ruleset`, not `.editorconfig` (probe evidence above).
  - KIT001 evaluates `#if` conditions as boolean expressions: a branch is editor-guarded only if it can run **only** when `UNITY_EDITOR` is defined. So `#if UNITY_EDITOR || DEVELOPMENT_BUILD` is not guarded, `#else` of `#if !UNITY_EDITOR` is, and `UNITY_EDITOR_WIN/OSX/LINUX/64` count as editor. Conditions that do not parse fall back to the card's literal rule.
  - `// kit-allow` on the line above only counts if that line holds nothing but the comment.
  - `UNT0010`-style errors come from the Editor's own console; the CS8032 check lives in `unity-check` step 2 (needs a console read after `unity-wait-ready` and before any clear).
- **Review (fresh-context subagent): APPROVE with minor findings**, ~70 probes, all verified fixes added with regression tests:
  1. Moving editor code into runtime passed (baseline counted with the new path's editor flag) → baseline now uses the old path's editor-only status at the merge-base; the new side requires editor-only also at the merge-base for files that already existed (a brand-new file trusts its `.asmdef` on disk, so a new editor assembly with its files passes).
  2. A file renamed out of `Tests/` was skipped via its old path → only the new path decides test-ness.
  3. `UNITY_EDITOR_WIN/OSX/LINUX` were reported as runtime → recognised.
  4. Nested generics (`FindObjectsByType<List<Foo>>`) and `using static System.Linq.Enumerable;` were missed → handled. Not fixed: a method group (`Action<object> a = Debug.Log;`).
  5. Known, per the card: count comparison is blind to swaps (fix one hit, add another of the same rule in the file).
  6. SKILL wording: the CS8032 read must come right after `unity-wait-ready` and before any console clear (done; `read_console` does accept `filter_text`, used above).
  - A new asmdef flipped to Editor-only in the same diff still trusts new files; the flip itself is for the scope gate and the human.

### 2026-10-11 — Task 002 merged (Claude Code)
- At Alexandros's explicit request in chat, the agent fast-forwarded `main` to `task/002-cheap-gates` (`70a0071..f3e9650`, local only, not pushed). This is an exception to D14 (human merges), asked for by the human. D14 is unchanged.
- `unity-check` on `main`: `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope: no card, 0 errors, 0 warnings`. Script tests `61 passed in 29.70s`. Wait-ready: compile 0.05 s, reload 4.6 s.
- Observed: the Editor reported `is_focused: true` this time, and the test job took 0.6 s instead of ~5.4 s in the earlier unfocused runs. Not investigated; worth knowing when timing gates later.
- `task/003-code-rules-analyzers` already sits on `main`'s tip; no rebase needed.

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
  4. Negative run: trailing whitespace in `SpikeMath.cs` → `FAIL format: Test Environments/Unity Agentic Kit test/Assets/Kit/Spike/Runtime/SpikeMath.cs(9,36): error WHITESPACE: Fix whitespace formatting. Replace 12 characters with '\r\n\s\s\s\s\s\s\s\s'.` exit 1, no `refresh_unity` call. Restored from a backup (`cmp` identical), re-ran: PASS.
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
