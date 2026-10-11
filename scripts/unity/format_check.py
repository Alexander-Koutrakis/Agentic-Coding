"""Format gate: changed .cs files under <project>/Assets follow the project's .editorconfig (whitespace rules).

Runs `dotnet format whitespace <project>/Assets --folder --verify-no-changes --include <files>`.
The workspace is Assets/, not the project root: the root also holds Library/PackageCache
(thousands of .cs files), which made one run 9.1 s instead of 1.3 s. --folder mode does not load
the Unity-generated .sln, so it needs no restore and no Unity DLLs.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from changed_files import changed_files, repo_root
from gate_common import GateError, exit_with, finish, parser, resolve_project

GATE = "format"
CHUNK = 50  # files per dotnet call, keeps the command line short
PROBLEM = re.compile(r"^(?P<file>.+?)\((?P<pos>\d+,\d+)\): (?P<rest>(?:error|warning) .*?)(?: \[[^\]]*\])?$")


def sdk_available(dotnet: str | None) -> bool:
    if not dotnet:
        return False
    try:
        proc = subprocess.run([dotnet, "format", "--version"], capture_output=True, text=True)
    except OSError:
        return False
    return proc.returncode == 0


def _relative(repo: Path, file: str) -> str:
    try:
        return Path(file).resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return file


def main(argv: list[str] | None = None) -> int:
    p = parser(__doc__.splitlines()[0])
    p.add_argument("--dotnet", default=None, help="dotnet executable (default: dotnet on PATH)")
    args = p.parse_args(argv)
    repo = repo_root(args.repo)
    project = resolve_project(repo, args.project)
    assets = repo / project / "Assets"
    prefix = f"{project}/Assets/"

    files = sorted(
        c.path for c in changed_files(repo, args.base)
        if c.status != "D" and c.path.startswith(prefix) and c.path.endswith(".cs")
    )
    if not files:
        return finish(repo, GATE, True, "0 files", [])

    dotnet = args.dotnet or shutil.which("dotnet")
    if not sdk_available(dotnet):
        return finish(repo, GATE, False, "no .NET SDK (dotnet format unavailable)", [f"dotnet: {dotnet}"])

    problems: list[str] = []
    for i in range(0, len(files), CHUNK):
        include = [f[len(prefix):] for f in files[i:i + CHUNK]]
        cmd = [dotnet, "format", "whitespace", str(assets), "--folder", "--verify-no-changes", "--include", *include]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        output = (proc.stdout + proc.stderr).splitlines()
        if proc.returncode not in (0, 2):
            first = next((line for line in output if line.strip()), f"exit {proc.returncode}")
            raise GateError(f"dotnet format failed: {first.strip()}")
        found_before = len(problems)
        for line in output:
            m = PROBLEM.match(line.strip())
            if m:
                problems.append(f"{_relative(repo, m['file'])}({m['pos']}): {m['rest']}")
        if proc.returncode == 2 and len(problems) == found_before:
            problems.append(f"dotnet format reported changes in: {', '.join(include)}")

    if problems:
        return finish(repo, GATE, False, problems[0], problems[1:])
    return finish(repo, GATE, True, f"{len(files)} files", files)


if __name__ == "__main__":
    exit_with(GATE, main)
