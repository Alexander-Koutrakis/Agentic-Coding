# HANDOFF

Read this first. Update it at the end of every session (newest entry on top, keep "Current state" current).

## Current state
- Project: {{name}}. Unity project at `{{unity_project}}/`. Kit installed: {{date}}.

## Next step
1. Open the Unity project once (Unity creates the `.meta` files for `Assets/Kit/Canary/`), commit the canary with its `.meta` files, then run `agentic-kit:unity-check` on the clean tree. Expected: `PASS 3/3 EditMode (Kit.Canary.Tests.EditMode)`. That is the baseline.

## Session log

### {{date}} (kit installed)
- `init` wrote `CLAUDE.md`, `.gitattributes`, `docs/HANDOFF.md`, `logs/friction-log.md` and the canary in `Assets/Kit/Canary/`. Not yet done: the gate on this project.
