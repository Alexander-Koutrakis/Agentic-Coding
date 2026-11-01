"""Find every user of a symbol in a Unity project with scoped searches (timing review, fx group C).

    find_refs.py --project P Symbol [Symbol ...] [--assets] [--timeout 120]

Code search: every `.cs` under <P>/Assets (Editor, Profiling and test folders included), plain form. The pattern
is the bare word, so `x?.Symbol` is found too. With --assets also a serialized-use search: the GUID of each
`<Symbol>.cs` (when such a file exists) in `*.prefab`, `*.unity`, `*.asset`, and the word itself in
`*.shader`, `*.hlsl`, `*.cginc` for string use. Never searches Library, Logs or the repo root, never without
an include list: the unscoped searches took 134 s to 484 s on a 2.6 GB Assets folder, scoped ones 0 to 16 s.
Uses `rg` when installed, else `grep`. Exit 0 always when the search ran; 2 on a usage error or a timeout.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from changed_files import repo_root
from gate_common import GateError, exit_with, resolve_project

GATE = "find-refs"
ASSET_TYPES = ("prefab", "unity", "asset")
SHADER_TYPES = ("shader", "hlsl", "cginc")


def search(pattern: str, root: Path, types: tuple[str, ...], timeout: int) -> list[str]:
    """Matching lines (path:line:text) for the regex pattern, files limited to the given extensions."""
    globs = [f"*.{t}" for t in types]
    if shutil.which("rg"):
        cmd = ["rg", "-n", "--no-heading", "-e", pattern, str(root)] + [a for g in globs for a in ("-g", g)]
    else:
        cmd = ["grep", "-rnIE", pattern, str(root)] + [f"--include={g}" for g in globs]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace").stdout
    except subprocess.TimeoutExpired:
        raise GateError(f"search timed out after {timeout} s: {pattern}")
    return [line for line in out.splitlines() if line]


def script_guid(assets: Path, symbol: str) -> str | None:
    for meta in assets.rglob(f"{symbol}.cs.meta"):
        m = re.search(r"^guid: ([0-9a-f]{32})", meta.read_text(encoding="utf-8", errors="replace"), re.M)
        if m:
            return m[1]
    return None


def cmd(args, repo: Path, project: str) -> int:
    assets = repo / project / "Assets"
    if not assets.is_dir():
        raise GateError(f"no Assets folder: {assets}")
    for symbol in args.symbols:
        word = rf"\b{re.escape(symbol)}\b"
        code = search(word, assets, ("cs",), args.timeout)
        print(f"== {symbol}: {len(code)} code lines (.cs, all assemblies)")
        for line in code:
            print(f"  {line}")
        if not args.assets:
            continue
        shaders = search(word, assets, SHADER_TYPES, args.timeout)
        print(f"== {symbol}: {len(shaders)} shader lines (.shader, .hlsl, .cginc)")
        for line in shaders:
            print(f"  {line}")
        guid = script_guid(assets, symbol)
        if guid is None:
            print(f"== {symbol}: no {symbol}.cs script file, serialized search skipped (only a script has a GUID)")
            continue
        hits = search(guid, assets, ASSET_TYPES, args.timeout)
        print(f"== {symbol}: {len(hits)} serialized uses (guid {guid}, .prefab .unity .asset)")
        for line in hits:
            print(f"  {line}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("symbols", nargs="+")
    p.add_argument("--repo", default=".", help="path inside the git repo (default: current folder)")
    p.add_argument("--project", required=True, help="Unity project folder, relative to the repo root")
    p.add_argument("--assets", action="store_true", help="also search serialized assets and shaders")
    p.add_argument("--timeout", type=int, default=120, help="seconds per search")
    args = p.parse_args(argv)
    repo = repo_root(args.repo)
    return cmd(args, repo, resolve_project(repo, args.project))


if __name__ == "__main__":
    exit_with(GATE, main)
