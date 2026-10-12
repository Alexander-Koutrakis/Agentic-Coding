# Task 005 — Frustum cull compute shader

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T2)
Coder: shader · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
`GrassCull.compute`: one thread per blade tests the blade's bounding sphere against six frustum planes and appends the blade's index to an append buffer when visible. Compiles with 0 errors and 0 warnings.

## Scope
```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassCull.compute
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassCull.compute.meta
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders.meta
  - docs/tasks/005-grass-cull-compute.md
tests: may-not-change
```

## Steps
1. Read `skills/roles/shader-coder/SKILL.md` and `skills/style/shader.md`; no C# guides. The human allowed shaders in this trial; the shader gate does not exist, so the gate is the console.
2. Kernel `CSMain`, `[numthreads(64,1,1)]`. Inputs: `StructuredBuffer<float4x4> _Blades`; `AppendStructuredBuffer<uint> _Visible`; `float4 _FrustumPlanes[6]` (xyz normal pointing inwards, w distance); `uint _BladeCount`; `float3 _BoundCenter` and `float _BoundRadius` (bounds center and radius of the unscaled blade mesh, object space).
3. Per thread: return if `id.x >= _BladeCount`; center = the matrix applied to `_BoundCenter`; radius = `_BoundRadius` times the largest column length of the upper 3x3; the blade is visible when for all six planes `dot(plane.xyz, center) + plane.w >= -radius`. Append `id.x` when visible. Early-out on the first failing plane. No branching beyond that.
4. Run `unity-wait-ready`; read the console with `types=["error"]` and warnings separately. The compute shader must report no errors or warnings (also check with `manage_shader` if it exposes compile info).
5. Report the measured cull cost at 100,000 blades if you can (Frame Debugger or a one-off check), or say it is left to T6. Report the `skills/style/shader.md` checklist items you verified by reading, yes or no per item (SRP Batcher and keywords do not apply to compute: say so).
6. Follow `unity-wait-ready` then `unity-check` and paste its PASS line. Run scope_check against this card.

## Acceptance
- [ ] `unity-check` PASS line with 0 errors and 0 warnings
- [ ] Console output after the last compile pasted
- [ ] Kernel name, thread group size and the exact property names listed, because T4 binds them by name
- [ ] `scope_check` clean
- [ ] Budget: the feature budget (0.05 ms per 1000 blades, 3 ms at 100,000) is measured in T6; here report the work per blade you added per thread or per vertex

## Out of scope
- The C# that dispatches it (T4)
- Hierarchical or per-tile culling, distance culling

## Approvals
None.
