import io
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "unity"))

import docs_check  # noqa: E402
import gate_common  # noqa: E402

REPO = Path(__file__).resolve().parents[3]

FEATURE = """# Feature: Water ripples

Tier: medium · Status: approved 2026-10-11 · Owner: Alexandros

## Goal
Ripples appear where the player touches water.

## Systems
- Input: reports touch points.

## Out of scope
- Boats.

## Constraints and budget
- Budget: 0.4 ms GPU at 1080p.

## Acceptance
- [ ] A touch makes a ripple.

## Open questions
- none
"""

PLAN = """# Plan: Water ripples

Brief: `docs/features/water/feature.md` · Tier: medium
Status: {status} · Written by the Director.
Styles that apply: `csharp-architecture`, `csharp-performance`, `shader`

## Approach
Ripples live in a height texture updated per frame.

## Data and ownership
| Type | Kind | Fields / purpose | Owner |
|---|---|---|---|
| `RippleCreateInfo` | create-info | resolution | RippleSystem |

## Tasks
| ID | Title | Coder | Profile | Depends on |
|---|---|---|---|---|
| T1 | Ripple system | csharp | hot-path | - |
| T2 | Ripple shader | shader | normal | T1 |

## Performance
- Budget: 0.4 ms GPU at 1080p
- Harness: fixed scene, ON vs OFF

## Risks
- none

## Review
| Reviewer lens | Verdict | Findings |
|---|---|---|
| architecture and style | pass | |

Human approval: Alexandros, 2026-10-11
"""

CARD = """# Task 004 — Ripple system

Branch: `task/004-ripple` · Project: `Game/` · Plan: `docs/features/water/implementation-plan.md` (T1)
Coder: csharp · Profile: hot-path
Status: todo

## Goal
Ripple system exists.

## Scope

```scope
allow:
  - Game/Assets/Ripples/**
tests: may-not-change
```

## Steps
1. Write it.

## Acceptance
- [ ] unity-check PASS
- [ ] budget 0.4 ms met

## Out of scope
- shader

## Approvals
none
"""


@pytest.fixture
def repo(tmp_path):
    for s in ("csharp-architecture", "csharp-performance", "shader"):
        (tmp_path / "skills" / "style").mkdir(parents=True, exist_ok=True)
        (tmp_path / "skills" / "style" / f"{s}.md").write_text("x")
    (tmp_path / "docs" / "features" / "water").mkdir(parents=True)
    (tmp_path / "docs" / "tasks").mkdir(parents=True)
    write(tmp_path, "docs/features/water/feature.md", FEATURE)
    write(tmp_path, "docs/features/water/implementation-plan.md", PLAN.format(status="approved 2026-10-11"))
    write(tmp_path, "docs/tasks/004-ripple.md", CARD)
    return tmp_path


def write(root, rel, text):
    (root / rel).write_text(text, encoding="utf-8")


def run(repo, *files, extra=()):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = gate_common.run(docs_check.GATE, docs_check.main, ["--repo", str(repo), *extra, *files])
    return code, buf.getvalue()


def edit(repo, rel, old, new):
    path = repo / rel
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


BRIEF, PLAN_PATH, CARD_PATH = (
    "docs/features/water/feature.md",
    "docs/features/water/implementation-plan.md",
    "docs/tasks/004-ripple.md",
)


def test_valid_documents_pass(repo):
    code, out = run(repo, BRIEF, PLAN_PATH, CARD_PATH)
    assert code == 0, out
    assert out.startswith("PASS docs: 3 files")


def test_real_templates_pass_structure_check():
    code, out = run(REPO, "templates/feature.md", "templates/implementation-plan.md", "templates/task-card.md",
                    extra=["--allow-placeholders"])
    assert code == 0, out


def test_real_templates_fail_without_the_flag():
    code, out = run(REPO, "templates/feature.md")
    assert code == 1
    assert out.startswith("FAIL docs: ")


def test_unknown_file_name_is_exit_2(repo):
    write(repo, "notes.md", "# x\n")
    code, out = run(repo, "notes.md")
    assert code == 2
    assert out.startswith("ERROR docs: ")


def test_missing_file_is_exit_2(repo):
    assert run(repo, "docs/nope/feature.md")[0] == 2


@pytest.mark.parametrize("old,new,expect", [
    ("Tier: medium", "Tier: huge", "Tier must be one of"),
    ("Status: approved 2026-10-11", "Status: approved", "needs a date"),
    ("## Out of scope\n- Boats.\n", "", "missing section '## Out of scope'"),
    ("- [ ] A touch makes a ripple.", "A touch makes a ripple.", "at least one '- [ ]'"),
    ("Ripples appear", "Ripples <thing> appear", "unfilled placeholder <thing>"),
    ("## Systems\n- Input: reports touch points.", "## Systems\n```cs\nclass A {}\n```", "not code"),
    ("## Open questions\n- none\n", "## Open questions\n", "section 'Open questions' is empty"),
])
def test_feature_failures(repo, old, new, expect):
    edit(repo, BRIEF, old, new)
    code, out = run(repo, BRIEF)
    assert code == 1
    assert expect in out


@pytest.mark.parametrize("old,new,expect", [
    ("| T2 | Ripple shader | shader | normal | T1 |", "| T2 | Ripple shader | artist | normal | T1 |", "Coder must be one of"),
    ("| shader | normal | T1 |", "| shader | fast | T1 |", "Profile must be one of"),
    ("| shader | normal | T1 |", "| shader | normal | T9 |", "depends on 'T9'"),
    ("| shader | normal | T1 |", "| shader | normal | T2 |", "depends on 'T2'"),
    ("| T2 | Ripple shader", "| T1 | Ripple shader", "duplicated"),
    ("| RippleSystem |", "| |", "has no owner"),
    ("`csharp-performance`, ", "", "must list `csharp-performance`"),
    (", `shader`", "", "must list `shader`"),
    ("`shader`", "`shader`, `water-magic`", "no file skills/style/water-magic.md"),
    ("- Budget: 0.4 ms GPU at 1080p\n", "- Budget:\n", "needs 'Budget:'"),
    ("- Harness: fixed scene, ON vs OFF\n", "", "needs 'Harness:'"),
    ("| pass |", "| veto |", "vetoed"),
    ("| pass |", "| |", "has verdict ''"),
    ("Human approval: Alexandros, 2026-10-11", "Human approval: Alexandros", "needs 'Human approval"),
    ("Brief: `docs/features/water/feature.md`", "Brief: `docs/features/air/feature.md`", "does not exist"),
])
def test_plan_failures(repo, old, new, expect):
    edit(repo, PLAN_PATH, old, new)
    code, out = run(repo, PLAN_PATH)
    assert code == 1
    assert expect in out


def test_plan_approach_longer_than_five_lines_fails(repo):
    edit(repo, PLAN_PATH, "Ripples live in a height texture updated per frame.", "\n".join(f"line {i}" for i in range(6)))
    assert "Approach has 6 lines" in run(repo, PLAN_PATH)[1]


def test_draft_plan_needs_no_review(repo):
    edit(repo, PLAN_PATH, "approved 2026-10-11 ·", "draft ·")
    edit(repo, PLAN_PATH, "| pass |", "| |")
    code, out = run(repo, PLAN_PATH)
    assert code == 0, out


def test_plan_with_no_new_types_may_say_none(repo):
    edit(repo, PLAN_PATH, "| `RippleCreateInfo` | create-info | resolution | RippleSystem |\n", "")
    assert run(repo, PLAN_PATH)[0] == 1
    edit(repo, PLAN_PATH, "## Data and ownership\n", "## Data and ownership\nnone\n")
    assert run(repo, PLAN_PATH)[0] == 0


@pytest.mark.parametrize("old,new,expect", [
    ("Coder: csharp", "Coder: shader", "plan says 'csharp'"),
    ("Profile: hot-path", "Profile: normal", "plan says 'hot-path'"),
    ("(T1)", "(T7)", "task T7 is not in the plan"),
    ("`docs/features/water/implementation-plan.md` (T1)", "`docs/features/x/y.md` (T1)", "does not exist"),
    ("# Task 004", "# Task 4", "3-digit number"),
    ("Coder: csharp · ", "", "header has no 'Coder:'"),
    ("```scope\nallow:\n  - Game/Assets/Ripples/**\ntests: may-not-change\n```", "", "no scope block"),
    ("  - Game/Assets/Ripples/**\n", "", "no allow paths"),
    ("1. Write it.", "Write it.", "numbered step"),
    ("- [ ] budget 0.4 ms met", "- [ ] works", "must mention the budget"),
    ("- [ ] unity-check PASS\n- [ ] budget 0.4 ms met", "unity-check PASS, budget 0.4 ms met", "at least one '- [ ]'"),
    ("## Approvals\nnone\n", "", "missing section '## Approvals'"),
])
def test_card_failures(repo, old, new, expect):
    edit(repo, CARD_PATH, old, new)
    code, out = run(repo, CARD_PATH)
    assert code == 1
    assert expect in out


def test_old_format_card_fails_missing_coder(repo):
    shutil.copy(REPO / "docs/tasks/003-code-rules-analyzers.md", repo / "docs/tasks/003-old.md")
    code, out = run(repo, "docs/tasks/003-old.md")
    assert code == 1
    assert "'Coder:'" in out


def test_all_problems_reach_the_log_but_output_is_capped(repo):
    edit(repo, PLAN_PATH, "| T2 | Ripple shader | shader | normal | T1 |", "| T2 | x | a | b | T9 |")
    code, out = run(repo, PLAN_PATH)
    assert code == 1
    assert len(out.splitlines()) <= 1 + gate_common.MAX_DETAILS
    assert (repo / ".agent" / "logs" / "docs.txt").read_text(encoding="utf-8").startswith("FAIL docs")


def test_utf8_bom_and_crlf_are_accepted(repo):
    text = (repo / BRIEF).read_text(encoding="utf-8").replace("\n", "\r\n")
    (repo / BRIEF).write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    code, out = run(repo, BRIEF)
    assert code == 0, out
