---
name: director
description: Turn an approved feature brief into an implementation plan and task cards. Use after the human approves docs/features/<name>/feature.md.
---

# director

## When to use
A brief has `Status: approved`. Not before.

## Inputs & access
- The approved `feature.md`, `${CLAUDE_PLUGIN_ROOT}/templates/implementation-plan.md`, `${CLAUDE_PLUGIN_ROOT}/templates/task-card.md`.
- Style guides, in `${CLAUDE_PLUGIN_ROOT}/skills/style/`: `csharp-architecture.md` and `minimal-code.md` always; `csharp-performance.md` if any task is hot-path; `shader.md` if any task is a shader.
- Read the repo with search first (`Grep`, `Glob`), whole files only when needed.
- Write access: `docs/features/<name>/implementation-plan.md` and `docs/tasks/`. No source files.

## Steps
1. Apply `minimal-code.md` to the scope: what already exists, what can be reused, what need not be built.
2. Design in words: approach in five lines, then the types (`CreateInfo`, data, system) with an owner for every resource.
3. Split into tasks. Each is one independently testable unit, not smaller (every coder pays a context cost). Set `Coder: csharp | shader` and `Profile: normal | hot-path` per task.
4. Fill the plan from the template. For hot-path or graphics work, write the perf section: budget from the brief, harness, baseline.
5. Write one task card per task from the template, with a `scope` block listing exact paths. Never allow `ProjectSettings/` or `Packages/` unless the plan says why.
6. Run the docs check on the plan and every card: `uv run --no-project python "${CLAUDE_PLUGIN_ROOT}/scripts/core/docs_check.py" <plan> <cards...>`. Fix what it reports.
7. Ask for plan review (`plan-reviewer`, lenses by tier). Fix critical and major findings, then give the plan to the human.

## How to validate
- Every brief acceptance line is covered by at least one task.
- Every task has a coder, a profile, a scope block and acceptance lines.
- Every type in the data table has an owner.

## What to return
Plan path, task list (ID, title, coder, profile), the tier of review used, and the review verdicts.

## Approvals
The human approves the plan before any coding starts. Do not write code or start a coder.
