"""Write the project-owned kit files into a target Unity repo (a plugin cannot ship them).

    python init_project.py --target PATH [--name NAME] [--unity-project REL] [--no-canary]

Writes CLAUDE.md, .gitattributes, docs/HANDOFF.md, logs/friction-log.md from the kit's templates/project/, and
the canary (templates/unity-canary/ -> <unity project>/Assets/Kit/Canary/: a tiny assembly with 3 EditMode tests, so
the first `unity-check` has tests to run and a known-good PASS). --no-canary skips it. Unity creates the .meta files
when the Editor refreshes; commit them with the canary.
Never overwrites: a file that already exists is reported as SKIPPED and left alone.
--unity-project defaults to the one folder under the target that holds Assets/ and ProjectSettings/.
Exit 0 ok, 2 bad input. Next step it prints: run setup_git.py once in the target.
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]


def find_unity_project(target: Path) -> str | None:
    found = [p.parent for p in target.glob("**/ProjectSettings/ProjectVersion.txt") if (p.parent.parent / "Assets").is_dir()]
    found = [p for p in found if "Library" not in p.parts]
    if len(found) != 1:
        return None
    return found[0].parent.relative_to(target).as_posix() or "."


def fill(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def attributes_text(kit: Path = KIT) -> str:
    return (kit / ".gitattributes").read_text(encoding="utf-8")


def plan(kit: Path, values: dict[str, str], canary: bool = False) -> list[tuple[str, str]]:
    tpl = kit / "templates" / "project"
    read = lambda name: fill((tpl / name).read_text(encoding="utf-8"), values)  # noqa: E731
    files = [
        ("CLAUDE.md", read("CLAUDE.md")),
        (".gitattributes", attributes_text(kit)),
        ("docs/HANDOFF.md", read("HANDOFF.md")),
        ("logs/friction-log.md", read("friction-log.md")),
    ]
    if canary:
        src = kit / "templates" / "unity-canary"
        root = f"{values['unity_project']}/Assets/Kit/Canary".removeprefix("./")
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            files.append((f"{root}/{path.relative_to(src).as_posix()}", path.read_text(encoding="utf-8")))
    return files


def main(argv: list[str] | None = None, kit: Path = KIT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", required=True)
    parser.add_argument("--name")
    parser.add_argument("--unity-project")
    parser.add_argument("--no-canary", action="store_true", help="do not install the canary test assembly")
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    if not (target / ".git").exists():
        print(f"FAIL init: not a git repo root: {target}")
        return 2
    unity = args.unity_project or find_unity_project(target)
    if unity is None or not (target / unity / "Assets").is_dir():
        print("FAIL init: could not find exactly one Unity project; pass --unity-project <folder relative to the repo root>")
        return 2
    values = {"name": args.name or target.name, "unity_project": unity, "date": datetime.date.today().isoformat()}

    written, skipped = [], []
    for rel, text in plan(kit, values, canary=not args.no_canary):
        path = target / rel
        if path.exists():
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(rel)
    print(f"PASS init: wrote {len(written)} ({', '.join(written) or '-'}); SKIPPED existing {len(skipped)} ({', '.join(skipped) or '-'}); unity project '{unity}'")
    if any("/Canary/" in rel or rel.startswith("Assets/Kit/Canary") for rel in written):
        print("Canary written without .meta files: open the project in Unity (it creates them), then commit the canary with its .meta files.")
    print(f"Next, in the target: python \"{(kit / 'scripts/core/setup_git.py').as_posix()}\" --repo .")
    return 0


if __name__ == "__main__":
    sys.exit(main())
