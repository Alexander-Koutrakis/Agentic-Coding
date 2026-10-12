"""Run the Unity file gates as one command and compose the final PASS line.

    file_gates.py begin  --project P --card C    record the task's base (HEAD now) and card
    file_gates.py run    --project P [--card C]  format, assets, scope, code-rules; stops at the first failure
    file_gates.py finish --project P --editor "18/18 EditMode (Asm)" --errors 0 --warnings 0
                                                 PASS line = file gates (verified current) + Editor results

Every gate compares against the same base: --base, else the rev `begin` recorded, else main (T1-8, T1-12).
`finish` refuses if files changed since `run` (fingerprint of HEAD, base and every changed file), so the file
part of the PASS line is never a claim. The Editor part (compile, console, tests) stays with UnityMCP (D11);
`finish` only checks it is consistent (tests passed == total > 0, no errors).

Exit codes: 0 PASS, 1 FAIL, 2 usage or environment error.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from contextlib import redirect_stdout
from pathlib import Path

import asset_check
import code_rules
import format_check
import scope_check
from changed_files import changed_files, git, repo_root
from gate_common import GateError, exit_with, read_task_base, resolve_base, resolve_project, write_task_base

GATE = "file-gates"
STATE = ".agent/logs/file-gates.json"
EDITOR = re.compile(r"^(\d+)/(\d+)\b")


def run_one(module, repo: Path, project: str, base: str, extra: list[str]) -> tuple[int, str]:
    argv = ["--repo", str(repo), "--project", project, "--base", base, *extra]
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = module.main(argv)
    return code, buf.getvalue()


def fingerprint(repo: Path, base: str) -> str:
    h = hashlib.sha256()
    h.update(git(repo, "rev-parse", "HEAD").encode())
    h.update(git(repo, "rev-parse", base).encode())
    for c in sorted(changed_files(repo, base), key=lambda c: c.path):
        h.update(f"{c.status}\0{c.path}\0".encode())
        f = repo / c.path
        if c.status != "D" and f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()


def pick_card(repo: Path, card: str | None) -> str | None:
    recorded = read_task_base(repo)
    if card and recorded and recorded[0] != card:
        raise GateError(f"base was recorded for {recorded[0]}, not {card}: run 'begin --card {card}' first")
    return card or (recorded[0] if recorded else None)


def cmd_begin(args, repo: Path, project: str) -> int:
    if not (repo / args.card).is_file():
        raise GateError(f"task card not found: {args.card}")
    rev = git(repo, "rev-parse", "HEAD").strip()
    write_task_base(repo, args.card, rev)
    dirty = [c.path for c in changed_files(repo, rev)]
    print(f"BEGIN {args.card}: base {rev[:7]}")
    if dirty:
        print(f"  WARNING: {len(dirty)} uncommitted changes will count as this task's (scope will flag them): {dirty[0]}")
    return 0


def cmd_run(args, repo: Path, project: str) -> int:
    base = resolve_base(repo, args.base)
    card = pick_card(repo, args.card)
    gates = [
        ("format", format_check, []),
        ("assets", asset_check, []),
        ("scope", scope_check, ["--card", card] if card else None),
        ("code-rules", code_rules, []),
    ]
    parts: list[str] = []
    for name, module, extra in gates:
        if extra is None:
            parts.append("scope: no card")
            continue
        code, out = run_one(module, repo, project, base, extra)
        if code != 0:
            print(out, end="")
            return code
        summary = out.splitlines()[0].split(": ", 1)[1]
        parts.append(f"{name} ok ({summary})")
    line = ", ".join(parts)
    state = {"base": base, "card": card, "line": line, "fingerprint": fingerprint(repo, base)}
    (repo / STATE).parent.mkdir(parents=True, exist_ok=True)
    (repo / STATE).write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"PASS {GATE}: {line}, base {base[:7]}")
    return 0


def cmd_finish(args, repo: Path, project: str) -> int:
    f = repo / STATE
    if not f.is_file():
        raise GateError("no file-gate result: run 'file_gates.py run' first")
    state = json.loads(f.read_text(encoding="utf-8"))
    if fingerprint(repo, state["base"]) != state["fingerprint"]:
        print("FAIL stale: files changed since the file gates ran; run 'file_gates.py run' again")
        return 1
    m = EDITOR.match(args.editor)
    if not m:
        raise GateError(f"--editor must start with passed/total, e.g. '18/18 EditMode (Asm)', got '{args.editor}'")
    passed, total = int(m[1]), int(m[2])
    if total == 0:
        print("FAIL tests: 0 tests ran (wrong assembly name, or tests did not compile)")
        return 1
    if passed != total:
        print(f"FAIL tests {passed}/{total}: {args.editor}")
        return 1
    if args.errors:
        print(f"FAIL console: {args.errors} errors")
        return 1
    print(f"PASS {args.editor}, {state['line']}, analyzer warnings {args.analyzer_warnings}, "
          f"{args.errors} errors, {args.warnings} warnings")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("begin", "run", "finish"):
        s = sub.add_parser(name)
        s.add_argument("--repo", default=".", help="path inside the git repo (default: current folder)")
        s.add_argument("--project", required=True, help="Unity project folder, relative to the repo root")
        if name != "finish":
            s.add_argument("--card", required=name == "begin", help="task card, relative to the repo root")
        if name == "run":
            s.add_argument("--base", default=None, help="override the recorded base (default: recorded, else main)")
        if name == "finish":
            s.add_argument("--editor", required=True, help='tests from the Editor, e.g. "18/18 EditMode (Kit.Spike.Tests.EditMode)"')
            s.add_argument("--errors", type=int, required=True, help="console errors after the run")
            s.add_argument("--warnings", type=int, required=True, help="console warnings after the run")
            s.add_argument("--analyzer-warnings", type=int, default=0)
    args = p.parse_args(argv)
    repo = repo_root(args.repo)
    project = resolve_project(repo, args.project)
    return {"begin": cmd_begin, "run": cmd_run, "finish": cmd_finish}[args.cmd](args, repo, project)


if __name__ == "__main__":
    exit_with(GATE, main)
