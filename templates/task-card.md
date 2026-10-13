# Task <NNN> — <title>

Branch: `feature/<name>` (or `task/<NNN>-<name>` for a standalone task) · Project: `<path to Unity project>/` · Plan: `docs/features/<name>/implementation-plan.md` (<task id>)
Coder: csharp | shader · Profile: normal | hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo | in progress | gate PASS | reviewed

## Goal
Two to four lines. What exists when this task is done.

## Scope
The scope gate reads this block. Paths are relative to the repo root; `*` stays in one folder, `**` crosses folders. A `.meta` is allowed when its asset is.

```scope
allow:
  - <path or glob>
tests: may-not-change
```

## Steps
1. <step, concrete enough to follow without asking>

## Acceptance
Each line is checked by the gate or the reviewer. Include the evidence to paste.
- [ ] `unity-check` PASS line
- [ ] <observable result>
- [ ] (hot-path) budget `<limit>` met, harness result attached

## Out of scope
- 

## Approvals
Needs the human before: <deleting data, ProjectSettings/Packages changes, anything else>. Otherwise none.
