# Spike 001 — Unity agent loop

Goal: prove that an agent in Claude Code can run the full loop **edit → refresh/compile → wait → read console → run tests → read results** through UnityMCP, with no human relaying anything. Record every friction point; they become the kit's first scripts and rules.

Branch: `spike/001-unity-loop` · Project: `Test Enviroments/Unity Agentic Kit test/`
Time-box: one session.

## Steps (agent)
For **every** step, record in the Results table: tool(s) used, wall time, whether it worked first try, and anything surprising.

1. **Baseline.** `git status` is clean (if not, stop and tell the human). Create the branch. Read the Unity console via UnityMCP; note any pre-existing messages.
2. **Runtime code.** Create `Assets/Kit/Spike/Runtime/` with an asmdef `Kit.Spike` and a small class `SpikeMath` (e.g. `static float Lerp01(float a, float b, float t)` clamping `t`).
3. **Compile.** Refresh + compile through UnityMCP. Find out how to know compiling has *finished* (does the tool block? does it return early? does the domain reload drop the MCP connection?). Read the console. Confirm `.meta` files were generated.
4. **Detect a compile error.** Introduce a deliberate syntax error. Refresh, wait, read console. Confirm the agent sees the error with file + line. Fix it, confirm the console is clean.
5. **EditMode tests.** Create `Assets/Kit/Spike/Tests/EditMode/` with asmdef `Kit.Spike.Tests.EditMode` (Editor-only, test assembly, references `Kit.Spike`) and 3 tests for `SpikeMath`. Compile, then run only these tests through `run_tests` and poll `get_test_job` until done.
6. **Detect a failing test.** Break one assertion on purpose. Run, confirm the failure and message are visible. Fix, re-run, all green.
7. **Profiler probe (prep for D7).** Using UnityMCP's profiler tool, find out what you can read in the Editor: frame CPU/GPU time? a custom `ProfilerMarker`'s timing? Just discover and note capabilities; don't build anything.
8. **Wrap up.** Fill in Results + Friction + Proposals below, update `docs/HANDOFF.md`, commit on the branch.

## Results
| Step | Tools used | Wall time | First try? | Notes |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |

## Friction log
(Every time something was slow, confusing, needed a retry, or needed a guess.)

## Proposals
(Which frictions should become a script, a rule in CLAUDE.md, or a skill step. Be concrete.)
