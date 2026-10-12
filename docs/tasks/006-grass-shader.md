# Task 006 — Grass shader (URP forward, indirect instances)

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T3)
Coder: shader · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
`GrassInstanced.shader`: hand-written URP HLSL that draws each instance with the matrix found at `_Visible[SV_InstanceID]` in `_Blades`, lit by the main light plus ambient. Compiles with 0 errors and 0 warnings.

## Scope
```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassInstanced.shader
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassInstanced.shader.meta
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassCommon.hlsl
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassCommon.hlsl.meta
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders.meta
  - docs/tasks/006-grass-shader.md
tests: may-not-change
```

## Steps
1. Read `skills/roles/shader-coder/SKILL.md` and `skills/style/shader.md`. Start from URP Unlit; reuse URP includes for the main light and ambient (spherical harmonics). No keywords, no `discard`.
2. Shader name `Kit/GrassInstanced`, one `UniversalForward` pass, `Cull Off` unless the blade mesh needs it (note the choice). Buffers: `StructuredBuffer<float4x4> _Blades`, `StructuredBuffer<uint> _Visible` (same names as the cull compute). Material properties (`_BaseColor`, nothing else needed) in `CBUFFER_START(UnityPerMaterial)`.
3. Vertex stage: `float4x4 m = _Blades[_Visible[instanceID]]`, object to world with `m`, then clip space with the URP camera matrices (indirect draws do not set `unity_ObjectToWorld`). Per-vertex lighting (Lambert with the main light and SH ambient) in the vertex stage, `float` for world position and `half` for color; fragment returns the interpolated color times `_BaseColor`. Check in the Frame Debugger that one indirect draw is issued.
4. Run `unity-wait-ready`; read the console with `types=["error"]` and warnings separately; 0 errors and 0 warnings.
5. Report the `shader.md` checklist with yes or no per item; say that SRP Batcher compatibility was checked by reading the `CBUFFER` (indirect draws do not use the batcher). Variant count is 1.
6. Follow `unity-wait-ready` then `unity-check` and paste its PASS line. Run scope_check against this card.

## Acceptance
- [ ] `unity-check` PASS line with 0 errors and 0 warnings
- [ ] Console output after the last compile pasted
- [ ] Buffer and property names listed, because T4 and T5 bind them by name
- [ ] `shader.md` checklist answered
- [ ] `scope_check` clean
- [ ] Budget: the feature budget (0.05 ms per 1000 blades, 3 ms at 100,000) is measured in T6; here report the work per blade you added per thread or per vertex

## Out of scope
- Shadows, depth-only, depth-normals passes, additional lights, textures (out of scope)
- Material creation (T5)
- C# code (T4)

## Approvals
None.
