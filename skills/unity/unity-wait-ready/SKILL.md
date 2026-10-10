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
4. Give up after about 120 s of polling. Report "still compiling after 120 s" with the last state; do not carry on.

## How to validate
- A compile **error** does not trigger a domain reload (`last_domain_reload_after_unix_ms` stays the same). Judge "finished" by `is_compiling` and `last_compile_finished_unix_ms`, never by the reload timestamp.
- Typical timings in the test project: compile 0.1-6 s, domain reload 3-6 s more.

## What to return
One line: `ready: compile 5.6s, reload 5.7s` (from the timestamps) or `NOT READY: <reason>`.

## Approvals
None. Read-only plus a refresh.
