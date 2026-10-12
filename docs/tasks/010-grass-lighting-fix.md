# Task 010 — Fix black blades and blade size (escape from T3/T5)

Branch: `trial/001-grass` · Project: `Test Environments/Unity Agentic Kit test/` · Plan: `docs/features/grass/implementation-plan.md` (T3)
Coder: shader · Profile: hot-path
Pipeline: coder → `unity-check` → code reviewer → report to the human.
Status: todo

## Goal
T5 screenshots show about half of the blades solid black: with `Cull Off` the back faces use the unflipped normal, so N.L is 0 and ambient is not enough. Blades at scale 0.8 to 1.2 (13 cm) are also specks in the whole-patch pose. After this task every blade is lit from both sides, and the blade size makes the patch readable. Evidence: new screenshots from the same two camera poses.

## Scope
The scope gate reads this block.

```scope
allow:
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/Shaders/GrassInstanced.shader
  - Test Environments/Unity Agentic Kit test/Assets/Settings/PC_Renderer.asset
  - Test Environments/Unity Agentic Kit test/Assets/Kit/Grass/GrassBlade.mat
  - docs/tasks/010-grass-lighting-fix.md
tests: may-not-change
```

## Steps
1. Read `skills/roles/shader-coder/SKILL.md` and `skills/style/shader.md`. In `GrassInstanced.shader` make the lighting two-sided without a per-pixel cost: keep the vertex-stage Lambert but use the absolute value of N.L (a flat blade is lit from either side) and keep the SH ambient term; no new keywords, no `discard`, still one variant. Do not move lighting to the fragment stage.
2. Through UnityMCP only, set the feature's `minScale` and `maxScale` on the grass feature in `PC_Renderer` to 2.0 and 3.0 (blades about 26 to 39 cm tall, readable from the reference cameras). Do not change any other setting. Note: Unity reserializes this asset on save; report the diff size.
3. Re-take the screenshots in `GrassReference` for both fixed camera poses (whole patch at (0,45,-50) rot (42,0,0); half at (0,8,-12) rot (30,0,0)) and one closeup, and check that no blade is black and the whole-patch pose shows no bald edges. Save them in the scratchpad directory the lead names.
4. Run `unity-wait-ready`, read the console errors and warnings separately (0 and 0), run all EditMode and PlayMode tests of `Kit.Grass` (the T4 readback tests must still give 10000, 0, about 50 percent). Run `unity-check`; paste the PASS line.

## Acceptance
- [ ] `unity-check` PASS line with 0 shader errors and 0 warnings
- [ ] Screenshots of both poses and a closeup show no black blades
- [ ] T4 readback tests still pass with the same counts
- [ ] Budget: the feature budget is measured in T6; here report what the change adds per vertex (one `abs`)
- [ ] `scope_check` clean (use `--base HEAD`)

## Out of scope
- Shadows, extra passes, normal flipping per face in the fragment stage
- Any C# change; any other renderer or project setting

## Approvals
None; this card fixes a defect found in T5 within the approved plan.
