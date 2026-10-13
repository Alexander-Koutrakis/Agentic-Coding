"""One-time git setup for a Unity repo on this machine: Git LFS hooks and the UnityYAMLMerge driver.

`.gitattributes` names the driver (`merge=unityyamlmerge`) but git keeps the driver's command in config,
which is per machine, so it cannot be committed. Run this once per clone. The driver is
`unity_merge.py`, a wrapper around UnityYAMLMerge (git's temp files lack the extension it needs).

    python scripts/core/setup_git.py            # configure the repo this script lives in
    python scripts/core/setup_git.py --check    # report only, change nothing
    python scripts/core/setup_git.py --repo PATH --yaml-merge PATH_TO_UnityYAMLMerge

Without --yaml-merge it looks at $UNITY_YAML_MERGE, then at the Unity Hub install folders, newest first.
Exit 0 ok, 1 something is missing, 2 bad input.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DRIVER = "unityyamlmerge"
TOOL = "UnityYAMLMerge.exe" if os.name == "nt" else "UnityYAMLMerge"
HUB_ROOTS = (
    Path("C:/Program Files/Unity/Hub/Editor"),
    Path("/Applications/Unity/Hub/Editor"),
    Path.home() / "Unity/Hub/Editor",
)


def find_yaml_merge(roots: tuple[Path, ...] = HUB_ROOTS, env: dict | None = None) -> Path | None:
    env = os.environ if env is None else env
    explicit = env.get("UNITY_YAML_MERGE")
    if explicit:
        return Path(explicit) if Path(explicit).is_file() else None
    candidates = []
    for root in roots:
        if root.is_dir():
            for editor in root.iterdir():
                for sub in ("Editor/Data/Tools", "Unity.app/Contents/Tools"):
                    exe = editor / sub / TOOL
                    if exe.is_file():
                        candidates.append((editor.name, exe))
    return max(candidates)[1] if candidates else None  # newest folder name sorts last


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def driver_command(exe: Path) -> str:
    wrapper = Path(__file__).resolve().with_name("unity_merge.py")
    return f'"{Path(sys.executable).as_posix()}" "{wrapper.as_posix()}" "{exe.as_posix()}" %O %B %A %P'


def configured_driver(repo: Path) -> str:
    return git(repo, "config", "--get", f"merge.{DRIVER}.driver", check=False)


def lfs_installed(repo: Path) -> bool:
    return git(repo, "config", "--get", "filter.lfs.process", check=False) != ""


def check(repo: Path, exe: Path | None) -> list[str]:
    """Problems found; empty means the machine is set up."""
    problems = []
    if not lfs_installed(repo):
        problems.append("git lfs is not installed for this repo (run without --check)")
    current = configured_driver(repo)
    if not current:
        problems.append(f"merge driver '{DRIVER}' is not configured")
    elif exe is not None and current != driver_command(exe):
        problems.append(f"merge driver '{DRIVER}' points elsewhere: {current}")
    return problems


def apply(repo: Path, exe: Path) -> None:
    subprocess.run(["git", "-C", str(repo), "lfs", "install", "--local"], check=True, capture_output=True)
    git(repo, "config", "--local", f"merge.{DRIVER}.name", "Unity YAML merge")
    git(repo, "config", "--local", f"merge.{DRIVER}.driver", driver_command(exe))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--yaml-merge", help="path to UnityYAMLMerge")
    parser.add_argument("--check", action="store_true", help="report only, change nothing")
    args = parser.parse_args(argv)

    repo = Path(args.repo)
    if not (repo / ".git").exists():
        print(f"FAIL setup_git: not a git repo root: {repo}")
        return 2
    exe = Path(args.yaml_merge) if args.yaml_merge else find_yaml_merge()
    if exe is not None and not exe.is_file():
        print(f"FAIL setup_git: UnityYAMLMerge not found at {exe}")
        return 2
    if exe is None:
        print("FAIL setup_git: UnityYAMLMerge not found; pass --yaml-merge or set UNITY_YAML_MERGE")
        return 1

    if not args.check:
        apply(repo, exe)
    problems = check(repo, exe)
    if problems:
        print("FAIL setup_git: " + "; ".join(problems))
        return 1
    print(f"PASS setup_git: lfs on, merge driver '{DRIVER}' -> {exe.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
