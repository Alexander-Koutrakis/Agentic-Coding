"""What a branch changed, read from git. Shared by the Unity file gates.

Two views:
- changed_files(..., worktree=True): committed since the merge-base + staged + unstaged + untracked.
  Everything the task touched; used by the format and scope gates.
- changed_files(..., worktree=False): merge-base vs the index (committed + staged).
  What git will hold after the next commit; used by the asset gate's .meta pairing.

All paths are repo-relative with forward slashes. Agent runtime files under .agent/ are never reported.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from gate_common import GateError

IGNORED_PREFIXES = (".agent/",)


@dataclass(frozen=True)
class Change:
    status: str  # "A" added, "M" modified, "D" deleted, "R" renamed
    path: str  # the new path for a rename
    old_path: str | None = None  # renames only


def git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        raise GateError("git not found on PATH") from None
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)}: {proc.stderr.strip() or f'exit {proc.returncode}'}")
    return proc.stdout


def repo_root(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_dir():
        raise GateError(f"not a folder: {p}")
    return Path(git(p, "rev-parse", "--show-toplevel").strip())


def merge_base(repo: Path, base: str) -> str:
    return git(repo, "merge-base", base, "HEAD").strip()


def _parse_name_status(out: str) -> list[Change]:
    fields = out.split("\0")
    changes: list[Change] = []
    i = 0
    while i < len(fields) and fields[i]:
        code = fields[i][0]
        if code in "RC":
            old, new = fields[i + 1], fields[i + 2]
            i += 3
            changes.append(Change("R", new, old) if code == "R" else Change("A", new))
        else:
            path = fields[i + 1]
            i += 2
            changes.append(Change({"A": "A", "D": "D"}.get(code, "M"), path))
    return changes


def changed_files(repo: Path, base: str, worktree: bool = True) -> list[Change]:
    mb = merge_base(repo, base)
    if worktree:
        changes = _parse_name_status(git(repo, "diff", "--name-status", "-z", "-M", mb))
        untracked = git(repo, "ls-files", "--others", "--exclude-standard", "--full-name", "-z")
        changes += [Change("A", p) for p in untracked.split("\0") if p]
    else:
        changes = _parse_name_status(git(repo, "diff", "--cached", "--name-status", "-z", "-M", mb))
    return [c for c in changes if not c.path.startswith(IGNORED_PREFIXES)]


def index_files(repo: Path, prefix: str) -> set[str]:
    """Paths in the git index under prefix (a repo-relative folder ending in '/')."""
    out = git(repo, "ls-files", "--full-name", "-z", "--", prefix)
    return {p for p in out.split("\0") if p}


def tree_files(repo: Path, rev: str, prefix: str) -> set[str]:
    """Paths tracked at rev under prefix."""
    out = git(repo, "ls-tree", "-r", "--name-only", "--full-name", "-z", rev, "--", prefix)
    return {p for p in out.split("\0") if p}


def read_at(repo: Path, rev: str, path: str) -> str | None:
    """File content at rev, or None if the path does not exist there."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{rev}:{path}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.stdout if proc.returncode == 0 else None
