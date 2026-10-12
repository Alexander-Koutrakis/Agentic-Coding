# Task 014 — Stale task base after a merge

Branch: `task/014-task-base-stale` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: none (kit maintenance, D28)
Coder: csharp · Profile: normal
Pipeline: coder → `unity-check` → report to the human.
Status: gate PASS

## Goal
`file_gates.py` ignores a recorded task base made on another branch, so a check on `main` after a merge no longer picks up the old card and base (found in the unity-check on `main`, 2026-10-12).

## Scope
```scope
allow:
  - scripts/unity/**
  - skills/unity/unity-check/SKILL.md
  - docs/tasks/014-task-base-stale.md
  - docs/HANDOFF.md
tests: may-not-change
```

## Steps
1. `.agent/task-base` records the branch as a third line; `read_task_base` returns None when the current branch differs.
2. Test, skill text.

## Acceptance
- [ ] `just check` passes, `unity-check` PASS line from `file_gates.py finish`
- [ ] test: a base recorded on a task branch is ignored on `main`

## Out of scope
- A `--no-card` option, clearing state in `finish`.

## Approvals
None.
