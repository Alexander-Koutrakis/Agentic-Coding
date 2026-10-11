# C# performance style (main thread, plain C#)

v1. Loaded only for tasks tagged `profile: hot-path`, plus the performance reviewer. Structure rules stay in `csharp-architecture.md`.

## When it applies
- Only code that runs per frame or over many items, and only with a budget in the card.
- Measure with the perf harness before and after. If the gain is not measurable, keep the simple version.

## Allocation
- Allocate in `Create`, reuse every frame (`Clear()` lists, reuse arrays).
- None per frame: LINQ, closures that capture, string building, boxing, `new` of classes.
- Cache lookups in `Create` (`GetComponent`, `Camera.main`, `transform`). Never per frame.

## Data layout (cache locality)
- Arrays of structs, not lists of class objects. Loop by index, front to back.
- A loop that reads one or two fields of many items: one array per field (struct of arrays). Keep hot fields together and cold data elsewhere.
- No managed references inside hot structs.
- No dictionary lookup per item per frame. Store the index or handle instead.

## Branching
- Hoist conditions that do not change out of the loop.
- Sort or partition items once by type or state, then run one tight loop per group, instead of a branch per item.
- No virtual or interface calls in tight loops. Use an enum in the data and a `switch`, or one array per type.
- Cheap early-out checks first. Branch-free math (`Mathf.Min`/`Max`, arithmetic select) only where measured.
- Skip work when nothing changed (dirty flag).

## Reviewer checklist
1. Is the task tagged hot-path with a budget, and is there a before/after measurement?
2. Any per-frame allocation or uncached lookup?
3. Any list of objects or per-item dictionary lookup in a hot loop?
4. Any per-item branch that grouping or hoisting would remove?
