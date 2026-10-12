# Trial 001 — build a rendering feature with the kit

Purpose: find out where the kit helps and where it fails when an agent builds a **new rendering feature** end to end. The agent follows the kit; the human watches and records. The goal is the friction list, not the feature.

## Setup
- Branch from `spike/003-sweep-harness` (or `main` once merged): `trial/001-<feature-name>`.
- Unity Editor open on `Test Enviroments/Unity Agentic Kit test/`, UnityMCP connected from Claude Code started at the repo root. The human does not touch the Editor during a task (D6).
- One agent, one task at a time (D5).

## Task card (fill in with the agent before it starts)
- **Feature:** what it renders and why.
- **Sweep:** the parameter and its points (e.g. blade count 1k, 3k, 6k, 10k, 50k, 100k; at least 4 in the loaded range).
- **Budget:** ms per 1000 and a total at the real in-game count, for which metric. The agent asks; it does not invent them.
- **Reference scene:** camera, resolution, seed, anything animated (wind, time) fixed.
- **Acceptance:** compiles with no errors or warnings, tests pass, harness within budget, visual check (screenshot) of the feature.

## What the agent must follow
`CLAUDE.md` (read first), then `docs/HANDOFF.md`. Gates: `skills/unity/unity-wait-ready`, `skills/unity/unity-check`. Perf: `skills/unity/unity-perf-harness`. Scene and asset edits only through UnityMCP (`unity-scene-safety`).

## What the human records (copy into a "Trial log" section here)
| When | What happened | Kit part involved | Human had to step in? | Fix (script, rule, skill text) |
|---|---|---|---|---|
- Every point where the agent was blocked, guessed an API, ignored a rule, or needed a human decision.
- Every number it reported: was it from a run, and did the evidence (PASS line, `perf_analyze` output) match?
- Time from task card to PASS line, and the number of harness runs.

## Success
- The agent reaches a PASS line from `unity-check` and a `perf_analyze` report with exit 0 (or a reported budget failure with evidence) **without the human relaying output**.
- No rule in `CLAUDE.md` was broken; no scene/prefab/asset text edit; no invented API names.
- Every friction item has a proposed structural fix (script, lint, test or skill step), following "encode repeated mistakes in structure".

## After the trial
Update `docs/HANDOFF.md`, add the friction to `docs/spikes` or a new trial log, and turn the repeats into changes to the skills or scripts.
