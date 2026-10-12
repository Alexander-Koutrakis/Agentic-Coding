# Task 006 — Editor wiring through UnityMCP

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T3)
Coder: csharp · Profile: normal
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
The blade mesh is checked, a URP Lit instancing material exists, the grass feature is on the PC renderer, and a reference scene `GrassReference` shows the 50 x 50 m patch. Everything binary or YAML is changed through UnityMCP, never as text.

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
  - docs/tasks/006-grass-editor-wiring.md
tests: may-not-change
```

## Steps
1. Follow the Unity rules in CLAUDE.md (no text edits of `.unity`, `.mat`, `.asset`, `.meta`). Inspect `Assets/GrassBlade.fbx` through UnityMCP: mesh count, submeshes, bounds, scale in world units, pivot at the blade base. Report numbers. Fix only through import settings in the Editor. If the mesh is unusable, stop and ask.
2. Create `Assets/Kit/Grass/GrassBlade.mat` with the URP Lit shader, GPU instancing enabled (UnityMCP material tools).
3. Find which renderer the active quality level uses (PC or Mobile asset) and add `GrassFeature` to that renderer with the mesh, material and the brief's settings (patch 50 x 50, seed 12345, minScale and maxScale from the mesh size). The Editor serializes the asset, never edit its text.
4. Create scene `Assets/Kit/Grass/GrassReference.unity`: a 50 x 50 m ground plane, one directional light, one camera at a fixed angled-down position that sees the patch, 1920x1080 game view. No grass GameObject. Do not touch `SampleScene`.
5. Enter Play Mode with the reference scene and take a screenshot through UnityMCP; confirm blades are visible and lit. Toggle the feature off and on and read the console after each.
6. Count scene GameObjects before and after raising the count (must not grow).
7. Follow `unity-wait-ready` then `unity-check`; paste the PASS line. Run scope_check.

## Acceptance
- [ ] `unity-check` PASS line
- [ ] Mesh inspection numbers reported
- [ ] Screenshot path (or the UnityMCP capture) shows the patch with blades
- [ ] Feature toggle off/on: console has no errors (paste `read_console` output)
- [ ] Scene object count unchanged when blade count changes
- [ ] `scope_check` clean

## Out of scope
- Code changes in `Runtime/` (T2)
- Perf sweep (T4)
- Changing `ProjectSettings/` or `Packages/`

## Approvals
Needs the human before: nothing beyond plan approval, which covers editing the renderer asset and creating the material and scene. Stop and ask if `ProjectSettings/` must change.
