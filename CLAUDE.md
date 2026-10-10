# Agentic Coding Kit — agent rules

Start every session: read `docs/HANDOFF.md`, then `docs/IMPLEMENTATION_PLAN.md`.
End every session: add an entry to the HANDOFF session log, update "Current state" and "Next step", commit.

## Layout
- Kit docs: `docs/` · spikes: `docs/spikes/`
- Unity test project: `Test Enviroments/Unity Agentic Kit test/` (Unity 6000.3.10f1, URP 17.3)
- The Unity Editor is open and reachable through the `UnityMCP` MCP server. The human is not using the Editor while you work.

## Unity rules
- IMPORTANT: never edit `.unity`, `.prefab`, `.asset`, `.mat` or `.meta` files as text. Change them through the Editor (UnityMCP) or stop and ask.
- Plain text sources (`.cs`, `.asmdef`, `.shader`, `.hlsl`, `.uss`, `.uxml`) may be written with file tools. Never write a `.meta` by hand; Unity creates it on refresh.
- After any script/asset change: refresh + compile through UnityMCP → wait until compiling has finished → read the console. A task is not done while the console shows errors.
- Run tests through UnityMCP (`run_tests` → poll `get_test_job`). Batch mode cannot open the project while the Editor has it open.
- Never touch `Library/`, `Temp/`, `Logs/`, `UserSettings/`.

## Git
- Work on a branch named for the task. Commit with clear messages. Never push.

## Reporting
Show evidence, not claims: the console output, the test result, the numbers.
