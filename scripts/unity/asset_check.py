"""Asset integrity gate: every asset under <project>/Assets has a .meta, no orphan .meta, no duplicate GUIDs,
and changed assets are staged/committed together with their .meta.

Disk check: the whole Assets/ tree. Git check: merge-base vs the index (committed + staged), so an asset
committed or staged without its .meta fails even while the .meta sits untracked on disk (Spike 001, friction #9).
Names Unity itself skips are skipped: hidden (".x"), ending in "~", "cvs", "*.tmp".
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from changed_files import changed_files, index_files, repo_root
from gate_common import exit_with, finish, parser, resolve_project

GATE = "assets"
GUID = re.compile(r"^guid:\s*([0-9a-fA-F]{32})\s*$", re.M)


def unity_ignores(name: str) -> bool:
    low = name.lower()
    return name.startswith(".") or name.endswith("~") or low == "cvs" or low.endswith(".tmp")


def check_disk(repo: Path, project: str) -> tuple[list[str], int, int]:
    """Return (problems, asset count, meta count) for the Assets tree on disk."""
    assets_dir = repo / project / "Assets"
    problems: list[str] = []
    guids: dict[str, str] = {}
    n_assets = n_metas = 0
    for dirpath, dirnames, filenames in os.walk(assets_dir):
        dirnames[:] = sorted(d for d in dirnames if not unity_ignores(d))
        here = Path(dirpath)
        rel_dir = here.relative_to(repo).as_posix()
        metas = {f for f in filenames if f.endswith(".meta") and not unity_ignores(f)}
        items = (set(dirnames) | {f for f in filenames if not unity_ignores(f)}) - metas
        n_assets += len(items)
        n_metas += len(metas)
        for name in sorted(items):
            if f"{name}.meta" not in metas:
                problems.append(f"missing .meta: {rel_dir}/{name}")
        for meta in sorted(metas):
            rel = f"{rel_dir}/{meta}"
            if meta[:-5] not in items:
                problems.append(f"orphan .meta: {rel}")
            m = GUID.search((here / meta).read_text(encoding="utf-8", errors="replace"))
            if not m:
                problems.append(f"bad guid line: {rel}")
                continue
            guid = m.group(1).lower()
            if guid in guids:
                problems.append(f"duplicate guid {guid}: {guids[guid]} and {rel}")
            else:
                guids[guid] = rel
    return problems, n_assets, n_metas


def check_git(repo: Path, project: str, base: str) -> tuple[list[str], int]:
    """Check .meta pairing for paths changed between the merge-base and the index."""
    prefix = f"{project}/Assets/"
    index = index_files(repo, prefix)
    index_dirs = {p.rsplit("/", i)[0] for p in index for i in range(1, p.count("/") + 1)}

    def in_index(asset: str) -> bool:  # a file, or a folder with files in it
        return asset in index or asset in index_dirs

    def skipped(path: str) -> bool:
        return any(unity_ignores(part) for part in path[len(prefix):].split("/"))

    added: set[str] = set()
    removed: set[str] = set()
    for c in changed_files(repo, base, worktree=False):
        if c.status == "R":
            added.add(c.path)
            removed.add(c.old_path)
        elif c.status == "A":
            added.add(c.path)
        elif c.status == "D":
            removed.add(c.path)

    problems: list[str] = []
    for path in sorted(added):
        if not path.startswith(prefix) or skipped(path):
            continue
        if path.endswith(".meta"):
            if not in_index(path[:-5]):
                problems.append(f"staged .meta without its asset: {path}")
            continue
        if f"{path}.meta" not in index:
            problems.append(f"staged without its .meta: {path}")
        folder = path.rsplit("/", 1)[0]
        while len(folder) > len(prefix) - 1:
            if f"{folder}.meta" not in index:
                problems.append(f"folder staged without its .meta: {folder}")
            folder = folder.rsplit("/", 1)[0]
    for path in sorted(removed):
        if not path.startswith(prefix) or skipped(path) or path in added:
            continue
        if path.endswith(".meta"):
            if in_index(path[:-5]):
                problems.append(f".meta removed but asset still staged: {path}")
        elif not in_index(path) and f"{path}.meta" in index:
            problems.append(f"removed but its .meta is still staged: {path}")
    return list(dict.fromkeys(problems)), sum(p.startswith(prefix) for p in added | removed)


def main(argv: list[str] | None = None) -> int:
    args = parser(__doc__.splitlines()[0]).parse_args(argv)
    repo = repo_root(args.repo)
    project = resolve_project(repo, args.project)
    disk, n_assets, n_metas = check_disk(repo, project)
    staged, n_changed = check_git(repo, project, args.base)
    problems = disk + staged
    if problems:
        return finish(repo, GATE, False, problems[0], problems[1:])
    return finish(repo, GATE, True, f"{n_assets} assets, {n_metas} .meta, {n_changed} changed in git", [])


if __name__ == "__main__":
    exit_with(GATE, main)
