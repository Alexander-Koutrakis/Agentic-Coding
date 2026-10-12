# Task 007 — Culler, renderer feature and passes

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T4)
Coder: csharp · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
The C# that runs the GPU culling and the draw: `GrassCuller` (owns three `GraphicsBuffer`s), `GrassFeature` (URP renderer feature, settings, result enum), `GrassPass` (compute cull pass and raster indirect-draw pass, markers `Kit.Grass.Cull` and `Kit.Grass.Draw`), and a PlayMode readback test that proves culling counts. Nothing allocates per frame.

## Scope
```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Runtime/**
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/EditMode/**
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/PlayMode/**
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Tests/PlayMode.meta
  - docs/tasks/007-grass-feature-pass.md
tests: may-not-change
```

## Steps
1. Read `skills/style/csharp-performance.md` as well. Before writing code, verify the real URP 17.3 Render Graph API (`unity_reflect` or `unity_docs`): compute pass, `ImportBuffer` for `GraphicsBuffer`, `UniversalResourceData` color and depth, `SetRenderAttachment`, `DrawMeshInstancedIndirect` on the raster command buffer, `SetComputeBufferParam`, `SetComputeVectorArrayParam`, counter copy. Do not guess names; list what you verified.
2. Add the URP assembly references to `Kit.Grass.asmdef` (`Unity.RenderPipelines.Universal.Runtime`, `Unity.RenderPipelines.Core.Runtime`). Add `Kit.Grass.Tests.PlayMode.asmdef` (references `Kit.Grass`, test runner, nunit; copy the shape of `Kit.Perf.Tests.PlayMode`).
3. `GrassSettings`, `GrassSetupResult`, `GrassCullerCreateInfo` (with `boundCenter` and `boundRadius`), `GrassCuller` (blades `Structured`, visible `Append`, args `IndirectArguments`; `Upload(Matrix4x4[], int)` once per placement; `Record(ComputeCommandBuffer, in GrassCullData)` does the counter reset, bind, dispatch and counter copy; `Dispose` releases all three), `GrassPassCreateInfo`, `GrassPass`, `GrassSystem` (`TryCreate` pre-validates and returns the result; owns field, culler and pass; `SetBladeCount` re-places only when the count changed: dispose old culler, create the new one, upload, drop the field), `GrassFeature` (thin adapter that forwards to the system), per the plan's data table. `AddRenderPasses` skips both passes unless the result is `Ok` and enqueues for `CameraType.Game` only. Nothing writes the serialized settings.
4. Per frame: `GeometryUtility.CalculateFrustumPlanes(camera, cachedPlanes)` into cached arrays, then `GrassCuller.Record` (`SetCounterValue(0)` on the visible buffer, dispatch `ceil(N / 64)` groups, copy the counter into the args buffer instance count), then one `DrawMeshInstancedIndirect` with bounds covering the patch. No LINQ, no capturing closures, no `new` per frame (cache delegates). Names of buffers and kernel come from the T2 and T3 reports.
5. PlayMode readback test: three fixed camera poses over the 50 x 50 m patch, N = 10000, seed 12345: whole patch in view reads N visible, camera turned away reads 0, half-view pose reads between 40 and 60 percent of N; run at least two consecutive frames with different poses (the counter must reset); blades placed just outside and just inside a frustum edge are culled and kept correctly. The readback exists only in the test. Also: create and dispose the culler twice with no console warning.
6. EditMode tests: `Create` sets `MissingMesh`, `MissingMaterial`, `MissingCullShader` or `BadSettings` for bad settings and `AddRenderPasses` skips then; `SetBladeCount` changes the runtime count and leaves the serialized setting unchanged.
7. Follow `unity-wait-ready` then `unity-check` and paste its PASS line. Run scope_check against this card.

## Acceptance
- [ ] `unity-check` PASS line with real counts (EditMode and the PlayMode readback test result)
- [ ] The Render Graph API names used are listed with how each was verified
- [ ] Readback numbers for the three poses pasted
- [ ] No per-frame allocation by inspection: report each line in `AddRenderPasses` and the record functions that could allocate and why it does not
- [ ] `scope_check` clean
- [ ] Budget and harness result belong to T6

## Out of scope
- Material, scene, renderer asset changes (T5)
- Perf sweep (T6)
- Editing the shader files (T2, T3): report a problem instead

## Approvals
None.
