# Plan: grass

Brief: `docs/features/grass/feature.md` · Tier: medium
Status: approved 2026-10-12 (revision 2: GPU frustum culling and shaders) · Written by the Director.
Styles that apply: `csharp-architecture`, `csharp-performance`, `shader`

## Approach
The grass is a URP renderer feature (Render Graph) with two passes: a compute pass that culls blades against the camera frustum, and a raster pass that draws the survivors with one indirect instanced draw of the blade mesh.
Blade matrices are placed once on the CPU from a fixed seed into one flat array and uploaded to a GPU buffer only when placement changes (count or settings), never per frame.
Each frame the six frustum planes (cached arrays) go to a compute shader that tests one bounding sphere per blade and appends visible blade indices to a GPU buffer; its count is copied into the indirect draw arguments.
A hand-written HLSL grass shader (main light and ambient only) reads each blade's matrix through the visible index. No managed allocation per frame, no CPU readback at runtime.

## Ponytail ladder: what was cut
Rung 1, "does it need to exist", and what the human must confirm:
- **The scene "grass patch component" from the brief is cut.** A component cannot reach the renderer feature without static state or a `Find` (both banned by `csharp-architecture`). The field settings (count, patch size, seed, scale range, mesh, material, compute shader) are serialized on the feature itself. Brief acceptance lines that mention the component are met by the feature (the reference scene needs no grass object, only the feature on the renderer). **Needs the human's OK; if refused, T4 grows a registry design and the plan returns to review.**
- Rung 4: no stock URP shader reads instance data from a GPU buffer, so one hand-written shader is unavoidable; the stock Lit/Unlit materials cannot be used with indirect draws. The shader gate does not exist, so T2 and T3 use the console as their gate and T4 carries the readback test that proves the culling.
- Per-tile culling, occlusion culling, distance fade and LOD are not built (per-blade sphere test is one short kernel; the brief puts the rest out of scope).
- No shadow, depth-only or depth-normals passes and no additional lights in the grass shader (brief: out of scope). Risk below covers what that does to the renderer setup.
- No custom inspector, no settings ScriptableObject asset, no Editor assembly (Editor work is done through UnityMCP in T5).
- No CPU culling path and no per-frame readback of the visible count (a test reads it back, the runtime does not).
- Reuse: `GraphicsBuffer`, `GeometryUtility.CalculateFrustumPlanes` (non-allocating overload), URP shader includes for the main light, `Kit.Perf` (`PerfRunner`, `PerfRunWriter`), the sweep test shape of `ToyInstancesSweepTests`, the `feature.json` format of `Perf/toy-instances`.

## Data and ownership
| Type | Kind | Fields / purpose | Owner (creates and releases) |
|---|---|---|---|
| `GrassFieldCreateInfo` | create-info | `seed`, `bladeCount`, `patchSize` (Vector2), `patchCenter` (Vector3), `minScale`, `maxScale` | `GrassSystem` fills it from `GrassSettings` |
| `GrassField` | system | `Create(in GrassFieldCreateInfo)` validates (throws on bad input, a programmer error) and fills one flat `Matrix4x4[]`; exposes `Matrices`, `BladeCount`. Managed array only, so no `Dispose`. Allocating it on a count change is a setup-time allocation, never per frame; `GrassSystem` drops its reference once the array is uploaded so the 6.4 MB is not kept alive | `GrassSystem` |
| `GrassSettings` | data (serialized struct, also the create-info of `GrassSystem`) | `bladeCount`, `patchSize`, `patchCenter`, `seed`, `minScale`, `maxScale`, `mesh`, `material`, `cullShader` (ComputeShader), `passEvent`. Source of truth, never written at runtime | `GrassFeature` (serialized field) |
| `GrassSetupResult` | result enum | `Ok`, `MissingMesh`, `MissingMaterial`, `MissingCullShader`, `BadSettings` (a renderer feature must not throw during renderer setup) | returned by `GrassSystem.TryCreate` |
| `GrassCullerCreateInfo` | create-info | `cullShader`, `bladeCount`, `boundCenter` (mesh bounds center, object space), `boundRadius` (mesh bounds radius) | `GrassSystem` |
| `GrassCuller` | system | owns three `GraphicsBuffer`s: all blade matrices (`Structured`), visible indices (`Append`), draw arguments (`IndirectArguments`). `Create(in GrassCullerCreateInfo)` validates and allocates; `Upload(Matrix4x4[] matrices, int count)` sets the blade buffer once per placement; `Record(ComputeCommandBuffer cmd, in GrassCullData data)` is the only place that does the per-frame work: `SetCounterValue(0)` on the visible buffer, bind, dispatch, copy the counter into the draw arguments; `Dispose()` releases all three | `GrassSystem` |
| `GrassCullData` | data (class, Render Graph pass data, one cached instance) | references only: the culler and the cached `Vector4[6]` planes; no logic, never disposed by the pass | `GrassPass` |
| `GrassPassCreateInfo` | create-info | `mesh`, `material`, `passEvent` | `GrassSystem` fills it from `GrassSettings` |
| `GrassPassData` | data (class, Render Graph requires it) | references only: culler buffer handles, `Mesh`, `Material`; one instance reused every frame, filled by plain assignment | `GrassPass` |
| `GrassPass` | system | `ScriptableRenderPass`: `Create(in GrassPassCreateInfo)` validates; each frame computes the frustum planes with `GeometryUtility.CalculateFrustumPlanes(camera, Plane[6])` into cached arrays, adds a compute pass that only calls `GrassCuller.Record`, then one raster pass with one `DrawMeshInstancedIndirect`; all delegates cached; wrapped in `ProfilerMarker`s `Kit.Grass.Cull` and `Kit.Grass.Draw`. Draws for `CameraType.Game` only. No native resource, no `Dispose` | `GrassSystem` |
| `GrassSystem` | system (plain class, the logic) | `TryCreate(in GrassSettings, out GrassSystem)` pre-validates the settings and returns `GrassSetupResult` (so bad serialized values never throw inside renderer setup; the inner `Create` calls throw only for programmer errors); owns `GrassField`, `GrassCuller` and `GrassPass`; `SetBladeCount(int)` re-places only when the count changed (dispose the old culler first, create the new one, upload, drop the field); `Dispose()` releases the culler | `GrassFeature` |
| `GrassFeature` | thin adapter (`ScriptableRendererFeature`) | `Create` calls `GrassSystem.TryCreate`; `AddRenderPasses` enqueues the pass when the result is `Ok` and hands it the current system's culler by reference each call; `SetBladeCount(int)` forwards (runtime count, does not touch the serialized settings); `Dispose` forwards. No other logic | the URP renderer asset (Unity creates and disposes it) |
| `GrassCull.compute` | shader | kernel `CSMain`, `[numthreads(64,1,1)]`, dispatch `ceil(N / 64)` groups; one thread per blade, sphere vs six planes, append visible index. Constants: planes, blade count, bound center, bound radius | bound by `GrassCuller` |
| `Kit/GrassInstanced` (`GrassInstanced.shader`) | shader | URP forward pass `UniversalForward`; vertex reads matrix at `_Blades[_Visible[SV_InstanceID]]`; Lambert from the main light plus SH ambient computed in the vertex stage; `float` for world position, `half` for color; `_BaseColor` in `UnityPerMaterial`; buffers sit outside the cbuffer on purpose and SRP Batcher compatibility is not expected for indirect draws; no `discard`, no keywords; the Frame Debugger confirms one indirect draw | the material `GrassBlade.mat` uses it |

Cull design: per-blade sphere test (not per-tile) because 100k threads is one short dispatch; T2 reports the measured cull cost at 100k to confirm. The sphere center is the blade matrix applied to the mesh bounds center, the radius is the mesh bounds radius times the blade's largest scale, so edge blades are not culled by mistake (T4 tests blades just outside and just inside the frustum edge). The kernel reads the full 64-byte matrix per blade; a separate position-and-scale buffer is added only if T2's number shows the kernel is bandwidth-bound.

Layout: `Assets/Kit/Grass/Runtime/Kit.Grass.asmdef`, `Assets/Kit/Grass/Shaders/` (shader and compute files, no asmdef), `Tests/EditMode/Kit.Grass.Tests.EditMode.asmdef`, `Tests/PlayMode/Kit.Grass.Tests.PlayMode.asmdef`. No Editor assembly.

## Tasks
| ID | Title | Coder (`csharp`/`shader`) | Profile (`normal`/`hot-path`) | Depends on |
|---|---|---|---|---|
| T1 | Blade placement (`GrassField`) with EditMode tests | csharp | normal | none |
| T2 | Frustum cull compute shader (`GrassCull.compute`) | shader | hot-path | none |
| T3 | Grass shader (`GrassInstanced.shader`) | shader | hot-path | none |
| T4 | Culler, system, renderer feature and passes (`GrassCuller`, `GrassSystem`, `GrassFeature`, `GrassPass`, `GrassPassCreateInfo`, `GrassSetupResult`) with a GPU readback test | csharp | hot-path | T1, T2, T3 |
| T5 | Editor wiring through UnityMCP: blade mesh check, material, feature on the renderer, reference scene with two camera poses, screenshots | csharp | normal | T4 |
| T6 | Perf sweep test and `Perf/grass/feature.json` | csharp | hot-path | T5 |

Task cards: `docs/tasks/004-grass-placement.md`, `005-grass-cull-compute.md`, `006-grass-shader.md`, `007-grass-feature-pass.md`, `008-grass-editor-wiring.md`, `009-grass-perf-sweep.md`.

Brief acceptance coverage:
- Feature on the renderer asset, toggles off and on without errors: T5 (T4 provides the feature).
- 50 x 50 m patch visible in the reference camera (screenshot): T5.
- N blades drawn; same seed and N give same positions: T1 (determinism, count), T4 (readback shows N visible with the whole patch in view).
- Rotation and size vary, blades stand on the patch plane: T1.
- No GameObject per blade: by design; T5 checks the scene object count.
- Away pose draws none, half-view pose about half, whole patch all N: T4 (readback test with known camera poses), T5 (screenshots).
- No bald edges when the whole patch is in view: T5 screenshot, T4 readback equals N.
- No per-frame managed allocation: T4 (review), T6 (GC bytes in the harness).
- Sweep runs through Play Mode tests, within budget: T6.
- Both shaders compile with 0 errors and 0 warnings: T2, T3 (console), T4.
- Compiles clean, `unity-check` passes: every task.

## Performance
- Budget: from the brief, GPU frame time of the feature (culling plus draw) <= 0.05 ms per 1000 blades and <= 3 ms total at 100,000 blades @ 1920x1080 with the whole patch in view (worst case), Editor, test machine (relative numbers, tolerance 10-15%).
- Harness: scene `GrassReference` (50 x 50 m plane, one fixed camera angled down, 1920x1080, vSync off, seed 12345, nothing animated). Sweep blade count 1000, 3000, 6000, 10000, 50000, 100000, baseline N = 0 (feature on) first and last, 3 repeats shuffled, 100 warmup frames, 300 measured. The slope fit uses N >= 10000 (`fit_min_n`); the 1000, 3000 and 6000 points are reported but not gated, they sit below the GPU timing noise. The binding limit is 3 ms at 100,000 blades (the per-1000 figure is looser at that count). The Scene view stays closed during the run and the pass only draws for Game cameras. Primary metric `gpu_ms`; `feature_ms` (CPU recording of the passes) and `render_ms` as context. The fixed cost is the N = 0 intercept. Per-pass GPU time is not wired in the harness, so cost is read as the slope of frame GPU time over N, and a feature OFF run is the comparison point. Culling gain: one extra measurement at N = 100000 with the half-view camera pose, reported next to the full-view number. The OFF toggle is restored in `finally` and the renderer asset must show no diff after the run.
- Noise rules: the sweep is invalid if the two N = 0 runs differ by more than 15% in `gpu_ms`. `gpu_valid` must be true in every run; if frame GPU time is unavailable the test fails, it never reports 0. The Game view size is reported from `run.json`; if the Editor cannot be held at 1920x1080 under `run_tests`, T6 reports the real size and asks the human. The directional light in `GrassReference` is fixed so lighting cost is comparable.
- Baseline: none yet; T6 records the first accepted result as the baseline.

## Risks
- Render Graph API in URP 17.3: compute pass, `ImportBuffer`, `DrawMeshInstancedIndirect` on the raster command buffer, and how a test can run the culler without a renderer → T4 checks the real API with `unity_reflect` / docs before coding, no guessed names. If the culler cannot be driven from a plain test, the readback test runs inside a test scene that renders through the feature.
- The PC renderer uses Forward+ and no depth priming; a grass shader with only `UniversalForward` and the main light may not match other objects' lighting or may break features that need depth or depth-normals (SSAO) → T5 screenshot shows lit blades and the console is clean; extra passes stay out of scope unless T5 shows they are required, then the human decides.
- Compute shader plus indirect draw is not covered by a shader gate → T2 and T3 prove 0 console errors and warnings, T4's readback test proves culling counts, the reviewer lists the `shader.md` checklist by reading.
- `GraphicsBuffer` leaks on disable or when the count changes → `GrassCuller.Dispose` is called from `GrassFeature.Dispose` and before each rebuild; T4 test creates and disposes twice and the console must show no leak warning.
- Indirect draws bypass the SRP Batcher and Unity's own culling, so the draw is one call but its bounds must be large enough (bounds passed to the indirect call cover the patch) → T4 sets the bounds from the patch size.
- The harness may not see the cost of culling separately from the draw → accepted, one combined number against one budget; per-pass GPU time is a later harness item.
- Tests that toggle the feature dirty the renderer asset in the Editor → T6 restores and checks the git diff.
- The blade mesh (already imported by the human) may have a wrong scale or pivot, and its triangle count decides the vertex cost at 100k instances (100 triangles per blade would be 10M) → T5 inspects it, reports vertex and triangle counts, and the human agrees a cap or accepts the number before T6 runs; scale and pivot are fixed through the import settings in the Editor.
- The append counter must be reset every frame or the draw count accumulates → `GrassCuller.Record` does `SetCounterValue(0)`; the T4 readback test runs at least two consecutive frames with different poses.

Built differently from the plan (code review, 2026-10-12): `DrawMeshInstancedIndirect` on the command buffer takes no bounds, so the "bounds cover the patch" item is moot; `GrassCullerCreateInfo` also has `indexCount`; markers are `ProfilingSampler`s named `Kit.Grass.Cull` and `Kit.Grass.Draw` (recordable by the harness).

## Review
| Reviewer lens | Verdict (pass / changes / veto) | Findings |
|---|---|---|
| architecture and style | changes | 0 critical, 3 major: Unity-facing feature held logic (added `GrassSystem`, the feature is a thin adapter); per-frame cull steps split between culler and pass (the culler's `Record` owns them); throw vs result policy unclear (`TryCreate` pre-validates). 6 minor: `in` on a class, setup allocation, data classes hold references only, shader stage and precision, SRP Batcher note, shader and kernel names. All applied. |
| performance and GC | changes | 0 critical, 3 major: no per-frame counter reset named; mesh triangle cost unbounded; cull sphere ignored mesh center and scale (edge blades lost). 6 minor: kernel layout, vertex lighting, Scene view contamination, low-N noise, 6.4 MB array kept alive, open question not answered. All applied. |

Human approval: Alexandros, 2026-10-12 (brief, plan, component cut, shader exception)
