# Task 013 — Gate plumbing (friction T1-8 to T1-12)

Branch: `task/013-gate-plumbing` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: none (kit maintenance, D28)
Coder: csharp · Profile: normal
Pipeline: coder → `unity-check` → report to the human.
Status: gate PASS

## Goal
One base for every file gate, one command that runs them and composes the PASS line, and a `unity-wait-ready` fallback for subagents without a resource reader.

## Scope
```scope
allow:
  - scripts/unity/**
  - skills/unity/**
  - skills/roles/**
  - docs/tasks/013-gate-plumbing.md
  - docs/HANDOFF.md
  - docs/IMPLEMENTATION_PLAN.md
  - logs/friction-log.md
tests: may-not-change
```

## Steps
1. `gate_common.resolve_base`: `--base`, else the rev recorded by `file_gates.py begin`, else `main`; all four gates use it.
2. `scripts/unity/file_gates.py` with `begin`, `run`, `finish` and tests.
3. `unity-wait-ready` fallback using `execute_code`; `unity-check` and the coder role files use the new commands.

## Acceptance
- [ ] `just check` passes
- [ ] `unity-check` PASS line printed by `file_gates.py finish`
- [ ] the `unity-wait-ready` fallback probe run live: ready after a compile

## Out of scope
- Shader gate, 1M budget, control run (D27).

## Approvals
None.
