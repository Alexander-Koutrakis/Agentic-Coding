"""Docs format gate: a feature brief, implementation plan or task card follows its template.

    uv run --no-project python scripts/core/docs_check.py [--repo .] [--kind feature|plan|card]
        [--allow-placeholders] FILE...

Kind is guessed from the file name (feature.md, implementation-plan.md, task-card.md, docs/tasks/*.md).
Checks structure and consistency only, never quality: headers, required sections, table columns, allowed
values, links between brief, plan and cards, and that a hot-path task has a budget. Template files are
checked with --allow-placeholders (structure only, `<...>` placeholders and unchosen values allowed).

Exit codes as the Unity gates: 0 PASS, 1 FAIL, 2 usage or environment error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unity"))
from gate_common import GateError, exit_with, finish  # noqa: E402
from scope_check import CardError, parse_card  # noqa: E402

GATE = "docs"
TIERS = {"small", "medium", "large"}
CODERS = {"csharp", "shader"}
PROFILES = {"normal", "hot-path"}
VERDICTS = {"pass", "changes", "veto"}
DATE = r"\d{4}-\d{2}-\d{2}"
PLACEHOLDER = re.compile(r"(?<![A-Za-z0-9_])<[A-Za-z][A-Za-z0-9 /_.\-]*>")
NO_DEP = {"", "-", "none", "—"}

FEATURE_SECTIONS = ["Goal", "Systems", "Out of scope", "Constraints and budget", "Acceptance", "Open questions"]
PLAN_SECTIONS = ["Approach", "Data and ownership", "Tasks", "Performance", "Risks", "Review"]
CARD_SECTIONS = ["Goal", "Scope", "Steps", "Acceptance", "Out of scope", "Approvals"]


class Doc:
    def __init__(self, text: str):
        self.text = text
        self.lines = text.splitlines()
        self.h1 = next((ln for ln in self.lines if ln.startswith("# ")), "")
        self.header: list[str] = []
        self.sections: dict[str, list[str]] = {}
        fence, cur = False, None
        for ln in self.lines:
            if ln.startswith("```"):
                fence = not fence
            if not fence and ln.startswith("## "):
                cur = ln[3:].strip()
                self.sections[cur] = []
            elif cur is not None:
                self.sections[cur].append(ln)
            elif not ln.startswith("# "):
                self.header.append(ln)

    def section(self, prefix: str) -> list[str] | None:
        for name, lines in self.sections.items():
            if name.lower().startswith(prefix.lower()):
                return lines
        return None

    def field(self, key: str) -> str | None:
        m = re.search(rf"{key}:[ \t]*([^·\n]*)", "\n".join(self.header))
        return m.group(1).strip().strip("`") if m else None


def table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """First markdown table in `lines`: lowercase header cells and body rows (separator row dropped)."""
    block = [ln.strip() for ln in lines if ln.strip().startswith("|")]
    cells = [[c.strip().strip("`") for c in ln.strip("|").split("|")] for ln in block]
    cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    if not cells:
        return [], []
    return [c.lower() for c in cells[0]], cells[1:]


def col(header: list[str], prefix: str) -> int | None:
    return next((i for i, c in enumerate(header) if c.startswith(prefix)), None)


def cell(row: list[str], i: int | None) -> str:
    return row[i] if i is not None and i < len(row) else ""


def common(d: Doc, kind: str, sections: list[str], tpl: bool) -> list[str]:
    problems = []
    if not re.match(rf"{re.escape('# ' + kind)}\s+\S", d.h1):
        problems.append(f"title must start with '# {kind}' followed by a name")
    for name in sections:
        body = d.section(name)
        if body is None:
            problems.append(f"missing section '## {name}'")
        elif not any(ln.strip() for ln in body):
            problems.append(f"section '{name}' is empty (write 'none' if it does not apply)")
    if not tpl:
        for n, ln in enumerate(d.lines, 1):
            m = PLACEHOLDER.search(ln)
            if m:
                problems.append(f"line {n}: unfilled placeholder {m.group(0)}")
                break
    return problems


def enum_field(d: Doc, key: str, allowed: set[str], tpl: bool) -> list[str]:
    v = d.field(key)
    if v is None:
        return [f"header has no '{key}:'"]
    if not tpl and v not in allowed:
        return [f"{key} must be one of {sorted(allowed)}, got '{v}'"]
    return []


def status(d: Doc, allowed: list[str], tpl: bool) -> tuple[list[str], str]:
    v = d.field("Status")
    if v is None:
        return ["header has no 'Status:'"], ""
    if tpl:
        return [], ""
    m = re.fullmatch(rf"({'|'.join(allowed)})(?: ({DATE}))?\b.*", v)
    if not m:
        return [f"Status must be one of {allowed}, got '{v}'"], ""
    if m.group(1) == "approved" and not m.group(2):
        return ["Status 'approved' needs a date (approved YYYY-MM-DD)"], "approved"
    return [], m.group(1)


def check_feature(d: Doc, repo: Path, tpl: bool) -> list[str]:
    p = common(d, "Feature:", FEATURE_SECTIONS, tpl)
    p += enum_field(d, "Tier", TIERS, tpl)
    p += status(d, ["draft", "approved"], tpl)[0]
    acc = d.section("Acceptance") or []
    if not any(re.match(r"\s*- \[[ xX]\]", ln) for ln in acc):
        p.append("Acceptance needs at least one '- [ ]' line")
    if "```" in d.text:
        p.append("a brief describes systems, not code: remove the code block")
    return p


def plan_tasks(d: Doc) -> dict[str, tuple[str, str]]:
    h, rows = table(d.section("Tasks") or [])
    i, c, pr = col(h, "id"), col(h, "coder"), col(h, "profile")
    return {cell(r, i): (cell(r, c), cell(r, pr)) for r in rows if cell(r, i)}


def check_plan(d: Doc, repo: Path, tpl: bool) -> list[str]:
    p = common(d, "Plan:", PLAN_SECTIONS, tpl)
    p += enum_field(d, "Tier", TIERS, tpl)
    st_problems, st = status(d, ["draft", "reviewed", "approved"], tpl)
    p += st_problems
    brief = d.field("Brief")
    if brief is None:
        p.append("header has no 'Brief:'")
    elif not tpl and not (repo / brief).is_file():
        p.append(f"Brief '{brief}' does not exist")

    approach = [ln for ln in (d.section("Approach") or []) if ln.strip()]
    if len(approach) > 5:
        p.append(f"Approach has {len(approach)} lines, the template allows 5")

    h, rows = table(d.section("Data and ownership") or [])
    t, o = col(h, "type"), col(h, "owner")
    if t is None or o is None:
        p.append("Data and ownership table needs 'Type' and 'Owner' columns")
    elif not tpl:
        if not rows and "none" not in " ".join(d.section("Data and ownership") or []).lower():
            p.append("Data and ownership has no rows (write 'none' if the plan adds no types)")
        p += [f"type '{cell(r, t)}' has no owner" for r in rows if not cell(r, o)]

    h, rows = table(d.section("Tasks") or [])
    ids, cd, pr, dep = col(h, "id"), col(h, "coder"), col(h, "profile"), col(h, "depends")
    if None in (ids, cd, pr, dep) or col(h, "title") is None:
        p.append("Tasks table needs columns ID, Title, Coder, Profile, Depends on")
        return p
    if tpl:
        return p
    if not rows:
        p.append("Tasks table has no rows")
    seen = [cell(r, ids) for r in rows]
    for r in rows:
        tid = cell(r, ids)
        if not tid or seen.count(tid) > 1:
            p.append(f"task ID '{tid}' is empty or duplicated")
        if cell(r, cd) not in CODERS:
            p.append(f"{tid}: Coder must be one of {sorted(CODERS)}, got '{cell(r, cd)}'")
        if cell(r, pr) not in PROFILES:
            p.append(f"{tid}: Profile must be one of {sorted(PROFILES)}, got '{cell(r, pr)}'")
        for dep_id in [x.strip() for x in cell(r, dep).split(",")]:
            if dep_id.lower() not in NO_DEP and (dep_id not in seen or dep_id == tid):
                p.append(f"{tid}: depends on '{dep_id}', which is not another task in this plan")

    p += style_checks(d, rows, cd, pr, repo)
    if any(cell(r, pr) == "hot-path" for r in rows):
        perf = d.section("Performance") or []
        for key in ("Budget", "Harness"):
            if not any(re.match(rf"\s*(?:- )?{key}:[ \t]*\S", ln) for ln in perf):
                p.append(f"a task is hot-path, so Performance needs '{key}:' filled in")
    p += review_checks(d, st)
    return p


def style_checks(d: Doc, rows, cd: int, pr: int, repo: Path) -> list[str]:
    line = next((ln for ln in d.header if ln.startswith("Styles that apply")), "")
    styles = set(re.findall(r"`([^`]+)`", line))
    need = set()
    if any(cell(r, cd) == "csharp" for r in rows):
        need.add("csharp-architecture")
    if any(cell(r, cd) == "csharp" and cell(r, pr) == "hot-path" for r in rows):
        need.add("csharp-performance")
    if any(cell(r, cd) == "shader" for r in rows):
        need.add("shader")
    p = [f"Styles that apply must list `{n}` (a task needs it)" for n in sorted(need - styles)]
    p += [f"style '{s}' has no file skills/style/{s}.md" for s in sorted(styles) if not (repo / "skills" / "style" / f"{s}.md").is_file()]
    return p


def review_checks(d: Doc, st: str) -> list[str]:
    if st not in ("reviewed", "approved"):
        return []
    h, rows = table(d.section("Review") or [])
    lens, verdict = col(h, "reviewer"), col(h, "verdict")
    rows = [r for r in rows if cell(r, lens)]
    p = []
    if not rows:
        p.append(f"Status '{st}' needs at least one review row")
    for r in rows:
        v = cell(r, verdict).split()[0].lower() if cell(r, verdict) else ""
        if v not in VERDICTS:
            p.append(f"review '{cell(r, lens)}' has verdict '{cell(r, verdict)}', expected one of {sorted(VERDICTS)} (delete unused rows)")
        elif v == "veto":
            p.append(f"review '{cell(r, lens)}' vetoed the plan; it cannot be {st}")
    if st == "approved":
        human = re.search(rf"Human approval:\s*(.*)", "\n".join(d.section("Review") or []))
        if not human or not re.search(DATE, human.group(1)):
            p.append("approved plan needs 'Human approval: <name>, <YYYY-MM-DD>'")
    return p


def check_card(d: Doc, repo: Path, tpl: bool) -> list[str]:
    p = common(d, "Task", CARD_SECTIONS, tpl)
    if not tpl and not re.match(r"# Task \d{3}\b", d.h1):
        p.append("title must be '# Task NNN — <title>' with a 3-digit number")
    p += enum_field(d, "Coder", CODERS, tpl)
    p += enum_field(d, "Profile", PROFILES, tpl)
    for key in ("Branch", "Plan"):
        if d.field(key) is None:
            p.append(f"header has no '{key}:'")
    try:
        allow, _ = parse_card(d.text)
        if not allow:
            p.append("scope block has no allow paths")
    except CardError as e:
        p.append(str(e))
    if not any(re.match(r"\s*\d+\. \S", ln) for ln in d.section("Steps") or []) and not tpl:
        p.append("Steps needs at least one numbered step")
    acc = d.section("Acceptance") or []
    if not any(re.match(r"\s*- \[[ xX]\]", ln) for ln in acc):
        p.append("Acceptance needs at least one '- [ ]' line")
    if d.field("Profile") == "hot-path" and not any("budget" in ln.lower() for ln in acc):
        p.append("hot-path task: Acceptance must mention the budget")
    if not tpl:
        p += card_plan_link(d, repo)
    return p


def card_plan_link(d: Doc, repo: Path) -> list[str]:
    m = re.search(r"Plan:\s*`([^`]+)`\s*\(([^)]+)\)", "\n".join(d.header))
    if not m:
        return ["header Plan must look like: Plan: `docs/features/<name>/implementation-plan.md` (T1)"]
    plan_path, tid = repo / m.group(1), m.group(2).strip()
    if not plan_path.is_file():
        return [f"Plan '{m.group(1)}' does not exist"]
    tasks = plan_tasks(Doc(plan_path.read_text(encoding="utf-8")))
    if tid not in tasks:
        return [f"task {tid} is not in the plan's Tasks table"]
    want_coder, want_profile = tasks[tid]
    p = []
    if d.field("Coder") != want_coder:
        p.append(f"Coder is '{d.field('Coder')}' but the plan says '{want_coder}' for {tid}")
    if d.field("Profile") != want_profile:
        p.append(f"Profile is '{d.field('Profile')}' but the plan says '{want_profile}' for {tid}")
    return p


CHECKS = {"feature": check_feature, "plan": check_plan, "card": check_card}


def guess_kind(path: Path) -> str:
    if path.name == "feature.md":
        return "feature"
    if path.name == "implementation-plan.md":
        return "plan"
    if path.name == "task-card.md" or path.parent.name == "tasks":
        return "card"
    raise GateError(f"cannot tell the kind of {path.name}; pass --kind feature|plan|card")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", help="documents to check, relative to --repo")
    ap.add_argument("--repo", default=".", help="repo root (default: current folder)")
    ap.add_argument("--kind", choices=sorted(CHECKS), help="force the kind for all files")
    ap.add_argument("--allow-placeholders", action="store_true", help="check a template: structure only")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    problems: list[str] = []
    for name in a.files:
        path = repo / name
        if not path.is_file():
            raise GateError(f"no such file: {name}")
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raise GateError(f"{name} is not UTF-8") from None
        kind = a.kind or guess_kind(path)
        problems += [f"{name}: {m}" for m in CHECKS[kind](Doc(text), repo, a.allow_placeholders)]
    ok = not problems
    return finish(repo, GATE, ok, f"{len(a.files)} files" if ok else problems[0], problems[1:])


if __name__ == "__main__":
    exit_with(GATE, main)
