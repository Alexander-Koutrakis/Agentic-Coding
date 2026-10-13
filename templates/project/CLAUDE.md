# {{name}} — agent rules

Rules for working in this repo with the Agentic Coding Kit (Claude Code plugin `agentic-kit`; skills are named `agentic-kit:<skill>`).

Start every session: read `docs/HANDOFF.md`. End every session: add an entry to its session log, update "Current state" and "Next step", commit.

## Layout
- Unity project: `{{unity_project}}/`. The Unity Editor is open and reachable through the `UnityMCP` MCP server; the human does not use the Editor while you work.
- Briefs in `docs/features/<name>/`, task cards in `docs/tasks/`, repeated mistakes in `logs/friction-log.md`.

## Feature pipeline
- Roles are skills: `agentic-kit:architect`, `director`, `plan-reviewer`, `csharp-coder`, `shader-coder`, `code-reviewer`. When you act as a role, invoke its skill first and follow it.
- Tiers: small (coder + gate), medium (short brief, plan, 1-2 plan reviewers), large (full pipeline). The architect proposes, the human confirms.

## The gate (Unity)
- IMPORTANT: after any change to scripts or assets, follow `agentic-kit:unity-wait-ready`. Never trust the return value of `refresh_unity`; it returns while still compiling.
- IMPORTANT: before saying a Unity task is done, committing or handing off, follow `agentic-kit:unity-check` and paste its result line plus the real evidence. No PASS line, not done.
- Do not edit or delete tests to make the gate pass unless the task is to change those tests.

## Unity rules
- IMPORTANT: never edit `.unity`, `.prefab`, `.asset`, `.mat` or `.meta` files as text. Change them through the Editor (UnityMCP) or stop and ask.
- Plain text sources (`.cs`, `.asmdef`, `.shader`, `.hlsl`, `.uss`, `.uxml`) may be written with file tools. Never write a `.meta` by hand; Unity creates it on refresh. Commit every `.meta` together with its asset or folder.
- Re-read a source file before editing it if a compile has happened since you last read it.
- Console: read errors with `types=["error"]` and warnings separately. Lines starting with `MCP-FOR-UNITY` are the bridge's own messages; ignore them.
- Run tests through UnityMCP (`run_tests` then `get_test_job` with `wait_timeout`). Batch mode cannot open the project while the Editor has it open.
- Never connect to the bridge port (6400) or script the bridge directly: a second client closes Claude Code's MCP link.
- Never touch `Library/`, `Temp/`, `Logs/`, `UserSettings/`.

## Profiler rules
- `get_counters`: always pass explicit counter names, never a whole category.
- Numbers from the Edit Mode Editor are zeros. Measure in Play Mode, discard the first samples after entering Play, never report a single frame.
- For the cost of a rendering feature, follow `agentic-kit:unity-perf-harness`. Agree sweep points and budget with the human first. Run it through `run_tests`, never `manage_editor play`.

## Git
- One branch per feature (`feature/<name>`), one commit per task card. A standalone task gets `task/<NNN>-<name>`. Run `file_gates.py begin` (see `agentic-kit:unity-check`) at the start of every card. Never push or merge.
- Once per clone: run the kit's `setup_git.py` (Git LFS hooks and the UnityYAMLMerge driver named in `.gitattributes`).

## Reporting
Show evidence, not claims: the console output, the test result, the numbers.
