# Feature: grass

Tier: medium · Status: approved 2026-10-12 (amended: GPU frustum culling and shaders) · Owner: Alexandros
Written by the Architect with the human. Describes systems and behavior, not code.

## Goal
A flat area covered in grass blades, so a scene reads as a meadow. Blades are drawn as GPU instances of one supplied blade mesh, so the count can be raised to tens of thousands without one object per blade, and blades outside the camera's view are removed on the GPU before drawing (frustum culling), so off-screen grass costs nothing to draw. The feature is also the first real rendering feature run through the kit, so its render cost must be measurable and stay inside a budget.

## Systems
- Blade placement: scatters N blade transforms over a rectangular flat patch from a fixed seed; each blade gets a random rotation around the up axis and a random size within a small range. Same seed and N give the same field.
- Blade culling: each frame the camera's frustum planes are sent to the GPU, a compute step tests every blade against them and keeps only the visible ones in a GPU buffer, together with the draw arguments. The blade data stays on the GPU; it is uploaded when placement changes, not every frame.
- Blade rendering: a URP renderer feature that adds the culling step and a render pass to the camera's renderer and draws only the visible blades each frame as one indirect instanced draw of the blade mesh with a custom grass material (simple lighting from the main light). It is enabled on the project's URP renderer asset (changed through the Editor), not by a component that draws on its own. Talks to the camera and the render pipeline only.
- Grass patch component: the thing a scene author adds; holds the field settings (blade count, patch size, seed) and hands the placed blades to the renderer feature. Mesh and material are settings of the feature.
- Perf harness: sweeps the blade count in a fixed reference scene and reports cost per 1000 blades.

## Out of scope
- Wind or any animation (field is static).
- Per-blade tint or any color variation.
- Shader Graph, mobile targets, receiving or casting shadows, additional lights (the grass shader uses the main light and ambient only).
- Terrain, slopes, heightmaps (flat patch only).
- Occlusion, distance culling or fading, and LODs (frustum culling is in scope).
- Player interaction (trampling), shadows cast by blades, lighting tuning.
- Player-build numbers (Editor numbers are relative only).

## Constraints and budget
- Platform and render pipeline: desktop, delivered as a URP renderer feature, Unity 6000.3.10f1, URP 17.3, C# plus hand-written HLSL (one compute shader for culling, one grass shader). The human allowed shaders in this trial on 2026-10-12; the shader gate does not exist yet, so shader tasks use the console as their gate. Blade mesh is `Assets/GrassBlade.fbx` (imported through the Editor).
- Performance budget: GPU frame time of the feature (culling plus draw) <= 0.05 ms per 1000 blades and <= 3 ms total at 100,000 blades @ 1920x1080 with the whole patch in view (worst case), Editor on the test machine (relative numbers, tolerance 10-15%).
- Sweep: blade count 1000, 3000, 6000, 10000, 50000, 100000 (baseline N = 0 first and last, 3 runs per point). Fit from 10000 up if low counts are non-linear.
- Reference scene: flat plane 50 x 50 m, one fixed camera angled down at the patch, 1920x1080, vSync off, seed 12345, nothing animated; same camera at every sweep point. A second fixed camera pose sees about half of the patch, used once at 100,000 blades to show the culling gain.
- Other limits: no per-frame managed allocation after setup; no new package dependencies; GPU buffers are released when the feature is disabled or removed.

## Acceptance
Observable results a person or a test can check.
- [ ] The grass renderer feature appears on the URP renderer asset, can be toggled off (grass disappears) and on (grass returns) without errors.
- [ ] A scene with the grass component shows a 50 x 50 m patch of blades in the reference camera view (screenshot).
- [ ] Setting the blade count to N draws N blades; the same seed and N give the same blade positions twice.
- [ ] Blades vary in rotation and size, and all stand on the patch plane.
- [ ] No GameObject is created per blade (object count in the scene does not grow with N).
- [ ] No per-frame managed allocation while the field is drawn (GC bytes per frame in the harness are at the Editor floor).
- [ ] With the camera turned fully away from the patch no blade is drawn, with the half-view pose about half are drawn, with the whole patch in view all N are drawn (visible count read back from the GPU in a test).
- [ ] Blades that are in view are not culled by mistake: the screenshot of the whole patch shows no bald edges.
- [ ] The perf sweep runs through Play Mode tests and reports ms per 1000 blades; GPU cost is <= 0.05 ms per 1000 blades and <= 3 ms at 100,000 blades.
- [ ] Both shaders compile with 0 errors and 0 warnings in the console.
- [ ] The project compiles with no errors or warnings and the unity-check gate passes.

## Open questions
- Does the FBX blade mesh import with usable scale, pivot at the blade base and one material slot? → Director checks the imported asset in the Editor.
- How is the feature's own GPU cost measured when it is a render pass (per-pass timing is not wired in the harness yet; otherwise frame GPU time with the feature on vs. off)? → Director proposes with the harness skill, human confirms.
- Does the culling shape (per-blade test vs. per-tile test) fit the 3 ms budget? → Director proposes, plan reviewers judge.
- Does the PC renderer's rendering mode (Forward+) and depth setup allow a custom pass to draw lit grass with only the main light? → coder checks in the Editor and reports.
