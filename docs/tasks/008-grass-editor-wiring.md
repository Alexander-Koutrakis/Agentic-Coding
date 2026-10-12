# Task 008 — Editor wiring through UnityMCP

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T5)
Coder: csharp · Profile: normal
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: done

## Goal
The blade mesh is checked, a material using `Kit/GrassInstanced` exists, the grass feature is on the PC renderer, and a reference scene `GrassReference` shows the 50 x 50 m patch with two fixed camera poses (whole patch, about half). Everything binary or YAML is changed through UnityMCP, never as text.

## Scope
```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/GrassBlade.mat
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/GrassBlade.mat.meta
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/GrassReference.unity
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/GrassReference.unity.meta
  - Test Environments/Unity Agentic Kit test/Assets/GrassBlade.fbx
  - Test Environments/Unity Agentic Kit test/Assets/GrassBlade.fbx.meta
  - Test Environments/Unity Agentic Kit test/Assets/Settings/PC_Renderer.asset
  - Test Environments/Unity Agentic Kit test/Assets/Settings/PC_Renderer.asset.meta
  - Test Environments/Unity Agentic Kit test/Assets/Settings/PC_RPAsset.asset
  - Test Environments/Unity Agentic Kit test/Assets/Settings/Mobile_Renderer.asset
  - docs/tasks/008-grass-editor-wiring.md
tests: may-not-change
```

## Steps
1. Follow the Unity rules in CLAUDE.md (no text edits of `.unity`, `.mat`, `.asset`, `.meta`). Inspect `Assets/GrassBlade.fbx` through UnityMCP: mesh count, submeshes, bounds, scale in world units, pivot at the blade base. Report numbers including vertex and triangle counts and the bounds center and radius the feature needs; if the triangle count is high (a blade is a handful of triangles, not dozens) stop and tell the human before T6. Fix only through import settings in the Editor. If the mesh is unusable, stop and ask.
2. Create `Assets/Kit/Grass/GrassBlade.mat` with shader `Kit/GrassInstanced` (UnityMCP material tools).
3. Find which renderer the active quality level uses (PC or Mobile asset) and add `GrassFeature` to that renderer with mesh, material, compute shader and the brief's settings (patch 50 x 50, seed 12345, minScale and maxScale from the mesh size). The Editor serializes the asset, never edit its text.
4. Create scene `Assets/Kit/Grass/GrassReference.unity`: a 50 x 50 m ground plane, one directional light, one camera with a fixed angled-down pose that sees the whole patch and a second fixed pose that sees about half (record both transforms in the report; T6 uses them). No grass GameObject. Do not touch `SampleScene`.
5. Enter Play Mode in the reference scene and take screenshots through UnityMCP of both poses; confirm blades are visible, lit and not bald at the edges of the whole-patch pose. Toggle the feature off and on, reading the console after each.
6. Count scene GameObjects before and after raising the count (must not grow). Check the renderer settings for Forward+ and depth priming and report whether the grass is lit the same as the plane.
7. Follow `unity-wait-ready` then `unity-check` and paste its PASS line. Run scope_check against this card.

## Acceptance
- [ ] `unity-check` PASS line
- [ ] Mesh inspection numbers reported
- [ ] Screenshot paths (or UnityMCP captures) for both poses
- [ ] Feature toggle off/on: console has no errors (paste `read_console` output)
- [ ] Scene object count unchanged when blade count changes
- [ ] `scope_check` clean

## Out of scope
- Code changes in `Runtime/` or `Shaders/` (T2 to T4): report a problem instead
- Perf sweep (T6)
- Changing `ProjectSettings/` or `Packages/`

## Approvals
Needs the human before: nothing beyond plan approval, which covers editing the renderer asset and creating the material and scene. Stop and ask if `ProjectSettings/` must change, or if the grass needs extra shader passes to look right.
