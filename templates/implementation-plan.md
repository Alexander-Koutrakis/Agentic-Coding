# Plan: <feature name>

Brief: `docs/features/<name>/feature.md` · Tier: small | medium | large
Status: draft | reviewed | approved <date> · Written by the Director.
Styles that apply: `csharp-architecture` [, `csharp-performance`] [, `shader`]

## Approach
Five lines at most: the design in words, and why this one. Reuse before new code (Ponytail ladder).

## Data and ownership
| Type | Kind | Fields / purpose | Owner (creates and releases) |
|---|---|---|---|
| `<Thing>CreateInfo` | create-info | | |
| `<Thing>Data` | data | | |
| `<Thing>` | system | | |

## Tasks
Each row becomes a task card in `docs/tasks/`. One independently testable unit per task.
| ID | Title | Coder (`csharp`/`shader`) | Profile (`normal`/`hot-path`) | Depends on |
|---|---|---|---|---|
| T1 | | | | |

## Performance (only if any task is `hot-path` or the feature is graphics)
- Budget: copied from the brief.
- Harness: scene, camera, resolution, warmup, measured frames, feature ON vs OFF.
- Baseline: <none yet | link>

## Risks
- <risk> → <what we do about it>

## Review
| Reviewer lens | Verdict (pass / changes / veto) | Findings |
|---|---|---|
| architecture and style | | |
| performance and GC | | |
| unnecessary scope | | |

Human approval: <name, date>
