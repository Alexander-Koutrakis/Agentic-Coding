# Research: how others approach agentic coding (relevant to game/graphics)

Date: 2026-10-10 · Author: Claude (session with Alexandros)
Status: first pass. Web search was disabled for the org during this session, so this covers
known primary sources fetched directly, not a broad sweep. Re-run a wider search when
WebSearch is enabled.

## 1. General agent-harness practice (applies to both tracks)

| Source | What matters for us |
|---|---|
| Anthropic, *Effective harnesses for long-running agents* | Separate an **initializer** session (writes `init.sh`, a progress log, a feature list, first commit) from **coding** sessions. Feature list in **JSON** (models corrupt it less than Markdown); agents may only flip a `passes` field, never delete tests. Each session starts: `pwd` → git log + progress file → pick top unfinished item → run a smoke check *before* adding anything; ends with commit + progress update. → Direct model for our `HANDOFF.md` + task list. |
| Claude Code docs, *Best practices* | "Give Claude a check it can run" is the #1 rule. Gate the stop with a **Stop hook** (deterministic) or a verification subagent, not just a prompt. Keep CLAUDE.md short; move occasional knowledge into skills; use hooks for "must happen every time". Writer/Reviewer split in separate contexts. |
| Claude Code docs, *Skills* | Skill = folder with `SKILL.md` (<~500 lines) + reference files + `scripts/`. Only name+description is always loaded; body on use; reference files on demand. Scripts are *executed*, not loaded (`${CLAUDE_SKILL_DIR}`). Project skills in `.claude/skills/`, or ship as a plugin. |
| Armin Ronacher, *Agentic Coding Recommendations* | Tools must be **fast, quiet, and never hang** (crash is fine, hang is not). Put critical commands in one task runner. Log to files the agent can read and tell it where. Pidfiles to stop double-launches. "The dumbest thing that works." Shared state (DBs, files) must be partitioned for parallel agents. |
| obra/superpowers | Mature open skill set: brainstorm → worktree → plan (2–5 min tasks with exact files + verification) → subagent per task with review → TDD → finish branch. Good reference for *process* skills; nothing engine-specific. |
| banteg/agents | Worktree per task, unattended only inside a container/sandbox, repo-as-zip for big-model review. |
| SpaceXAI blueprint (our docs/) | Six-part skill spec, trust ladder, "fix the environment not the agent", approvals for one-way doors. |

**Takeaway:** nobody publishes a serious game/graphics harness. The general pattern is clear
(verification gate + progress file + skills with scripts + isolation), and the engine-specific
part — the hard part — is ours to build.

## 2. Unity-specific findings

### 2.1 The Library/worktree problem (your first bump) — confirmed and explained
- Unity: *"You can't open a project in batch mode while the Editor has the same project open."*
  So one checkout = one Unity process at a time. Parallel agents need separate project folders,
  each with its own `Library/` — which is the expensive part.
- ParrelSync (multiplayer clone tool) solves a similar problem by **symlinking `Assets`,
  `Packages`, `ProjectSettings`** and keeping `Library/`, `Temp/`, `obj/` per clone. That shares
  sources (not what we want for isolated agent edits) but proves per-clone Library is the norm.

### 2.2 Options to make parallel Unity work affordable
> **Parked (D5, 2026-10-10):** we chose a single live Editor with serial tasks. Kept here for reference only.

| Option | Idea | Cost / risk |
|---|---|---|
| **A. Slot pool** (recommended baseline) | Fixed N persistent clones ("slots"), each with a warm `Library/`. A task *borrows* a slot and does `git switch` inside it instead of creating a fresh worktree. Library pays the full import once per slot, then only incremental reimports. | N × Library disk, once. Needs a lock/lease script so two agents never share a slot. |
| **B. Local Unity Accelerator** | Run Accelerator (installer or Docker) on the dev box; it caches import results, compiled shaders and texture compression. A new/cold slot pulls from cache instead of re-importing. | Extra service. Docs don't explicitly cover fresh-Library speedup → must benchmark. |
| **C. Dev Drive (ReFS) block cloning** | Win11 24H2+: copies on Dev Drive are metadata-only ("multiple files share the same logical clusters"). Copying a Library could be near-instant and nearly free in space. | Requires a Dev Drive volume. Microsoft doesn't state which copy APIs/tools trigger it → must test (robocopy vs Explorer vs Python `shutil`). |
| **D. Code-only lane** | For pure C# logic, agent edits in a cheap worktree and checks with a compile of the generated `.csproj` (references a warm slot's `Library/ScriptAssemblies` + Unity DLLs) or Roslyn validation. No editor launch. | Doesn't cover scenes/assets/PlayMode. Experiment. |
| **E. Live editor via MCP** | One open editor; the agent drives it (refresh, compile, read console, run tests). | Serial: one agent per editor. Best for the "home cook" rung. |

These combine: **A + B (+ C if available)** for parallel work, **E** inside each slot, **D** as a fast pre-check.

### 2.3 Unity ↔ agent bridges (MCP)
| Project | Notes |
|---|---|
| CoplayDev/unity-mcp ("MCP for Unity") | ~14.8k★, MIT, v10.3.0 (2026-10-04), Unity 2021.3–6.x, Python 3.10+/uv. 50 tools in toggleable groups: `read_console`, `refresh_unity` (+compile), `validate_script`, `run_tests`/`get_test_job` (async), `manage_scene`, `manage_prefabs`, `manage_profiler` (incl. Frame Debugger), `manage_build`, `manage_shader`, `execute_code`, `set_active_instance` (multi-instance routing). Most complete off-the-shelf option. |
| IvanMurzak/Unity-MCP | ~4k★. 70+ tools, Roslyn `script-execute`, custom tools via `[AiTool]` attributes, **also runs inside built games** (runtime tools) — interesting for in-game verification/bots. |
| Unity official AI Assistant package | Docs fetch failed; status of an official MCP endpoint unverified. Check again. |

**Implication:** we probably don't write a bridge. We wrap one with *our* skills, safety
rules and scripts, and keep the option to swap it (thin adapter, so Unreal/Godot fit later).
Multi-instance routing (`set_active_instance`) matters for the slot pool.

### 2.4 Headless verification (no MCP needed)
- Test Framework CLI: `-runTests -testPlatform EditMode|PlayMode|<BuildTarget> -testResults <xml>
  -testFilter -testCategory -assemblyNames`, plus `-batchmode -logFile <path>`.
- Don't combine `-quit` with `-runTests` (editor may quit before tests finish).
- `-nographics` disables output logs unless `-logFile` is given; also no GPU → unsuitable for render tests.
- `-accept-apiupdate` needed in batch mode or API updater skips → spurious compile errors.
- Batch mode exits with code 1 on exception; `-executeMethod` + `EditorApplication.Exit(n)` for custom checks.
→ A Python wrapper turns this into one command returning a short pass/fail + parsed NUnit XML + log excerpt.

## 3. Pure C++ / C# / Vulkan findings
- Cheap isolation: plain git worktrees work (build dirs are per-worktree; use ccache/sccache to share compile cache).
- RenderDoc is scriptable from Python: `renderdoc` module (replay API, full features; standalone
  build `renderdoc.pyd` on Windows, not in the distributed build) and `qrenderdoc` (UI API). →
  Feasible to build "capture → dump pipeline state / textures / draw list as JSON" scripts so an
  agent can *read* a frame.
- Khronos validation layers: make validation messages a **hard test failure** (debug callback
  counts errors → non-zero exit). Details of layer settings to confirm from LunarG docs (fetch failed).
- Golden-image tests (headless render → diff vs reference with tolerance) are the visual
  equivalent of unit tests. No standard tool found yet; small Python script.

## 4. Gaps / to research next (when search is enabled)
- Real-world reports of teams running parallel agents on Unity (slot pools, Accelerator numbers).
- Official Unity MCP / AI Assistant status.
- Existing RenderDoc MCP servers or agent scripts; Vulkan "agent-friendly" test harnesses.
- Shader tooling for agents: DXC/slang compile + reflection as a check.
- Unreal (Horde, UBT/UAT automation) and Godot (`--headless`, GUT/gdUnit) for later adapters.

## Sources
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/skills
- https://lucumr.pocoo.org/2025/6/12/agentic-coding/
- https://github.com/obra/superpowers
- https://github.com/banteg/agents
- https://github.com/CoplayDev/unity-mcp · https://coplaydev.github.io/unity-mcp/reference/tools/
- https://github.com/IvanMurzak/Unity-MCP
- https://github.com/VeriorPies/ParrelSync
- https://docs.unity3d.com/Manual/UnityAccelerator.html
- https://docs.unity3d.com/6000.2/Documentation/Manual/EditorCommandLineArguments.html
- https://docs.unity3d.com/Packages/com.unity.test-framework@1.4/manual/reference-command-line.html
- https://learn.microsoft.com/en-us/windows/dev-drive/
- https://learn.microsoft.com/en-us/windows-server/storage/refs/block-cloning
- https://renderdoc.org/docs/python_api/index.html
