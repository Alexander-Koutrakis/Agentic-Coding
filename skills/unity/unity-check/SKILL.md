---
name: unity-check
description: The Unity verification gate. Run the file gates (format, asset integrity, scope, code rules), then refresh and compile, read console errors, run EditMode (and optionally PlayMode) tests through UnityMCP, and return one PASS/FAIL line with evidence. Use before saying any Unity task is done.
---

# unity-check

## When to use
At the end of every Unity change, before you report done, commit or hand off. A task is not done while this gate fails.

## Inputs & access
- The Unity project path, relative to the repo root (test project: `Test Environments/Unity Agentic Kit test`).
- The task card, `docs/tasks/<NNN-name>.md`, for the scope gate. If there is no card (for example a check on `main`), the scope gate does not run and the result line says `scope: no card`.
- Python scripts in `scripts/unity/` (run from the repo root with `uv`; they only read files and git, never the bridge) and the .NET SDK for `dotnet format`.
- Skill `unity-wait-ready` (step 1 below).
- UnityMCP tools `read_console`, `run_tests`, `get_test_job`.
- The test assemblies to run. Default: every assembly you added or touched; if unsure, run all of EditMode.
- Never run batch-mode tests while the Editor has the project open.

## Steps
0. **File gates**, one command. Run from the repo root, with the card for the task:
   ```
   uv run --no-project python scripts/unity/file_gates.py begin --project "<project>" --card docs/tasks/<card>.md
   uv run --no-project python scripts/unity/file_gates.py run --project "<project>"
   ```
   - `begin` runs **once, when the task starts** (before your first edit; the lead's brief says so). It records HEAD as the task's base, the card and the branch; on any other branch (for example `main` after the merge) the record is ignored. Every gate then compares against that same base, so earlier committed work (brief, plan, other cards) is never flagged (T1-8, T1-12). Without a record for the current branch the base is `main`. The next task needs its own `begin`, run after the previous card's commit: on a feature branch with several cards this moves the base to the new HEAD, so the scope gate sees only this card's changes.
   - `run` runs format, assets, scope, code-rules in that order and stops at the first one that does not pass. It prints that gate's `FAIL <gate>: ...` line and up to 10 details (full report in `.agent/logs/<gate>.txt`). Do not refresh or compile after a failure.
   - Exit 1: that `FAIL <gate>: ...` line **is** the result line; paste it and its details.
   - Exit 2 (`ERROR ...`, a bad path, missing tool, unreadable card): the result line is `FAIL <gate>: ERROR ...` with the script's text. Fix the call; do not skip the gate.
   - Exit 0: it prints `PASS file-gates: ... base <sha>` and saves it. Do not retype it: step 8 composes the final line from it.
   - No task card (for example a check on `main`): run `run` without `begin`. The line says `scope: no card`.
   - Single gates still work on their own (`scripts/unity/format_check.py`, `asset_check.py`, `scope_check.py`, `code_rules.py`; same `--project`, optional `--base`), for example to re-check one gate while fixing it.
   - **format:** changed `.cs` files under `Assets/` vs the project's `.editorconfig`. Fix the file; never reformat files the task did not touch.
   - **assets:** `.meta` pairs, orphans, GUIDs on disk; `.meta` staged/committed together with its asset. Never write a `.meta` by hand: fix it through the Editor (refresh) or ask.
   - **scope:** changed files vs the card's `scope` block, `ProjectSettings/`/`Packages/` need approval, tests not deleted or weakened. Do not widen the card's scope yourself; ask.
   - **code-rules:** new violations only, in changed non-test `.cs` files: KIT001 `UnityEditor` in runtime code outside `#if UNITY_EDITOR`, KIT002 scene searches/`SendMessage` and KIT003 LINQ in `Update`/`LateUpdate`/`FixedUpdate`/`OnGUI`, KIT004 `Debug.Log`. Fix the code. A justified exception is `// kit-allow KIT00N: <reason>` (same line, or alone on the line above); the PASS line counts them, so the reviewer sees them. Never add a `kit-allow` just to pass without a real reason.
1. **Compile.** Run `unity-wait-ready`. If it does not report ready, the gate is FAIL.
2. **Console errors.** `read_console` with `action="get"`, `types=["error"]`, `count="20"`. Ignore only the bridge's own lines: their text starts with `MCP-FOR-UNITY` after rich-text tags (`<b><color=#cc3333>MCP-FOR-UNITY</color></b>: ...`). Any other error means FAIL, and the entries (file, line, column, CS or UNT code) are the evidence. A `UNT` error is an analyzer error (Microsoft.Unity.Analyzers, severities in `Assets/Default.ruleset`): fix the code, do not weaken the ruleset. If there are errors, stop here; do not run tests against stale assemblies.
   **Analyzers loaded?** Right after `unity-wait-ready`, before any console clear (a cleared console hides a load failure), also read warnings once with `filter_text="CS8032"` and once with `filter_text="analyzer"`. Any `CS8032` or "analyzer ... could not be loaded" line means `FAIL analyzers: not loaded` plus that line. A gate that silently stops analyzing must not pass.
3. **Warnings.** `read_console` with `types=["warning"]`. Report them, but ignore the bridge's own `MCP-FOR-UNITY` lines (as in step 2). Warnings you introduced are fixed; others are listed. List the `UNT` ones on their own line, `analyzer warnings: N` (performance rules; in v1 they do not fail the gate). N goes into the PASS line.
4. **Run tests.** `run_tests` with `mode="EditMode"`, `assembly_names=[...]`, `include_failed_tests=true`. For PlayMode use `mode="PlayMode"` and `init_timeout=120000`. If a run is rejected as already running, call `run_tests` with `clear_stuck=true` once (a lost job after a domain reload) and retry once.
5. **Wait for results.** `get_test_job` with `wait_timeout=30`. Repeat until `status` is `succeeded` or `failed`. One call is normally enough. Stop after about 5 minutes and report a timeout as FAIL.
6. **Collect failures.** On `failed`, read `progress.failures_so_far[]` (`full_name`, `message`). The message holds expected vs actual.
7. **Console again.** Read errors once more. Errors that appeared during the run are FAIL.
8. **Compose the PASS line.** Do not type it. Run:
   ```
   uv run --no-project python scripts/unity/file_gates.py finish --project "<project>" --editor "18/18 EditMode (Kit.Spike.Tests.EditMode)" --errors 0 --warnings 0 --analyzer-warnings 0
   ```
   `--editor` is the real `passed/total`, mode and assemblies from the test job. `finish` prints the PASS line only if the file gates ran on exactly the files now in the tree (otherwise `FAIL stale`: edit happened after `run`, run it again), tests passed equal total and total is above 0, and errors are 0. Paste its output as the result line.

## How to validate
- `file_gates.py finish` printed a `PASS` line (file gates current, zero console errors, job `status` is `succeeded`, `completed == total`, total above 0).
- If `total` is 0, that is FAIL: the assembly name is wrong or the tests did not compile (`finish` rejects it).
- Known-good reference (Spike 001): `Kit.Spike.Tests.EditMode` = 3 tests, all pass; a broken assertion shows as `Expected: 6.0d +/- 9.99e-06d But was: 5.0d`.
- The scripts have their own tests: `uv run --no-project --with pytest pytest scripts/unity/tests -q`.

## What to return
One line, then evidence:
- `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format ok (0 files), assets ok (55 assets, 55 .meta, 0 changed in git), scope ok (4 changed files in scope, tests may-not-change), code-rules ok (0 files, 0 new violations, 0 suppressed), analyzer warnings 0, 0 errors, 0 warnings` (printed by `file_gates.py finish`)
- Same with `scope: no card` in place of the scope part when there is no card.
- `FAIL format: Test Environments/Unity Agentic Kit test/Assets/Kit/Spike/Runtime/SpikeMath.cs(9,32): error WHITESPACE: Fix whitespace formatting. ...`
- `FAIL assets: staged without its .meta: Test Environments/Unity Agentic Kit test/Assets/Kit/New.cs`
- `FAIL scope: outside card scope: scripts/other.py`
- `FAIL scope: needs approval (ProjectSettings/Packages): Test Environments/Unity Agentic Kit test/ProjectSettings/ProjectSettings.asset`
- `FAIL code-rules: Test Environments/Unity Agentic Kit test/Assets/Kit/Spike/Runtime/SpikeMath.cs(12,9): KIT004 Debug.Log left in runtime code`
- `FAIL analyzers: not loaded: warning CS8032: An instance of analyzer ... cannot be created ...`
- `FAIL compile: SpikeMath.cs(9,35): error CS1002: ; expected`
- `FAIL tests 2/3: Kit.Spike.Tests.SpikeMathTests.Lerp01_Midpoint_ReturnsAverage - Expected: 6.0d ... But was: 5.0d`

Paste the real script output, console lines or the job's failure messages; do not paraphrase them.

## Approvals
None. Do not edit tests to make them pass unless the task is to change the tests; if a test fails, report it.
