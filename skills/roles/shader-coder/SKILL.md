---
name: shader-coder
description: Implement one shader task card (Unity URP, HLSL), following the shader style, and verify it compiles clean. Use for any task card with Coder: shader.
---

# shader-coder

## When to use
A task card with `Coder: shader` and an approved plan. One card per run.

## Inputs & access
- The task card and its plan row.
- Style: `skills/style/shader.md` and `minimal-code.md`. Skip the C# guides unless the card also touches C#.
- Skills: `unity-wait-ready`, `unity-check`. CLAUDE.md rules for Unity apply (shader files are text; materials and `.meta` only through the Editor).
- Write only inside the card's `scope` block.

## Steps
1. Create or switch to the branch named in the card (a feature branch holds several cards: one commit per card, never amend an earlier card's commit). Before your first edit run `file_gates.py begin` with the card (see `unity-check` step 0).
2. Apply `minimal-code.md`. Start from URP Unlit or Simple Lit; reuse URP includes.
3. Write the shader following `shader.md`: all material properties in `UnityPerMaterial`, minimum per-pixel math, `_local` keywords, no `discard` without a reason.
4. After every change run `unity-wait-ready` (its "Fallback" section if you cannot read the editor-state resource), then read the console for shader errors and warnings.
5. Create or change materials through UnityMCP only. Check the shader reports SRP Batcher compatible if the tools show it; otherwise say that you checked it by reading the `CBUFFER`.
6. Run `unity-check` with the card. On FAIL fix and run again; after 3 failed attempts report BLOCKED with the evidence.
7. For `hot-path`: measure with the Frame Debugger or the perf harness and attach numbers against the budget.
8. Commit on the branch. Never push or merge.

## How to validate
`unity-check` ends with the PASS line printed by `file_gates.py finish`, with 0 shader errors and 0 warnings. The shader gate (CBUFFER and keyword checks as a script) is not built yet, so state which checklist items from `shader.md` you verified by reading.

## What to return
The PASS line, evidence, the `shader.md` checklist with a yes/no per item, variant count if keywords were added, budget numbers for hot-path, deviations. Or BLOCKED with the last FAIL output.

## Approvals
Ask the human before: widening scope, changing `ProjectSettings/` (including graphics settings) or `Packages/`, deleting data.
