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
0. **File gates**, cheapest first. Run each from the repo root and stop at the first one that does not exit 0. Do not refresh or compile after a failure:
   ```
   uv run --no-project python scripts/unity/format_check.py --project "<project>"
   uv run --no-project python scripts/unity/asset_check.py --project "<project>"
   uv run --no-project python scripts/unity/scope_check.py --project "<project>" --card docs/tasks/<card>.md
   uv run --no-project python scripts/unity/code_rules.py --project "<project>"
   ```
   No task card (for example a check on `main`): skip the scope command and write `scope: no card` in the result line.
   Each prints one `PASS`/`FAIL <gate>: ...` line and up to 10 details. The full report is in `.agent/logs/<gate>.txt`. `--base` defaults to `main`.
   - Exit 1: the gate's `FAIL <gate>: ...` line **is** the result line; paste it and its details.
   - Exit 2 (`ERROR <gate>: ...`, a bad path, missing tool or unreadable card): the result line is `FAIL <gate>: ERROR ...` with the script's text. Fix the call; do not skip the gate.
   - All exit 0: carry the summaries into the final PASS line as `format <N> files, assets ok, scope ok, code-rules ok`.
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

## How to validate
- All file gates exit 0 **and** zero console errors **and** the job `status` is `succeeded` **and** `completed == total`.
- If `total` is 0, that is FAIL: the assembly name is wrong or the tests did not compile.
- Known-good reference (Spike 001): `Kit.Spike.Tests.EditMode` = 3 tests, all pass; a broken assertion shows as `Expected: 6.0d +/- 9.99e-06d But was: 5.0d`.
- The scripts have their own tests: `uv run --no-project --with pytest pytest scripts/unity/tests -q`.

## What to return
One line, then evidence:
- `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope ok, code-rules ok, analyzers on (0 warnings), 0 errors, 0 warnings, 11s`
- `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope: no card, code-rules ok, analyzers on (0 warnings), 0 errors, 0 warnings, 11s`
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
