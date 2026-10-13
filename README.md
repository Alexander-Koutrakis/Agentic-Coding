# Agentic Coding Kit for Unity

Skills, rules and Python scripts that let an AI coding agent (Claude Code) work on a Unity project **and verify its own work**: compile and console check, EditMode and PlayMode tests, file gates (format, `.meta` integrity, task scope, code rules), a perf harness for rendering features, and a role-based feature pipeline (architect, director, plan reviewers, coders, code reviewer).

It ships as a Claude Code plugin named `agentic-kit`, plus a script that writes the project-owned files into your Unity repo.

## Requirements
- [Claude Code](https://claude.com/claude-code) 2.1.280 or newer
- Unity 6 (developed on 6000.3, URP) with the **MCP for Unity** package ([CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp)) installed in the project, and its server registered in Claude Code under the name `UnityMCP` (stdio). Developed against server version 10.3.0:
  `claude mcp add UnityMCP -- uvx --from mcpforunityserver==10.3.0 mcp-for-unity`
- [uv](https://docs.astral.sh/uv/) (Python is handled by uv), git, the .NET SDK (for `dotnet format`), [Git LFS](https://git-lfs.com/)
- Your Unity project must be in a git repo whose main branch is called `main`.

## Install
1. Clone this repo anywhere, for example `C:\tools\agentic-kit`.
2. Tell Claude Code to load it as a plugin. Set a user environment variable and restart Claude Code:
   - Windows (PowerShell): `[Environment]::SetEnvironmentVariable("CLAUDE_CODE_PLUGIN_DIRS", "C:\tools\agentic-kit", "User")`
   - macOS/Linux: `export CLAUDE_CODE_PLUGIN_DIRS=/path/to/agentic-kit` in your shell profile

   Or start a session with `claude --plugin-dir <path to this repo>`. Skills then appear as `agentic-kit:<name>`.
3. In your Unity project's repo, write the project files (never overwrites existing ones):
   ```
   python <kit>/scripts/core/init_project.py --target <your repo> --name "<project name>"
   ```
   This creates `CLAUDE.md` (agent rules), `.gitattributes` (LF for Unity YAML, Git LFS for binaries, UnityYAMLMerge), `docs/HANDOFF.md` and `logs/friction-log.md`.
4. Once per clone of your project, register the Git LFS hooks and the Unity YAML merge driver:
   ```
   python <kit>/scripts/core/setup_git.py --repo <your repo>
   ```
5. Open the project in the Unity Editor (it creates the `.meta` files for the canary that step 3 wrote to `Assets/Kit/Canary/`), commit the canary with its `.meta` files, then start Claude Code in the repo and ask it to run `agentic-kit:unity-check`. A healthy install ends in `PASS 3/3 EditMode (Kit.Canary.Tests.EditMode)`. The canary is a tiny known-good assembly with 3 tests; the gate fails on zero tests, so a project without any test assembly cannot pass. Skip it with `--no-canary` if your project already has tests.

## What is in it
| Path | What |
|---|---|
| `skills/unity/` | `unity-wait-ready` (really wait for compile), `unity-check` (the gate), `unity-perf-harness` (cost of a rendering feature) |
| `skills/roles/` | architect, director, plan-reviewer, csharp-coder, shader-coder, code-reviewer |
| `skills/style/` | one-page style guides the roles load (C# architecture, C# performance, shader, minimal code) |
| `scripts/unity/` | file gates (`file_gates.py` runs them), perf analysis |
| `scripts/core/` | `init_project.py`, `setup_git.py`, `unity_merge.py`, `docs_check.py` (checks briefs, plans and task cards) |
| `templates/` | brief, implementation plan and task card formats; `templates/project/` is what `init_project.py` writes |

## How agents work with it
- One branch per feature (`feature/<name>`), one commit per task card. Agents never push or merge.
- The Editor is driven only through UnityMCP; scenes, prefabs, assets and `.meta` files are changed through the Editor, never as text.
- "Done" means the `unity-check` PASS line with real evidence.

## Developing the kit
- `docs/IMPLEMENTATION_PLAN.md`: goals, principles, decisions log.
- `docs/HANDOFF.md`: current state and next step; update it at the end of every session.
- `just check` (or `uv run --no-project --with pytest pytest scripts`) runs the script tests. The Unity side is checked with `agentic-kit:unity-check` in a real project.
- Earlier spike and trial write-ups, and the old test project, are in git history (tag `test-project-snapshot`).
