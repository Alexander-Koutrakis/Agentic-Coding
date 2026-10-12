# Task 009 — Perf sweep test and feature.json

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T6)
Coder: csharp · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
A PlayMode sweep test over blade count in the reference scene, a half-view measurement at 100,000 blades, and `Perf/grass/feature.json` with the agreed sweep and budget. The task ends when the test is written and compiles; running the sweep is the perf-harness stage, done with the human's confirmation.

## Scope
```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/PlayMode/**
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/PlayMode.meta
  - Test Environments/Unity Agentic Kit test/Perf/grass/feature.json
  - docs/tasks/009-grass-perf-sweep.md
tests: may-not-change
```

## Steps
1. Read `skills/unity/unity-perf-harness/SKILL.md` and copy the shape of `ToyInstancesSweepTests`. Do not edit `Kit.Perf`. Add `Kit.Perf` to the references of `Kit.Grass.Tests.PlayMode.asmdef` if needed (T4 created it).
2. Test: load `GrassReference` in Play Mode (`EditorSceneManager.LoadSceneInPlayMode`, Editor guard), find the `GrassFeature` on the active renderer, set the count per point through `SetBladeCount` before warmup, label `sweep-n<N>-i<index>`, points 1000, 3000, 6000, 10000, 50000, 100000, baseline 0 first and last, 3 repeats shuffled with a fixed seed, `FeatureMarker = Kit.Grass.Draw`, feature name `grass`, seed 12345, whole-patch camera pose. Only the Game view renders; the Scene view must be closed (note it in the report). `fit_min_n` 10000: the 1000, 3000 and 6000 points are reported but not gated.
3. Fail the test if `gpu_valid` is false or the two N = 0 runs differ by more than 15% in `gpu_ms`. Report `Screen.width x height` from `run.json`; if it is not 1920x1080 and cannot be forced under `run_tests`, stop and ask the human. `SetBladeCount` is called only before warmup. After accepting the first sweep, record it as the baseline (human confirms).
4. Culling gain: one extra run at N = 100000 with the half-view pose, label `cull-half-n100000`, run after the sweep points; the report states both numbers.
5. An OFF run: one extra point set with the feature disabled (`SetActive(false)`), restored in `finally`. After the test the renderer asset must show no change in `git status`.
6. `Perf/grass/feature.json`: sweep points, `fit_min_n` 10000, primary metric `gpu_ms`, budgets `gpu_ms per_1000 <= 0.05` and `gpu_ms total_at 100000 <= 3.0`.
7. Follow `unity-wait-ready` then `unity-check`; paste PASS. Do NOT run the full sweep.

## Acceptance
- [ ] `unity-check` PASS line
- [ ] The sweep test compiles and a one-point smoke run (N = 1000, one run) passes with `timing_frames == measured_frames`
- [ ] `feature.json` matches the brief's sweep and budget
- [ ] Renderer asset has no diff after the smoke run
- [ ] `scope_check` clean

## Out of scope
- Running the full sweep and reading the numbers (perf stage)
- Changing `Kit.Perf`

## Approvals
None for the task. The full sweep needs the human to agree the sweep points and budget again before running.
