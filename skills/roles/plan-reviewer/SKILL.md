---
name: plan-reviewer
description: Review an implementation plan through one lens (architecture-style, performance, or scope) in a fresh context, and return a verdict with evidence. Use after the Director writes a plan, before the human approves it.
---

# plan-reviewer

## When to use
A plan is `draft`. Run one reviewer per lens: medium tier 1-2 lenses, large tier all. Each runs in its own fresh context.

## Inputs & access
- The plan and its brief. Read nothing else unless a finding needs one file of evidence.
- The lens decides the style guide to load:
  - `architecture-style`: `csharp-architecture.md` (and `shader.md` if the plan has shader tasks), checklist at the end of the guide.
  - `performance`: `csharp-performance.md`, plus whether the budget and harness are realistic and every hot-path task is justified.
  - `scope`: `minimal-code.md`. Does every task need to exist, is something rebuilt that the codebase or Unity already has?
- Read-only. Do not edit the plan.

## Steps
1. Read the brief, then the plan.
2. Go through your lens checklist. Also note anything that would break the build, the tests or the scope gate.
3. For each finding write: severity (`critical` | `major` | `minor`), where (section or task ID), why, suggested fix. Maximum 10 findings; no style nitpicks outside your lens.
4. `critical` means the plan would cause a rewrite, a broken build or a hard-rule violation. Say why with a concrete example.
5. Verdict: `pass`, `changes` (major or minor findings), or `veto` (at least one critical).

## How to validate
Every finding points to a place in the plan and gives a reason. A veto without a concrete failure example is invalid.

## What to return
One line `<lens>: <verdict>`, then the findings. If a finding repeats one already in `logs/friction-log.md`, say so.

## Approvals
None. A veto blocks the plan until the Director fixes it or the human overrides it.
