---
name: csharp-coder
description: Implement one task card in C# for the Unity project, following the architecture style, and loop on unity-check until it passes. Use for any task card with Coder: csharp.
---

# csharp-coder

## When to use
A task card with `Coder: csharp` and an approved plan. One card per run.

## Inputs & access
- The task card and its plan row. Read the whole plan only if the card is unclear.
- Style: `skills/style/csharp-architecture.md` and `minimal-code.md`; also `csharp-performance.md` when `Profile: hot-path`.
- Skills: `unity-wait-ready`, `unity-check`. CLAUDE.md rules for Unity apply.
- Write only inside the card's `scope` block.

## Steps
1. Create or switch to the branch named in the card. Before your first edit run `file_gates.py begin` with the card (see `unity-check` step 0); it fixes the base every gate compares against.
2. Apply `minimal-code.md`, then write the code in the structure the style guide requires.
3. After every change run `unity-wait-ready`, then the console check. If you cannot read the `mcpforunity://editor/state` resource, use its "Fallback" section; never replace it with a fixed delay.
4. Write or update the tests the card asks for. Do not weaken existing tests.
5. Run `unity-check` with the card. On FAIL fix the cause and run it again. After 3 failed attempts stop and report BLOCKED with the evidence.
6. For `hot-path`: run the perf harness and attach the numbers against the budget.
7. Commit on the branch with a clear message. Never push or merge.

## How to validate
`unity-check` ends with the PASS line printed by `file_gates.py finish`. No PASS line from that command, not done; do not type the line yourself.

## What to return
The PASS line, the evidence it prints, any `kit-allow` you added with its reason, deviations from the card, and for hot-path the budget numbers. Or BLOCKED with the last FAIL output.

## Approvals
Ask the human before: widening scope, editing `ProjectSettings/` or `Packages/`, deleting data, changing a test to make the gate pass.
