"""Shared plumbing for the Unity file gates: arguments, one-line output, log file, exit codes.

Exit codes: 0 PASS, 1 FAIL, 2 usage or environment error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

MAX_DETAILS = 10
BASE_FILE = ".agent/task-base"  # two lines: card, rev; written by file_gates.py begin; one task at a time (D5)
DEFAULT_BASE = "main"


class GateError(Exception):
    """The gate cannot run (bad path, not a git repo, missing tool). Exit 2."""


def parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--repo", default=".", help="path inside the git repo (default: current folder)")
    p.add_argument("--project", required=True, help="Unity project folder, relative to the repo root")
    p.add_argument("--base", default=None,
                   help=f"revision the change is compared against (default: the rev recorded by "
                        f"file_gates.py begin in {BASE_FILE}, else {DEFAULT_BASE})")
    return p


def read_task_base(repo: Path) -> tuple[str, str] | None:
    """(card, rev) recorded by `file_gates.py begin`, or None."""
    f = repo / BASE_FILE
    if not f.is_file():
        return None
    lines = f.read_text(encoding="utf-8").splitlines()
    return (lines[0], lines[1]) if len(lines) >= 2 and lines[0] and lines[1] else None


def write_task_base(repo: Path, card: str, rev: str) -> None:
    f = repo / BASE_FILE
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f"{card}\n{rev}\n", encoding="utf-8")


def resolve_base(repo: Path, explicit: str | None) -> str:
    """One base for every gate: --base, else the recorded task base, else main."""
    if explicit:
        return explicit
    recorded = read_task_base(repo)
    return recorded[1] if recorded else DEFAULT_BASE


def resolve_project(repo: Path, project: str) -> str:
    """Return the project path as repo-relative posix, checking it has an Assets folder.

    Resolved against the real file system, so "./X", an absolute path or a different letter case on
    Windows give the same prefix as git's paths. A prefix that does not match would make every gate
    see zero changed files and PASS silently.
    """
    path = (repo / project).resolve()
    try:
        rel = path.relative_to(repo.resolve()).as_posix()
    except ValueError:
        raise GateError(f"project '{project}' is outside the repo {repo}") from None
    if rel == "." or not (path / "Assets").is_dir():
        raise GateError(f"no Assets folder in project '{project}' (repo {repo})")
    return rel


def finish(repo: Path, gate: str, ok: bool, summary: str, details: list[str]) -> int:
    """Print the result line and up to MAX_DETAILS details; write everything to .agent/logs/<gate>.txt."""
    line = f"{'PASS' if ok else 'FAIL'} {gate}: {summary}"
    log = repo / ".agent" / "logs" / f"{gate}.txt"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join([line, *details]) + "\n", encoding="utf-8")
    print(line)
    shown = details if len(details) <= MAX_DETAILS else details[:MAX_DETAILS - 1]
    for d in shown:
        print(f"  {d}")
    if len(shown) < len(details):
        print(f"  ... {len(details) - len(shown)} more in .agent/logs/{gate}.txt")
    return 0 if ok else 1


def run(gate: str, main: Callable[[list[str] | None], int], argv: list[str] | None = None) -> int:
    """Run a gate's main, turning GateError into exit 2 with one ERROR line."""
    try:
        return main(argv)
    except GateError as e:
        print(f"ERROR {gate}: {e}")
        return 2


def exit_with(gate: str, main: Callable[[list[str] | None], int]) -> None:
    sys.exit(run(gate, main))
