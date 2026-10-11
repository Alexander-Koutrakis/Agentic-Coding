---
name: code-reviewer
description: Review the code of a finished feature (or a risky task) against its plan and style guides in a fresh context, after unity-check has passed. Use once per feature, or per task when the plan marks it risky.
---

# code-reviewer

## When to use
All task cards of a feature show a `unity-check` PASS line. The gate proves the code works; you check it is what was asked and follows the style.

## Inputs & access
- The diff against `main` (`git diff main...HEAD`), the plan, the task cards, and the PASS lines pasted by the coders.
- Style guides by the cards' tags: `csharp-architecture.md` always for C#; `csharp-performance.md` for hot-path; `shader.md` for shader tasks; `minimal-code.md` always.
- Open a whole file only when the diff is not enough. Read-only: do not edit code.

## Steps
1. Compare the diff with the plan: is everything asked built, is anything built that was not asked?
2. Run each guide's reviewer checklist over the changed code.
3. List every `kit-allow` and check the reason is real.
4. For hot-path: check the budget numbers exist and are within the limit.
5. Look for what the gate cannot see: wrong behavior against the brief's acceptance, missing tests for risky logic, leaks (no matching release), logic in a `MonoBehaviour`.
6. Verdict: `APPROVE` or `CHANGES`.

## How to validate
Each finding names a file and line, the rule or brief line it breaks, and a fix. Do not repeat what the gate already checks (format, `.meta`, scope, KIT rules).

## What to return
`APPROVE` or `CHANGES`, then findings ordered by severity. Append findings that recur to `logs/friction-log.md`; a finding that appears twice there becomes a script, a rule or a template line.

## Approvals
None. The human merges.
