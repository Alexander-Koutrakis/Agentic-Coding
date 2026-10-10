# HANDOFF

Read this first, then `docs/IMPLEMENTATION_PLAN.md`. Update it at the end of every session
(newest entry on top, keep the "Current state" block current).

## Current state
- Phase: **0 — Foundation (planning)**
- Repo contains: docs only (plan, handoff, research, SpaceXAI blueprint). No skills or scripts yet.
- Blocked on: answers to the open questions in the plan §6 (first track, harnesses, Unity setup).

## Next step
1. ~~Create test project + install CoplayDev/unity-mcp~~ done (D10). Remaining: register the server in Claude Code (stdio) and confirm with `claude mcp list` / `/mcp`; commit the project (check `git status` shows no Library/Temp/Logs/UserSettings/*.csproj).
2. Spike (agent + Alexandros): prove the loop edit → refresh → wait for compile → read console → run an EditMode test, with no human relaying. Note every friction point.
3. Create kit repo skeleton (§4 layout), root AGENTS.md, skill template.
4. Build `graphics-feature` skill + perf harness template + `perf_check.py`; prove it on one toy feature (e.g. a simple full-screen effect) with ON/OFF numbers.

## Session log
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
