# Agentic Coding Kit — agent rules

Start every session: if no skill named `agentic-kit:*` is listed, the kit plugin is not loaded: stop and tell the human to set the user environment variable `CLAUDE_CODE_PLUGIN_DIRS` to this repo's path and restart (or start with `claude --plugin-dir .`). Skills hold `${CLAUDE_PLUGIN_ROOT}` paths that only resolve when invoked by name, so never read a `SKILL.md` by path to follow it. Then read `docs/HANDOFF.md`, then `docs/IMPLEMENTATION_PLAN.md`.
End every session: add an entry to the HANDOFF session log, update "Current state" and "Next step", commit.

## Layout
- Kit docs: `docs/` (plan, handoff) · `README.md` for users · plugin `agentic-kit` (D31): skills `skills/<track>/<name>/SKILL.md`, scripts `scripts/`, templates `templates/` (project files for `init_project.py` in `templates/project/`)
- No Unity project lives in this repo (D32). The old test project (Unity 6000.3.10f1, URP 17.3, with the `Kit.Spike` and `Kit.Perf` canaries) is in git history, last present at commit `1deeaff`; to use it, check that commit out into a separate folder outside this repo (`git worktree add ../unity-test-snapshot 1deeaff`).
- When you work on a Unity project (a target project, not this repo), its Editor is open and reachable through the `UnityMCP` MCP server, and the human is not using the Editor while you work.

## Feature pipeline (plan §4.6)
- Roles are skills: `agentic-kit:architect`, `director`, `plan-reviewer`, `csharp-coder`, `shader-coder`, `code-reviewer`. When you act as a role, invoke its skill first and follow it.
- Style guides: `skills/style/` (`csharp-architecture`, `csharp-performance`, `shader`, `minimal-code`). Load only the ones your role skill names.
- Formats: `templates/` (`feature.md`, `implementation-plan.md`, `task-card.md`). Briefs live in `docs/features/<name>/`, cards in `docs/tasks/`.
- Repeated mistakes go to `logs/friction-log.md`.

## The gate (Unity)
- `just check` runs the shell-side checks (Python script tests). It does **not** cover Unity: that is `unity-check` below. Report both.
- IMPORTANT: after any change to scripts or assets, follow the skill `agentic-kit:unity-wait-ready`. Never trust the return value of `refresh_unity`; it returns while still compiling.
- IMPORTANT: before saying a Unity task is done, committing or handing off, follow the skill `agentic-kit:unity-check` and paste its result line plus the real evidence. No PASS line, not done.
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
- IMPORTANT: for the cost of a rendering feature (sweep, ms per 1000 instances, GPU/render/main time), follow the skill `agentic-kit:unity-perf-harness`. Agree the sweep points and the budget with the human first. Run it through `run_tests`, never `manage_editor play`. Editor numbers are relative only.

## Git
- Branching (D30): one branch per **feature** (`feature/<name>`) with **one commit per task card**; a standalone task (a gate fix, a spike) gets its own `task/<NNN>-<name>`. Run `file_gates.py begin` at the start of every card, after the previous card's commit. Commit with clear messages. Never push or merge.
- Once per clone: `python scripts/core/setup_git.py` (Git LFS hooks and the UnityYAMLMerge driver named in `.gitattributes`).

## Reporting
Show evidence, not claims: the console output, the test result, the numbers.
