# Task 012 — Million-blade sweep from a ground view

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T6)
Coder: csharp · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
The human asked (2026-10-12, in chat) to raise the sweep to a million blades and to measure from a ground-level camera so the culler is exercised. After this task the sweep test runs blade counts 20,000 doubling up to 640,000 and then 1,000,000 (the next double, 1.28M, would pass a million) from a ground view, and records how many blades the culler kept for each run.

## Scope
The scope gate reads this block. This card changes the feature's own perf test on purpose.

```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/PlayMode/GrassPerfSweepTests.cs
  - Test Environments/Unity Agentic Kit test/Perf/grass/feature.json
  - docs/tasks/012-grass-million-ground-sweep.md
tests: may-change
```

## Steps
1. Read `skills/unity/unity-perf-harness/SKILL.md` and the current `GrassPerfSweepTests.cs`. Check the runtime for any cap on the blade count (none was found by grep; confirm `GrassSystem`, `GrassCuller` and `GrassSettings` accept 1,000,000 and report the memory the buffers use at that count).
2. Sweep points: 20000, 40000, 80000, 160000, 320000, 640000, 1000000. Baseline N = 0 first and last, 3 repeats shuffled with the fixed seed, as today. Labels `sweep-n` plus the count and `-i` plus the run index.
3. Add a ground pose: camera at about (0, 1.5, -24), looking along +z with a level pitch (0), inside the patch edge so the frustum sees a wedge of the patch and most blades are behind or beside the camera. Pick the exact numbers so that the culler keeps clearly fewer than all blades, and report them. The primary sweep (label prefix `sweep-`) uses the ground pose.
4. For every run, after `SetBladeCount` and the existing wait frames, read the culler's visible count back (test-only readback, the way `GrassCullReadbackTests` does it) and put it in `PerfRunConfig.Notes` as `visible=` followed by the count so it lands in `run.json`; assert it is 0 for N = 0, never more than N, and for N >= 20000 less than 60 percent of N in the ground pose. Report the visible counts per point.
5. Comparison runs, one run each, same seed: `whole-n` plus the count for the same seven points with the whole-patch pose (all blades visible), and one `off-n1000000` run from the ground pose with the feature disabled (restore the previous `isActive` in `finally`). These labels are not part of the fit; `perf_analyze` only reads `sweep-`.
6. `Perf/grass/feature.json`: the seven points, `fit_min_n` 20000, keep `gpu_ms per_1000 <= 0.05`, and REMOVE the `total_at` entry for 100000 (100,000 is no longer a sweep point). Do not add a total budget for 1,000,000: the human has not given one; report that it is open.
7. Keep `Smoke_OnePoint` (it may use 20000 from the ground pose) and the existing helper structure. Estimate the sweep length (runs x 408 frames) in the report. Do NOT run the full sweep; run `Smoke_OnePoint` and a one-off check at N = 1000000 (one run, ground pose) to prove the count is accepted and report its numbers and visible count.
8. Follow `unity-wait-ready` then `unity-check`; paste the PASS line.

## Acceptance
- [ ] `unity-check` PASS line with real counts
- [ ] A one-run N = 1000000 check passes; its `gpu_ms`, `visible` count and the buffer memory are reported
- [ ] `Perf/grass/feature.json` has the seven points and no 100000 `total_at` budget
- [ ] Budget: per-1000 budget unchanged at 0.05 ms; no total budget for 1,000,000 exists yet (reported as open)
- [ ] `scope_check` clean (use `--base HEAD`)

## Out of scope
- Running the full sweep (the lead does it next), changing any runtime code or shader, an away pose, releasing buffers when disabled

## Approvals
None for this task. The full sweep run follows after this card.
