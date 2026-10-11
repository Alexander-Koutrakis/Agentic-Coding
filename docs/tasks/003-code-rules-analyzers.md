# Task 003 — Code rules and Roslyn analyzers

Branch: `task/003-code-rules-analyzers` (stacked on `task/002-cheap-gates`) · Project: `Test Enviroments/Unity Agentic Kit test/` · Plan: §4.5, "before done" tier
Pipeline: implementer → `unity-check` → reviewer (fresh context, checks the diff against this card) → report to Alexandros.

## Goal
Two gates that catch Unity-specific mistakes the compiler accepts:
- **Part A, code rules:** a Python file gate (`scripts/unity/code_rules.py`) for project rules no analyzer covers:
  - `UnityEditor` used in runtime code,
  - scene searches, `SendMessage` and LINQ in per-frame methods,
  - leftover `Debug.Log`.
  
  It runs in `unity-check` step 0, after scope. It reports **new** violations only, so old code does not block a task.
- **Part B, analyzers:** [Microsoft.Unity.Analyzers](https://github.com/microsoft/Microsoft.Unity.Analyzers) (`UNT0001`–`UNT0046`) runs inside Unity's own compile. Severities are set in the project's `.editorconfig`. Correctness and type-safety rules are `error`, so the existing compile + console gate fails on them with no new gate logic. Performance rules are `warning` and are reported.

Do Part A first: it needs no approvals. Part B starts with a probe (B1) whose result decides where the DLL goes and how severities are set.

## Prerequisites
- Task 002 merged, or this branch stays stacked on it.
- **Part B only:** Alexandros approves, in chat, downloading `microsoft.unity.analyzers.1.28.0.nupkg` from `https://www.nuget.org/api/v2/package/Microsoft.Unity.Analyzers/1.28.0` (164.76 KB, published by Microsoft, MIT). Ask at step B1, with the name, source and size. Do not use the copy bundled with Visual Studio (`...\Visual Studio Tools for Unity\Analyzers\Microsoft.Unity.Analyzers.dll`): its version follows the IDE install and is not in git.

## Scope
```scope
allow:
  - scripts/unity/**
  - skills/unity/unity-check/SKILL.md
  - Test Enviroments/Unity Agentic Kit test/.editorconfig
  - Test Enviroments/Unity Agentic Kit test/Assets/Kit/Analyzers/**
  - Test Enviroments/Unity Agentic Kit test/Assets/Default.ruleset
  - docs/tasks/003-code-rules-analyzers.md
  - docs/HANDOFF.md
  - docs/IMPLEMENTATION_PLAN.md
  - CLAUDE.md
tests: may-not-change
```
`Assets/Default.ruleset` is only allowed as the B1 fallback. Temporary probe scripts (B1, acceptance) must be gone before the gate runs. The scope gate would flag any that are left.

## Part A — code rules (`scripts/unity/code_rules.py`)

### A1. Shared assembly lookup
- Move the "which assembly owns this file" logic out of `scope_check.TestFiles` into `scripts/unity/unity_assemblies.py`. That covers the nearest `.asmdef` going up from the file, looked up on disk and at the merge-base, with BOM-safe JSON. Add:
  - `is_test(path)`: today's rule.
  - `is_editor_only(path)`: the owning `.asmdef` has `includePlatforms == ["Editor"]`. With no `.asmdef`, any folder part named `Editor` below `Assets/` counts (Unity's predefined `Assembly-CSharp-Editor`).
- `scope_check` uses the new module. Its 61 tests must still pass unchanged.

### A2. Rules
They apply to changed `.cs` files under `Assets/` that are **not** test code. Comments and strings are removed first (reuse `strip_comments`, but keep line numbers).

| ID | Rule | Applies to |
|---|---|---|
| KIT001 | `UnityEditor` (`using UnityEditor`, `UnityEditor.` qualified names) outside an `#if UNITY_EDITOR` region | runtime code (not editor-only) |
| KIT002 | Inside `Update`/`LateUpdate`/`FixedUpdate`/`OnGUI`: `GameObject.Find*`, `FindObjectOfType(s)`, `FindFirstObjectByType`, `FindAnyObjectByType`, `FindObjectsByType`, `SendMessage`, `BroadcastMessage` | all non-test code |
| KIT003 | Inside the same methods: LINQ calls (`.Where(`, `.Select(`, `.Any(`, `.All(`, `.First(`, `.FirstOrDefault(`, `.Last(`, `.OrderBy(`, `.ToList(`, `.ToArray(`, `.Count(`, `.Sum(`) in a file with `using System.Linq` | all non-test code |
| KIT004 | `Debug.Log(` / `Debug.LogFormat(` (not `LogWarning`/`LogError`/`LogException`) | runtime code |

- **`#if` tracking (KIT001):**
  - A line is editor-guarded if one of the `#if`/`#elif` branches it sits in has a condition containing `UNITY_EDITOR` that is not negated (`!UNITY_EDITOR`).
  - `#else` of such a branch is **not** guarded.
  - Nesting must work.
- **Method bodies (KIT002/003):**
  - Find `void Update(`, `void LateUpdate(`, `void FixedUpdate(` and `void OnGUI(` with any modifiers.
  - Take the body by matching braces on the comment- and string-free text.
  - Expression bodies (`=>`) run to the next `;`.
- **Suppression:** `// kit-allow KIT00N: <reason>` on the same line or the line above. A reason is required; without one, the comment does not suppress. Suppressed hits are counted in the PASS summary so the reviewer can check them.
- **New violations only:** for each file and rule, count the hits now and at the merge-base (use the old path for renames). FAIL if the count went up, and list the current hits of that rule in that file. New files compare against 0.

### A3. Output and wiring
- Same conventions as Task 002 (`gate_common`): one line, at most 10 details, `.agent/logs/code-rules.txt`, and exit codes 0/1/2.
  - PASS example: `PASS code-rules: 3 files, 0 new violations, 1 suppressed`.
  - FAIL example: `FAIL code-rules: <path>(12,9): KIT004 Debug.Log left in runtime code`.
- `unity-check` step 0 gets a 4th command after scope. The PASS line gains `code-rules ok`.

### A4. Tests (`scripts/unity/tests/test_code_rules.py`, fixtures as in Task 002)
- Each rule, with PASS and FAIL cases.
- KIT001: `#if UNITY_EDITOR` guarded (PASS), `#else` branch (FAIL), `#if !UNITY_EDITOR` (FAIL), nested `#if UNITY_EDITOR && DEBUG` (PASS), an editor-only asmdef (PASS), an `Editor/` folder with no asmdef (PASS), and a runtime asmdef (FAIL).
- KIT002/003: a call in `Update` (FAIL), the same call in `Start` (PASS), an expression-bodied `Update` (FAIL), the call inside a comment or string (PASS), and LINQ without `using System.Linq` (PASS).
- Suppression with a reason (PASS, counted), and without a reason (FAIL).
- A violation already present at the merge-base (PASS), one more of the same (FAIL), and a renamed file keeping its old violations (PASS).
- Test code is skipped.

## Part B — Roslyn analyzers

### B1. Probe (stop and report if it does not work)
1. Ask for the download approval (see Prerequisites).
2. Download into `.agent/downloads/unity-analyzers-1.28.0/`, a new empty folder (gitignored). Run `dotnet nuget verify <nupkg>`; it must report a valid Microsoft signature.
3. Extract only `analyzers/dotnet/cs/Microsoft.Unity.Analyzers.dll` with Python `zipfile` (`python -I`).
4. Copy the DLL to `Assets/Kit/Analyzers/` (a folder with **no** `.asmdef`). Refresh, and let Unity create the `.meta`.
5. Through the Editor (UnityMCP `execute_code` or a menu tool, **never** by editing the `.meta`):
   - `PluginImporter`: `SetCompatibleWithAnyPlatform(false)`, `SetCompatibleWithEditor(false)`, and every standalone target off;
   - `AssetDatabase.SetLabels(dll, new[] { "RoslynAnalyzer" })`;
   - `SaveAndReimport()`.
6. In `.editorconfig` (project root), set `dotnet_diagnostic.UNT0010.severity = error`. Create two temporary probes, each `public class XProbe : MonoBehaviour { void Update() { } void M() { var p = new XProbe(); } }`:
   - one in `Assets/Kit/Spike/Runtime/` (assembly `Kit.Spike`, a custom `.asmdef`);
   - one in `Assets/Kit/` (predefined `Assembly-CSharp`).
7. Run `unity-wait-ready` and read the console (errors, warnings and logs). Record per probe:
   - whether `UNT0010` shows as **error** (the `.editorconfig` severity applies);
   - whether `UNT0001` (empty Unity message) shows, and at what level (the default severity);
   - any `CS8032` or "analyzer could not be loaded" warning.
8. Remove both probes **through the Editor** (`delete_script` or `AssetDatabase.DeleteAsset`, so the `.meta` goes too). Refresh, and confirm the console is clean.

Decide from the evidence, and write the decision in the handoff:
- **DLL location:**
  - If both probes fire, keep `Assets/Kit/Analyzers/`.
  - If only `Assembly-CSharp` fires, the Unity docs are right that the scope is predefined assemblies only (the two manual pages disagree). Then try `Assets/` root; if custom asmdefs are still not covered, report BLOCKED with the evidence. Do not add the DLL to every asmdef folder.
- **Severity source:**
  - If `.editorconfig` works, use it.
  - If not, use `Assets/Default.ruleset`, the documented way for all assemblies, and note why.

### B2. Severities (`.editorconfig`, `[*.cs]` section, one line per ID, grouped with a comment)
- **error**, for correctness and type safety:
  - `UNT0003`, `UNT0004`, `UNT0006`–`UNT0016`,
  - `UNT0020`, `UNT0023`, `UNT0025`, `UNT0027`,
  - `UNT0029`–`UNT0031`, `UNT0033`, `UNT0040`, `UNT0043`.
- **warning**, for performance:
  - `UNT0001`, `UNT0002`, `UNT0017`–`UNT0019`,
  - `UNT0022`, `UNT0024`, `UNT0026`, `UNT0028`,
  - `UNT0032`, `UNT0036`–`UNT0038`, `UNT0041`, `UNT0042`, `UNT0044`–`UNT0046`.
- **Left at the default:**
  - `UNT0005` (retired),
  - `UNT0021` (opt-in style),
  - `UNT0034`/`UNT0035` (readability),
  - `UNT0039` (design advice).
  
  The reviewer may question any of these.
- Check the IDs against the 1.28.0 `doc/index.md` before writing them.

### B3. Gate wiring
- `unity-check` step 2 needs no change: a `UNT` error is a compile error.
- Step 3 lists `UNT` warnings on their own line (`analyzer warnings: N`). In v1 they do not fail the gate (decision below).
- **New check in step 2:** any `CS8032` / "analyzer could not be loaded" message means **FAIL analyzers: not loaded**. A gate that silently stops analyzing must not pass.
- The PASS line gains `analyzers on (N warnings)`.

## Decisions taken in this card (Alexandros can override at review)
1. **Performance warnings do not fail the gate in v1.**
   - Turning them into errors would block compiling the whole project over legacy code.
   - Failing only on warnings in changed files needs console parsing matched against `changed_files`, a good follow-up once we see how noisy they are.
2. **Code rules flag new violations only**, the same idea as the test-weakening check. Old code never blocks a task.
3. **One analyzer package.** No ErrorProne.NET or other analyzers until this one has run for a while.

## Acceptance (the reviewer checks each one)
1. `uv run --no-project --with pytest pytest scripts/unity/tests -q` passes, with the Task 002 tests unchanged. Paste the summary.
2. `code_rules.py` on this branch: PASS, exit 0. Paste the line.
3. The B1 probe evidence is pasted into the handoff: per probe, the console lines seen, plus the location and severity-source decisions.
4. Full `unity-check` on this branch, with this card: PASS, including `code-rules ok` and `analyzers on (N warnings)`, with no `CS8032`. The Spike canary still passes 3/3 and `asset_check` passes with the DLL and its `.meta`.
5. **Live negative runs**, each reverted, re-run and PASS, with both result lines pasted:
   - (a) `Debug.Log("x");` added to `SpikeMath.Lerp01` gives `FAIL code-rules: ... KIT004`, before compile. Revert with the Edit tool, not `sed`.
   - (b) a temporary `Assets/Kit/Spike/Runtime/AnalyzerProbe.cs` with `new AnalyzerProbe()` on a `MonoBehaviour` gives `FAIL compile: ... error UNT0010 ...`. Delete it through the Editor.
6. The file gates together (4 scripts) still finish in under 15 s.
7. Nothing in `Library/`, `Temp/`, `Logs/`, `UserSettings/`, `ProjectSettings/` or `Packages/` changed. The only new `.meta` files are the DLL's and `Assets/Kit/Analyzers.meta`, both created by Unity. The DLL's `.meta` shows the label and the platform settings, set through the Editor.

## Out of scope
Failing on performance warnings, other analyzer packages, PlayMode tests, `ProjectSettings` "warnings as errors", player builds, analyzers in the IDE (they already work there), and a custom analyzer of our own.

## Approvals
- The NuGet download (B1), asked in chat with the file name, source and size. Without a yes, finish Part A and report Part B as BLOCKED: waiting for approval.
- Anything outside the scope block: stop and ask.
- Give up after 3 failed gate loops on the same problem, and report `BLOCKED` with the evidence.
- Do not push or merge (D14).

## Done means
The acceptance evidence is in the handoff. The plan §4.5 rows for **Analyzers** and **Code rules** say `built`. HANDOFF "Current state" and "Next step" are updated. Everything is committed on `task/003-code-rules-analyzers`.
