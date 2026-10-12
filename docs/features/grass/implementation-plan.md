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
| `GrassFieldCreateInfo` | create-info | `seed`, `bladeCount`, `patchSize` (Vector2), `patchCenter` (Vector3), `minScale`, `maxScale` | `GrassFeature` fills it from its settings |
| `GrassBatch` | data | `Matrix4x4[] matrices` (length 1023 at most), `int count` | `GrassField` |
| `GrassField` | system | placement: `Create(in GrassFieldCreateInfo)` validates and builds the batches; exposes `Batches`, `BladeCount`; `Dispose()` | `GrassFeature` (creates in `Create`/`SetBladeCount`, disposes in `Dispose`) |
| `GrassSettings` | data | serialized: `bladeCount`, `patchSize`, `patchCenter`, `seed`, `minScale`, `maxScale`, `mesh`, `material` | `GrassFeature` (serialized field; never written at runtime) |
| `GrassPassData` | data | per-pass Render Graph data: `GrassBatch[] batches`, `Mesh`, `Material` | `GrassPass` (reused class instance given to the render graph) |
| `GrassPass` | system | `ScriptableRenderPass`: records one raster pass, draws all batches, wrapped in a `ProfilerMarker` | `GrassFeature` (creates in `Create`, disposes in `Dispose`) |
| `GrassFeature` | system | `ScriptableRendererFeature`: `Create`, `AddRenderPasses`, `Dispose`, `SetBladeCount(int)` (runtime count, does not touch the serialized settings) | the URP renderer asset (Unity creates and disposes it) |

## Tasks
| ID | Title | Coder (`csharp`/`shader`) | Profile (`normal`/`hot-path`) | Depends on |
|---|---|---|---|---|
| T1 | Blade placement (`GrassField`) with EditMode tests | csharp | normal | none |
| T2 | Renderer feature and raster pass (`GrassFeature`, `GrassPass`) | csharp | hot-path | T1 |
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
- Baseline: none yet

## Risks
- Render Graph API for `DrawMeshInstanced` in a raster pass may differ in URP 17.3 → T2 checks the real API with `unity_reflect` / docs before coding, no guessed names.
- 1023 matrices per call means about 98 draw calls and about 6.3 MB of matrix copy per frame at 100k blades; CPU recording could miss the budget → measured in T4; fallback is a smaller batch copy cost, a decision to be taken with the human, not a silent shader.
- URP Lit lighting data (main light, shadows) may not be ready for a custom pass at the chosen event → T3 screenshot shows lit blades; if not, move the pass event (T2 setting).
- Tests that toggle the feature dirty the renderer asset in the Editor → T4 restores and checks the git diff.
- The blade mesh (already imported by the human) may have a wrong scale or pivot → T3 inspects it and fixes the import settings through the Editor.

## Review
| Reviewer lens | Verdict (pass / changes / veto) | Findings |
|---|---|---|
| architecture and style | | |
| performance and GC | | |
| unnecessary scope | not run (medium tier: two lenses) | |

Human approval:
