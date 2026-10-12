# Friction log

A mistake or friction that happened. Seen twice becomes a script, a code-rules check, a hook or a template line (plan principle 3). Reviewers append here; the Director reads it before writing a plan.

Older numbered frictions (#1-#11) are in `docs/spikes/001-unity-loop.md`.

| # | Date | What happened | Seen | Fixed by (script / rule / template) |
|---|---|---|---|---|
| T1-1 | 2026-10-12 | Trial 001, Director: `templates/implementation-plan.md` has no place for the Ponytail cuts, and `docs_check` limits Approach to 5 lines, so the cuts list failed the check. Added a `## Ponytail ladder: what was cut` section; the check accepted it. | 1 | Template line: add an optional "Cuts" section to `templates/implementation-plan.md` (proposed) |
| T1-2 | 2026-10-12 | Trial 001, Director: a "brief acceptance coverage" table in the plan was parsed by `docs_check` as a second Tasks table (11 false errors). Rewritten as a list. | 1 | Proposal: `docs_check` should read only the table under `## Tasks`; or the template should name a coverage format |
| T1-3 | 2026-10-12 | Trial 001, Director: wrote `Budget (from the brief):`; `docs_check` wants the literal `Budget:`. The template text itself shows `Budget: copied from the brief.` | 1 | Proposal: `docs_check` accepts a parenthesis after the key, or the error message names the exact key |
| T1-4 | 2026-10-12 | Trial 001, Architect/Director: the approved brief lists a scene component that hands blades to a renderer feature. `csharp-architecture` bans static state, singletons and `Find`, so the component cannot reach the feature. The Architect brief should not fix mechanisms that the style guide rules out. Director cut the component and flagged it for the human. | 1 | Architect role file: "check each system in the brief against `csharp-architecture` before asking for approval" (proposed) |
| T1-5 | 2026-10-12 | Trial 001: a Bash heredoc holding a long Python script with apostrophes failed (`unexpected EOF`) on this Windows shell. Wrote the script to the scratchpad with the Write tool instead. | 1 | Note in CLAUDE.md or a skill: write multi-line scripts with the file tool, not inline heredocs |
