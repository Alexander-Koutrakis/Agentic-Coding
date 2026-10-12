# Plan: grass

Brief: `docs/features/grass/feature.md` · Tier: medium
Status: draft · Written by the Director.
Styles that apply: `csharp-architecture`, `csharp-performance`

## Approach
The grass is a URP renderer feature (Render Graph) whose raster pass draws the blades as instanced draw calls (batches of at most 1023 matrices) of the blade mesh, with a stock URP Lit material with instancing on.
Blade transforms are placed in `Create` (and again when the count changes) from a fixed seed into pre-sliced matrix batches, so the per-frame path only walks the batches and allocates nothing.
The pass runs after opaques on the camera's active color and depth targets. No custom shader, compute or indirect draw (they need a shader).
Cuts and reuse are in the Ponytail ladder section below.

## Ponytail ladder: what was cut
Rung 1, "does it need to exist", and what the human must confirm:
- **The scene "grass patch component" from the brief is cut.** A component cannot reach the renderer feature without static state or a `Find` (both banned by `csharp-architecture`). The field settings (count, patch size, seed, scale range, mesh, material) are serialized on the feature itself. Brief acceptance lines that mention the component are met by the feature (the reference scene needs no grass object, only the feature on the renderer). **Needs the human's OK; if refused, T2 grows a registry design and the plan returns to review.**
- No custom inspector, no settings ScriptableObject asset (the feature is already the settings holder).
- No frustum culling, LOD, distance fade (out of scope in the brief).
- No Editor assembly (nothing editor-only is written in code; the Editor work is done through UnityMCP in T3).
- No new analysis tooling; the existing harness and `perf_analyze.py` are reused as they are.
- Reuse: `Kit.Perf` (`PerfRunner`, `PerfRunWriter`), the sweep test shape of `ToyInstancesSweepTests`, the `feature.json` format of `Perf/toy-instances`.
Rung 3/4 notes: placement uses `System.Random` and `Matrix4x4.TRS` (standard); drawing uses the URP Render Graph raster pass and `DrawMeshInstanced` on the raster command buffer (platform feature, no new package).

## Data and ownership
| Type | Kind | Fields / purpose | Owner (creates and releases) |
|---|---|---|---|
| `GrassFieldCreateInfo` | create-info | `seed`, `bladeCount`, `patchSize` (Vector2), `patchCenter` (Vector3), `minScale`, `maxScale` | `GrassFeature` copies it once from `GrassSettings` |
| `GrassBatch` | data (sealed class, so no managed array sits inside a struct) | `Matrix4x4[] matrices` (length 1023 at most, sliced once), `int count` | `GrassField` |
| `GrassField` | system | `Create(in GrassFieldCreateInfo)` validates (throws on bad input) and builds only non-empty batches (at most the last is partial); exposes `Batches`, `BladeCount`. Holds managed arrays only, so no `Dispose`: dropping the reference releases it | `GrassFeature` (creates in `Create` and in `SetBladeCount`; the old field is just replaced, and only when the count changed) |
| `GrassSettings` | data | serialized source of truth: `bladeCount`, `patchSize`, `patchCenter`, `seed`, `minScale`, `maxScale`, `mesh`, `material`, `passEvent` | `GrassFeature` (serialized field; never written at runtime) |
| `GrassSetupResult` | result enum | `Ok`, `MissingMesh`, `MissingMaterial`, `BadSettings` (expected setup failures; a renderer feature must not throw during renderer setup) | `GrassFeature` (`Create` sets it; `AddRenderPasses` skips the pass unless `Ok`) |
| `GrassPassCreateInfo` | create-info | `mesh`, `material`, `passEvent` | `GrassFeature` fills it from `GrassSettings` |
| `GrassPassData` | data (class, Render Graph requires it) | per-pass data: `GrassBatch[] batches`, `Mesh`, `Material`; one instance reused every frame, filled by plain assignment | `GrassPass` |
| `GrassPass` | system | `ScriptableRenderPass`: `Create(in GrassPassCreateInfo)` validates; records one raster pass and loops over `field.Batches` by index with a plain `for` (no filtering, no LINQ); wrapped in a `ProfilerMarker`. Holds no native resource, so no `Dispose` | `GrassFeature` (creates in `Create`) |
| `GrassFeature` | system | `ScriptableRendererFeature`: `Create`, `AddRenderPasses` (hands the current `GrassField` to the pass by reference every call, so the pass never keeps a stale field), `SetBladeCount(int)` (runtime count, does not touch the serialized settings) | the URP renderer asset (Unity creates and disposes it) |

Layout: `Assets/Kit/Grass/Runtime/Kit.Grass.asmdef`, `Tests/EditMode/Kit.Grass.Tests.EditMode.asmdef`, `Tests/PlayMode/Kit.Grass.Tests.PlayMode.asmdef`. No Editor assembly.

## Tasks
| ID | Title | Coder (`csharp`/`shader`) | Profile (`normal`/`hot-path`) | Depends on |
|---|---|---|---|---|
| T1 | Blade placement (`GrassField`) with EditMode tests | csharp | normal | none |
| T2 | Renderer feature and raster pass (`GrassFeature`, `GrassPass`, `GrassPassCreateInfo`, `GrassSetupResult`) | csharp | hot-path | T1 |
| T3 | Editor wiring through UnityMCP: blade mesh check, material, feature on the renderer, reference scene, screenshot | csharp | normal | T2 |
| T4 | Perf sweep test and `Perf/grass/feature.json` | csharp | hot-path | T3 |

Task cards: `docs/tasks/004-grass-placement.md`, `005-grass-feature-pass.md`, `006-grass-editor-wiring.md`, `007-grass-perf-sweep.md`.

Brief acceptance coverage:
- Feature on the renderer asset, toggles off and on without errors: T3 (T2 provides the feature).
- 50 x 50 m patch visible in the reference camera (screenshot): T3.
- N blades drawn; same seed and N give same positions: T1 (determinism, count), T2 (draws `BladeCount`).
- Rotation and size vary, blades stand on the patch plane: T1.
- No GameObject per blade: by design in T1 and T2; T3 checks the scene object count.
- No per-frame managed allocation: T2 (review), T4 (GC bytes in the harness).
- Sweep runs through Play Mode tests, within budget: T4.
- Compiles clean, `unity-check` passes: every task.

## Performance
- Budget: from the brief, GPU frame time of the feature <= 0.05 ms per 1000 blades and <= 3 ms total at 100,000 blades @ 1920x1080, Editor, test machine (relative numbers, tolerance 10-15%).
- Harness: scene `GrassReference` (50 x 50 m plane, one fixed camera angled down, 1920x1080, vSync off, seed 12345, nothing animated). Sweep blade count 1000, 3000, 6000, 10000, 50000, 100000, baseline N = 0 (feature on) first and last, 3 repeats shuffled, 100 warmup frames, 300 measured. Primary metric `gpu_ms`; `feature_ms` (the pass marker, CPU recording) and `render_ms` as context. The fixed cost is the N = 0 intercept. Per-pass GPU time is not wired in the harness, so cost is read as the slope of frame GPU time over N, and the feature OFF run (feature disabled in the same session) is the comparison point. The OFF toggle is restored in `finally` and the renderer asset must show no diff after the run.
- Noise rules: the sweep is invalid if the two N = 0 runs differ by more than 15% in `gpu_ms` (harness drift warning). `gpu_valid` must be true in every run; if frame GPU time is unavailable the test fails, it never reports 0. The Game view size is reported from `run.json`; if the Editor cannot be held at 1920x1080 under `run_tests`, T4 reports the real size and asks the human instead of continuing silently. The directional light in `GrassReference` is fixed so lighting cost is comparable.
- Baseline: none yet; T4 records the first accepted result as the baseline.

## Risks
- Render Graph API for `DrawMeshInstanced` in a raster pass may differ in URP 17.3 → T2 checks the real API with `unity_reflect` / docs before coding, no guessed names.
- 1023 matrices per call means about 98 draw calls and about 6.3 MB of matrix copy per frame at 100k blades; CPU recording could miss the budget → measured in T4; named fallbacks, to be chosen with the human and never a silent shader: an array or `NativeArray` overload without a temporary allocation if T2 finds one, or fewer and larger copies via a `GraphicsBuffer` path (needs a shader, so it would return to the human as a scope change). T2 checks with `unity_reflect` which overloads of the raster command buffer exist, and slices the batch arrays once so the same references are reused every frame.
- URP Lit lighting data (main light, shadows) may not be ready for a custom pass at the chosen event → T3 screenshot shows lit blades; if not, move the pass event (T2 setting).
- Tests that toggle the feature dirty the renderer asset in the Editor → T4 restores and checks the git diff.
- The blade mesh (already imported by the human) may have a wrong scale or pivot → T3 inspects it and fixes the import settings through the Editor.

## Review
| Reviewer lens | Verdict (pass / changes / veto) | Findings |
|---|---|---|
| architecture and style | veto (critical on the seeded copy only, see trial log; real plan changed after review) | 1 critical: per-frame filter in the pass. 5 major: no `GrassPassCreateInfo`; unclear field ownership on `SetBladeCount` and stale field in the pass; `Dispose` on managed-only types; no failure behavior for bad settings; (2 minor: layout not named, settings vs create-info source). All applied. |
| performance and GC | veto (same critical) | 1 critical: LINQ and list per frame in the pass. 4 major: struct holding a managed array; batch arrays must be sliced once and reused, name the fallback; no noise floor rule; 1920x1080 mechanism. 3 minor: baseline, dirty check in `SetBladeCount`, fixed light. All applied. |
| unnecessary scope | not run (medium tier: two lenses) | |

Human approval:
