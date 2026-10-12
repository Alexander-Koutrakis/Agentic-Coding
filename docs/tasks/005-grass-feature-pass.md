# Task 005 — Renderer feature and raster pass

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T2)
Coder: csharp · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
A URP `ScriptableRendererFeature` (`GrassFeature`) and `ScriptableRenderPass` (`GrassPass`) that draw the `GrassField` batches as instanced draws of the serialized mesh and material, after opaques, with a `ProfilerMarker` named `Kit.Grass.Draw`. Nothing allocates per frame.

## Scope
```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Runtime/**
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/EditMode/**
  - docs/tasks/005-grass-feature-pass.md
tests: may-not-change
```

## Steps
1. Read `skills/style/csharp-performance.md` as well. Before writing code, verify the real Render Graph API in URP 17.3 (`unity_reflect` or `unity_docs`): `RecordRenderGraph`, `AddRasterRenderPass`, `UniversalResourceData` color and depth, `SetRenderAttachment`, and the instanced draw method on the raster command buffer. Do not guess names; note what you verified in your report.
2. Add the URP assembly references to `Kit.Grass.asmdef` (`Unity.RenderPipelines.Universal.Runtime`, `Unity.RenderPipelines.Core.Runtime`).
3. `GrassSettings` (serialized data, fields per the plan), `GrassFeature` (`Create` validates settings, builds the `GrassField` and the pass; `AddRenderPasses` enqueues for game cameras only and skips when the field is empty or mesh/material is null; `SetBladeCount(int)` rebuilds only the runtime field and never writes the serialized settings; `Dispose` releases field and pass), `GrassPass` and `GrassPassData`.
4. Pass: one raster pass, color and depth from the camera's active targets, loop over batches by index calling the instanced draw with `matrices` and `count`; no LINQ, no closures that capture, no `new` per frame (the render graph lambda is a cached static method or cached delegate). The marker wraps the loop.
5. EditMode tests: `Create` throws on null mesh or material or bad settings; `SetBladeCount` changes `BladeCount` and leaves the serialized setting unchanged.
6. Follow `unity-wait-ready` then `unity-check`; paste the PASS line. Run scope_check.

## Acceptance
- [ ] `unity-check` PASS line with real counts
- [ ] The Render Graph API names used are listed with how each was verified
- [ ] No per-frame allocation by inspection: report each line in `AddRenderPasses` and `RecordRenderGraph` that could allocate and why it does not
- [ ] `scope_check` clean
- [ ] Budget and harness result belong to T4; this task only proves it compiles, is allocation-free by design and tested

## Out of scope
- Material, scene, renderer asset changes (T3)
- Perf sweep (T4)
- A custom shader, compute shader or indirect draw

## Approvals
None.
