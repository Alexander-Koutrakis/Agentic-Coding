# Task 011 — Code review fixes (leaks, test fixture, restore)

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T4)
Coder: csharp · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
Fix the mechanical findings of the code review: GPU buffers leak when construction fails halfway, the perf test fixture shares state between tests, the OFF restore ignores the original state, and two tests that cannot fail. No behavior change on the success path.

## Scope
The scope gate reads this block. Tests belong to this feature; this card changes them on purpose.

```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Runtime/GrassCuller.cs
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Runtime/GrassSystem.cs
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/PlayMode/GrassPerfSweepTests.cs
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/PlayMode/GrassCullReadbackTests.cs
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassInstanced.shader
  - docs/tasks/011-grass-review-fixes.md
tests: may-change
```

## Steps
1. `GrassCuller` constructor: if allocating or filling the three buffers throws, dispose the ones already created, then rethrow. `GrassSystem.TryCreate` and its place method: if placing throws after the culler exists, dispose the culler. (Review findings 6.)
2. `GrassSystem.TryCreate`: pre-check the mesh bounds radius (not NaN, greater than 0) and the index count and return `BadSettings`, so the promise "never throws in renderer setup" holds. (Finding 7.)
3. `GrassPerfSweepTests`: add a `[SetUp]` that clears the shared `infos` list (finding 1); restore the feature's `isActive` to the value it had before the OFF run, not to true, and assert the renderer asset is not dirty afterwards if the API allows (finding 9); remove `Marker_Category_Check` (finding 10, it asserts nothing). Keep the test names `Smoke_OnePoint` and `Sweep_Grass`.
4. `GrassCullReadbackTests`: no silent fallback to a primitive quad: assert the mesh loaded; make the "create and dispose twice" test honest (rename it to say what it proves, or make it dispose a culler whose construction fails). (Finding 11.)
5. `GrassInstanced.shader`: add a comment that the back face uses the unflipped normal for ambient and that abs(N.L) lights both sides, the limit being acceptable under "lighting tuning out of scope". No code change. (Finding 12.)
6. Run `unity-wait-ready`, then `unity-check` with all Grass EditMode and PlayMode tests except the full `Sweep_Grass`; the readback counts must be the same as before (10000, 0, 5033). Run `Smoke_OnePoint` and report the one-point numbers. Do NOT run `Sweep_Grass`.

## Acceptance
- [ ] `unity-check` PASS line with real counts
- [ ] Readback counts unchanged: whole 10000, away 0, half 5033 of 10000
- [ ] `Smoke_OnePoint` still passes after running it after another test in the same session (fixture state is cleared)
- [ ] Budget: unchanged success path, no per-frame code touched; say that you did not touch `GrassPass` or the per-frame functions
- [ ] `scope_check` clean (use `--base HEAD`)

## Out of scope
- Releasing buffers when the feature is inactive (finding 5), reading back the count in the perf test (4), an away-pose perf run (3): human decisions
- Moving the camera-type filter (finding 8), the SSAO check (13)

## Approvals
None.
