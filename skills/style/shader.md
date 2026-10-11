# Shader style (Unity URP, HLSL)

DRAFT. Loaded by: shader coder, plan reviewers on shader tasks, code reviewer. Rules come from Unity's manual (6.3 shader performance, keywords, SRP Batcher) and general GPU practice. Measure before keeping any optimization. Tag: `(confirm)` = needs the human's call.

## Structure
- Write HLSL for URP. Use the URP includes and macros, not hand-written lighting. Start from Unlit, or Simple Lit if lighting is needed.
- Material properties go in one `CBUFFER_START(UnityPerMaterial)` block, built-ins in `UnityPerDraw`. Anything outside breaks the SRP Batcher. Check the shader's Inspector for "SRP Batcher compatible".
- One shader with few variants and many materials, not many near-copies.
- Shared code goes in `.hlsl` includes. Name properties `_PascalCase`, functions `PascalCase`.

## Work per pixel
- Move math from the fragment stage to the vertex stage and interpolate, if the result is linear enough.
- Do per-frame or per-material math in C# and pass it as a property.
- Avoid `sqrt`, `log`, `exp`, `sin`, `cos`, `pow` per pixel. Use `dot`, `cross`, a lookup texture, or a cheaper form. Use built-in helpers (`normalize`, `saturate`, `lerp`).
- Use `half` for colors, directions and short vectors. `float` for world-space positions, UVs and anything with trig or `pow`. Desktop ignores `half`, so only mobile benefits.

## Memory
- Fewer texture reads: compute shapes and gradients, pack channels into one texture, enable mipmaps. No dependent reads in the hot path.
- Read buffers in order. Use constant buffers for read-only data.
- Render targets: smallest size and format that works, no extra MRT outputs.

## Branching
- Avoid `discard` and `clip`: they disable early depth testing. If needed, switch them on only for materials that need them.
- Branch only to skip a large block, and only when neighboring pixels take the same path (same material, same light, same mask). Symmetric branches only: registers are sized for the longest side.
- For cheap work, compute both sides and select with `lerp`, `step` or `saturate`.
- Runtime switch, rarely changed: `dynamic_branch` keyword. Per-material feature, stripped at build: `shader_feature_local`.
- Check the compiled output before assuming a branch cost or saving.

## Keywords and variants
- Use `_local` keywords by default (`shader_feature_local`, `multi_compile_local`). Global only if C# toggles them with the global API.
- `shader_feature_local` when only materials set the keyword. `multi_compile_local` when scripts toggle it at runtime.
- Count variants in the plan. Every added keyword multiplies the build. Remove unused ones with `skip_variants`.

## Gate and checks (to build)
- Compile with 0 shader errors and 0 warnings through the console.
- Planned script check: `CBUFFER_START(UnityPerMaterial)` present, no `discard` without a comment, no global keyword without a reason.

## Reviewer checklist
1. SRP Batcher compatible, all material properties inside `UnityPerMaterial`?
2. Anything expensive per pixel that could move to the vertex stage or C#?
3. `half` and `float` used where the rules say?
4. `discard`/`clip` or a branch that is non-uniform or asymmetric?
5. Global keyword, or a keyword that multiplies variants without need?
6. Measured with the Frame Debugger or GPU profiler, not guessed?
