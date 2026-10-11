# C# architecture style (Vulkan-style)

v1, confirmed by Alexandros 2026-10-11. Loaded by Director, C# coder, reviewers. Performance rules are in `csharp-performance.md`. Structure comes from here and the plan; the Ponytail ladder only decides how much code goes inside it.

## Create-info structs
- Setup with 3 or more values takes one `<Thing>CreateInfo` struct: public fields, set explicitly, no logic.
- `Thing.Create(in ThingCreateInfo info)` validates the whole struct once and fails there.
- Dependencies arrive through the `CreateInfo`. No singletons, no static state, no `Find` lookups.

```csharp
public struct WaterCreateInfo { public Material material; public int resolution; }
public sealed class Water : System.IDisposable
{
    public static Water Create(in WaterCreateInfo info) { /* validate, allocate */ }
    public void Dispose() { /* release */ }
}
```

## Data structs
- State that travels together is one struct (`<Thing>Data`), not loose variables.
- Methods take at most 3 parameters. More means a struct. Planned check: KIT005.
- Structs over 16 bytes go by `in`. Inputs are `readonly struct` where possible.

## Data and behavior apart
- Data structs hold data. Systems (plain classes) act on it.
- `MonoBehaviour` is a thin adapter: `Create` in `OnEnable`, forward `Update`, `Dispose` in `OnDisable`. No logic in it.

## Ownership
- One owner per resource, `Create`/`Dispose` in pairs, including `NativeArray`, `GraphicsBuffer`, `RenderTexture`. The plan names the owner.

## Failures
- Bad input (null, bad `CreateInfo`): throw in `Create`. Expected runtime failures: return a result enum (like `VkResult`), never an exception.

## Layout
- One folder and one `.asmdef` per feature, runtime and editor apart. Names: `<Thing>CreateInfo`, `<Thing>Data`, `<Thing>System`.

## Reviewer checklist
1. Setup with 3 or more loose arguments that should be a `CreateInfo`?
2. Method with more than 3 parameters?
3. Static state, singleton or hidden dependency?
4. A `Create` without a matching release, or no named owner?
5. Logic inside a `MonoBehaviour` or a data struct?
