# Task 002 — Cheap gates (format, asset integrity, scope)

Branch: `task/002-cheap-gates` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: §4.5
Pipeline: implementer → `unity-check` → reviewer (fresh context, checks the diff against this card) → report to Alexandros.
Status: **implemented 2026-10-11, gate PASS; awaiting review and merge.** Evidence in `docs/HANDOFF.md`.

## Goal
Add three gates that read files on disk and run **before** the compile step of `unity-check`, cheapest first, stopping at the first FAIL:
1. **Format:** changed `.cs` files follow `.editorconfig`.
2. **Asset integrity:** every asset under `Assets/` has a `.meta`, there are no orphan `.meta` files and no duplicate GUIDs, and changed assets moved together with their `.meta` in git.
3. **Scope:** the branch only changes files that the task card allows, and it does not delete or weaken tests.

These are plain Python scripts. D11 only forbids scripts that talk to the bridge, and these never do.

## Prerequisite
- ~~Install a .NET SDK~~ Done 2026-10-11: .NET SDK **8.0.425** (winget `Microsoft.DotNet.SDK.8`), `dotnet format` 8.3.731007. If `dotnet` or its SDK is missing on another machine, the format gate must FAIL with `FAIL format: no .NET SDK (dotnet format unavailable)`, never skip.

## Scope
The scope gate (part 3) reads this block. Paths are relative to the repo root; `*` matches within one folder and `**` across folders. A `.meta` is allowed when its asset is allowed.

```scope
allow:
  - scripts/unity/**
  - skills/unity/unity-check/SKILL.md
  - Test Environments/Unity Agentic Kit test/.editorconfig
  - docs/tasks/002-cheap-gates.md
  - docs/HANDOFF.md
  - docs/IMPLEMENTATION_PLAN.md
  - CLAUDE.md
tests: may-not-change
```

## Steps

### 0. Shared conventions (all three scripts)
- Location: `scripts/unity/`. Python standard library only, run with `uv run --no-project python scripts/unity/<name>.py ...`.
- Arguments: `--repo <path>` (default: current folder), `--project <path relative to repo>` (required; never hardcode `Test Environments/...`, because the folder may be renamed, plan §6), `--base <ref>` (default `main`).
- **Changed files** = `git diff --name-status <merge-base(base, HEAD)>` + staged + unstaged + untracked files (`git status --porcelain=v1 -z`), with renames tracked. Put this in one shared module (`scripts/unity/changed_files.py`) that all three scripts use.
- Output: **one line** on stdout, `PASS <gate>: <summary>` or `FAIL <gate>: <first problem>`, then at most 10 detail lines. The full report goes to `.agent/logs/<gate>.txt` (already gitignored).
- Exit codes: `0` PASS, `1` FAIL, `2` usage or environment error (bad path, not a git repo, missing tool).
- Paths contain spaces (`Test Environments/Unity Agentic Kit test`). Never build shell command strings; call `subprocess` with argument lists.

### 1. Format gate — `scripts/unity/format_check.py` + `.editorconfig`
- Add `.editorconfig` at the test project root (`root = true`), with C# whitespace rules only: `indent_style = space`, `indent_size = 4`, `trim_trailing_whitespace = true`, `insert_final_newline = true`, plus the `csharp_new_line_*` / `csharp_space_*` rules that match the existing `Assets/Kit/Spike/**/*.cs` files.
- **Do not set `end_of_line` or `charset` in v1.** The tracked files are mixed today: `Kit/Spike` files are CRLF without a BOM, while `TutorialInfo` files are LF with a UTF-8 BOM, and `core.autocrlf=true` plus `.gitattributes text=auto` already normalize line endings in git. Enforcing either one would flag files nobody touched.
- Run `dotnet format whitespace "<project>/Assets" --folder --verify-no-changes --include <changed .cs files, relative to Assets/>`. `--folder` mode does not load the Unity-generated `.sln`/`.csproj`, so it needs no restore and no Unity DLLs. Style and analyzer rules, which do need the project loaded, belong to the later **Analyzers** gate.
- **The workspace must be `Assets/`, not the project root.** Measured 2026-10-11 on the 2 Spike files: project root 9.1 s (it scans the 6,684 `.cs` files in `Library/PackageCache`), `Assets/` 1.3 s. Both exited 0. The tests must prove that the `.editorconfig` at the project root still applies when the workspace is `Assets/`.
- Only changed `.cs` files under `<project>/Assets/` are checked. No changed `.cs` file means PASS: `PASS format: 0 files`.
- On FAIL, report `file(line,col): <message>` lines exactly as `dotnet format` prints them.
- Hint for friction #3 (a test file was rewritten under us, with a space after a comma removed): if the format gate flags something nobody wrote, note it in the handoff. Do not chase it in this task.

### 2. Asset integrity gate — `scripts/unity/asset_check.py`
On disk (whole `<project>/Assets/` tree):
- Every file and folder has `<name>.meta`. Unity skips hidden names (starting with `.`), names ending in `~`, and `cvs`/`*.tmp`. Skip the same names and nothing else.
- No orphan `.meta` (a `.meta` with no file or folder beside it).
- Every `.meta` has a `guid:` line with 32 hex characters, and no GUID appears twice.

In git (changed files only):
- An added, deleted or renamed asset under `Assets/` has its `.meta` added, deleted or renamed in the same change, and the other way round (friction #9).

Out of scope here: checking scenes and prefabs for missing scripts through MCP. That comes later, in the MCP part of the gate.

### 3. Scope gate — `scripts/unity/scope_check.py --card docs/tasks/<card>.md`
- Parse the first ```` ```scope ```` block of the card. Its format is shown above: `allow:` globs, and `tests: may-not-change | may-change`. A card with no scope block is FAIL (`FAIL scope: card has no scope block`).
- FAIL if any changed file does not match an `allow` glob. A `.meta` is allowed when its asset path matches.
- FAIL, as "needs approval", if any changed path is under `<project>/ProjectSettings/` or `<project>/Packages/`, even when allowed. The message says the human must approve it. Overriding this belongs to a later task.
- With `tests: may-not-change`, test files are `.cs` files under a `Tests/` folder or inside an assembly whose `.asmdef` has `"UNITY_INCLUDE_TESTS"` in `defineConstraints`. Then FAIL if:
  - a test file is deleted, or
  - a test file has fewer `[Test]`, `[UnityTest]`, `[TestCase(...)]` or `Assert.` occurrences than at the merge-base.
  
  This only catches the obvious cases on purpose. The reviewer catches the rest.

### 4. Wire into `unity-check`
- Edit `skills/unity/unity-check/SKILL.md`: add a new step **0. File gates**, run before the current step 1 (Compile): format → asset → scope, stopping at the first FAIL. Add the card path to "Inputs & access". The scope gate is skipped only when there is no task card (for example, a `unity-check` run on `main`). The skill must say so, and the result line must show it: `scope: no card`.
- New result line format: `PASS 3/3 EditMode (Kit.Spike.Tests.EditMode), format 0 files, assets ok, scope ok, 0 errors, 0 warnings, 11s`. The FAIL examples gain `FAIL format: ...`, `FAIL assets: ...` and `FAIL scope: ...`.
- Keep the six-section skill standard (when to use · inputs & access · steps · how to validate · what to return · approvals).

### 5. Tests for the scripts
- `scripts/unity/tests/`, run with `uv run --no-project --with pytest pytest scripts/unity/tests -q`.
- Each test builds a throwaway git repo plus a fake Unity project in `tmp_path`. **Never** create, delete or edit `.meta` files in the real test project to test the asset gate (CLAUDE.md rule). The negative cases only exist in fixtures.
- Required cases (each with PASS and FAIL):
  - format: a clean file, a file with trailing whitespace or wrong indentation, no changed files, and no SDK (simulate by pointing the `dotnet` path to a missing executable).
  - asset: missing `.meta`, orphan `.meta`, duplicate GUID, a bad `guid:` line, an asset added in git without its `.meta`, an asset renamed without its `.meta`, and hidden and `~` folders being ignored.
  - scope: a file outside `allow`, a `.meta` allowed through its asset, a `ProjectSettings/` change, a deleted test, a removed `Assert`, `tests: may-change` letting the same diff pass, a card with no scope block, and paths with spaces.

## Acceptance (the reviewer checks each one)
1. `uv run --no-project --with pytest pytest scripts/unity/tests -q` passes. Paste the summary line.
2. On this branch, each script run against the real project prints PASS and exits 0. Paste the three lines.
3. Full `unity-check` on this branch, with this card as input, prints the new PASS line, including `PASS 3/3`. Paste it with the evidence.
4. **One live negative run:** add trailing whitespace to `Assets/Kit/Spike/Runtime/SpikeMath.cs`. `unity-check` must stop at `FAIL format: ...` **before** compiling: no `refresh_unity` call happens. Revert, re-run, PASS. Paste both result lines.
5. The three file gates together finish in under 15 s on the test project. Report the time.
6. The scope gate passes on this branch's own diff. This proves the card's scope block covers the work.
7. Nothing in `Library/`, `Temp/`, `Logs/`, `UserSettings/`, `ProjectSettings/` or `Packages/` changed, and no `.meta` was written by hand.

## Out of scope
Roslyn analyzers, code-rule script (banned APIs, `UnityEditor` in runtime code), MCP missing-script check, PlayMode tests, pre-commit hooks, CI, folder rename, LFS / `.gitattributes`, enforcing `end_of_line`/`charset`.

## Approvals
- Ask before changing anything outside the scope block. If the work needs it, stop and say why. Do not widen the block yourself.
- Give up after 3 failed gate loops on the same problem, and report `BLOCKED` with the evidence.
- Do not push or merge (D14).

## Done means
The card's acceptance evidence is pasted into the handoff. The HANDOFF "Current state" and "Next step" are updated, and the plan §4.5 status column moves Format, Asset integrity (disk + git part) and Scope to `built`. Everything is committed on `task/002-cheap-gates`.
