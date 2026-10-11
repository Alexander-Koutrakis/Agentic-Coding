# Agentic Coding Kit — agent rules

Start every session: read `docs/HANDOFF.md`, then `docs/IMPLEMENTATION_PLAN.md`.
End every session: add an entry to the HANDOFF session log, update "Current state" and "Next step", commit.

## Layout
- Kit docs: `docs/` · spikes: `docs/spikes/` · skills: `skills/<track>/<name>/SKILL.md`
- Unity test project: `Test Enviroments/Unity Agentic Kit test/` (Unity 6000.3.10f1, URP 17.3)
- The Unity Editor is open and reachable through the `UnityMCP` MCP server. The human is not using the Editor while you work.

## The gate (Unity)
- IMPORTANT: after any change to scripts or assets, follow `skills/unity/unity-wait-ready/SKILL.md`. Never trust the return value of `refresh_unity`; it returns while still compiling.
- IMPORTANT: before saying a Unity task is done, committing or handing off, follow `skills/unity/unity-check/SKILL.md` and paste its result line plus the real evidence. No PASS line, not done.
- Do not edit or delete tests to make the gate pass unless the task is to change those tests.

## Unity rules
- IMPORTANT: never edit `.unity`, `.prefab`, `.asset`, `.mat` or `.meta` files as text. Change them through the Editor (UnityMCP) or stop and ask.
- Plain text sources (`.cs`, `.asmdef`, `.shader`, `.hlsl`, `.uss`, `.uxml`) may be written with file tools. Never write a `.meta` by hand; Unity creates it on refresh. Commit every `.meta` together with its asset or folder.
- Re-read a source file before editing it if a compile has happened since you last read it; something can rewrite it (Spike 001, friction #3).
- Console: read errors with `types=["error"]` and warnings separately. Lines starting with `MCP-FOR-UNITY` (often wrapped in rich-text tags like `<b><color=…>`) are the bridge's own messages; ignore them.
- Run tests through UnityMCP (`run_tests` → `get_test_job` with `wait_timeout`). Batch mode cannot open the project while the Editor has it open.
- Never connect to the bridge port (6400) or script the bridge directly: a second client closes Claude Code's MCP link.
- Never touch `Library/`, `Temp/`, `Logs/`, `UserSettings/`.

## Profiler rules
- `get_counters`: always pass explicit counter names, never a whole category (output is huge).
- Numbers from the Edit Mode Editor are zeros. Measure in Play Mode, discard the first samples after entering Play, and never report a single frame as a result.

## Git
- Work on a branch named for the task. Commit with clear messages. Never push.

## Reporting
Show evidence, not claims: the console output, the test result, the numbers.
