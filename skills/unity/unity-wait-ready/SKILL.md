---
name: unity-wait-ready
description: After changing Unity scripts or assets, refresh and compile through UnityMCP and wait until the Editor has really finished compiling. Use before reading the console or running tests.
---

# unity-wait-ready

## When to use
After any change to `.cs`, `.asmdef`, `.shader`, `.hlsl`, or any asset, and before you read the console or run tests. Also after a domain reload you triggered (entering/leaving Play Mode).

Why it exists: `refresh_unity` returns at once with `resulting_state: "compiling"`, even with `wait_for_ready=true` (Spike 001, friction #1). Its return value is not proof that compiling finished.

## Inputs & access
- UnityMCP tools `refresh_unity`, `read_console`; resource `mcpforunity://editor/state` (read it with the resource tool, not a tool call).
- **No resource reader?** A subagent often cannot load `ReadMcpResourceTool` (T1-9, T1-11). Do not approximate with a delay. Use "Fallback" below, which needs only `refresh_unity`, `execute_code` and `read_console`.
- Do **not** connect to port 6400 yourself. A second connection closes the MCP link (StdioBridgeHost.cs:605-620).

## Steps
1. Read `mcpforunity://editor/state`. Remember `data.compilation.last_compile_finished_unix_ms` as `B`. If `data.advice.ready_for_tools` is false, wait and re-read before continuing.
2. Call `refresh_unity` with `compile="request"`, `scope="all"` (use `mode="force"` only when a file changed outside the Editor and nothing seems to pick it up). Note `data.compile_started` in the reply.
3. Poll `mcpforunity://editor/state` until **all** of these hold:
   - `data.compilation.is_compiling` is false
   - `data.compilation.is_domain_reload_pending` is false
   - `data.assets.is_updating` is false
   - `data.advice.ready_for_tools` is true
   - `data.compilation.last_compile_finished_unix_ms` is greater than `B`, **or** step 2 reported `compile_started: false`
   - If `blocking_reasons` is `["stale_status"]` and `observed_at_unix_ms` has not changed since your last read, re-reading the resource does not help (seen with the Editor focused, 6 s+). Make one cheap tool call (`read_console` with `count="1"`) and read the resource again; the snapshot refreshed after that call in the Spike 001 follow-up. Cause not established.
   - If the resource comes back mostly `null` (`compilation: null`, `unity_version: null`) or a tool says `Unity instance '...' not found`, the active instance is stale. Unity's instance ID is `Name@hash` and the hash depends on the project path, so renaming or moving the project folder changes it. Read `mcpforunity://instances`, call `set_active_instance` with the new `Name@hash`, then start again at step 1.
4. Give up after about 120 s of polling. Report "still compiling after 120 s" with the last state; do not carry on.

## Fallback (no resource reader)
`execute_code` runs read-only C# in the Editor. The probe below reports the compile state and whether a domain reload has happened since the previous probe (`AppDomain` data is lost on reload):
```csharp
var d = System.AppDomain.CurrentDomain;
bool fresh = d.GetData("kit.probe") == null;
d.SetData("kit.probe", "1");
return new { compiling = UnityEditor.EditorApplication.isCompiling, updating = UnityEditor.EditorApplication.isUpdating, fresh };
```
1. Run the probe once (`action="execute"`). It marks the domain; ignore its result.
2. `refresh_unity` with `compile="request"`, `scope="all"`. Note `compile_started`.
3. Run the probe again every 2-3 s. A call that errors or times out means a reload is under way: wait and retry.
4. Ready when `compiling` and `updating` are false **and** (`fresh` is true, or `compile_started` was false). `fresh` true means a reload happened after step 1, so the new code is loaded.
5. A compile **error** causes no reload, so `fresh` stays false. If `compiling` has been false for 10 s with `compile_started` true and no `fresh`, read errors with `read_console` (`types=["error"]`): errors present means the compile failed (report them, this is the evidence); none means keep polling until the 120 s limit.
6. Give up after about 120 s as in step 4 above. Return the same line, ending `(fallback)`.

## How to validate
- A compile **error** does not trigger a domain reload (`last_domain_reload_after_unix_ms` stays the same). Judge "finished" by `is_compiling` and `last_compile_finished_unix_ms`, never by the reload timestamp.
- Typical timings in the test project: compile 0.1-6 s, domain reload 3-6 s more.

## What to return
One line: `ready: compile 5.6s, reload 5.7s` (from the timestamps) or `NOT READY: <reason>`. With the fallback, `ready: reload seen after 8s (fallback)` (no compile timestamps there).

## Approvals
None. Read-only plus a refresh.
