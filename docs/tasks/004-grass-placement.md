# Task 004 — Blade placement (GrassField)

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T1)
Coder: csharp · Profile: normal
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
A plain C# system that places N blade transforms on a flat rectangular patch from a fixed seed into one flat `Matrix4x4[]`, with EditMode tests. No rendering code.

## Scope
```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Runtime/**
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/EditMode/**
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass.meta
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Runtime.meta
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests.meta
  - docs/tasks/004-grass-placement.md
tests: may-not-change
```

## Steps
1. Create `Assets/Kit/Grass/Runtime/Kit.Grass.asmdef` (references: none yet) and `Tests/EditMode/Kit.Grass.Tests.EditMode.asmdef` (copy the shape of `Kit.Spike.Tests.EditMode`).
2. Write `GrassFieldCreateInfo` (`seed`, `bladeCount`, `patchSize`, `patchCenter`, `minScale`, `maxScale`) and `GrassField` per the plan's data table. `GrassField.Create(in GrassFieldCreateInfo)` validates (bladeCount >= 0, patchSize > 0, 0 < minScale <= maxScale) and throws on bad input; fills one flat `Matrix4x4[]` of length `bladeCount`; no `Dispose` (managed array only).
3. Each blade: position uniform over the patch at `patchCenter.y`, rotation random about the up axis only, uniform scale in `[minScale, maxScale]`, built with `Matrix4x4.TRS`. One `System.Random(seed)`; the blade sequence depends only on seed, so N blades are a prefix of N+1 blades.
4. EditMode tests: same seed and N give identical matrices; different seed differs; `Matrices.Length` equals N; N = 0 gives an empty array; all positions inside the patch and at `patchCenter.y`; scales inside the range; bad `CreateInfo` throws.
5. Follow `unity-wait-ready` then `unity-check` and paste its PASS line. Run scope_check against this card.

## Acceptance
- [ ] `unity-check` PASS line with real counts (new tests included in the EditMode total)
- [ ] Tests listed in step 4 exist and pass
- [ ] `scope_check` reports no out-of-scope file
- [ ] No method has more than 3 parameters; no static state

## Out of scope
- Rendering, GPU buffers, shaders (T2 to T4)
- Any Editor or `UnityEditor` code

## Approvals
None.
