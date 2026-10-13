"""Write the project-owned kit files into a target Unity repo (a plugin cannot ship them).

    python init_project.py --target PATH [--name NAME] [--unity-project REL]

Writes CLAUDE.md, .gitattributes, docs/HANDOFF.md, logs/friction-log.md from the kit's templates/project/.
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


def plan(kit: Path, values: dict[str, str]) -> list[tuple[str, str]]:
    tpl = kit / "templates" / "project"
    read = lambda name: fill((tpl / name).read_text(encoding="utf-8"), values)  # noqa: E731
    return [
        ("CLAUDE.md", read("CLAUDE.md")),
        (".gitattributes", attributes_text(kit)),
        ("docs/HANDOFF.md", read("HANDOFF.md")),
        ("logs/friction-log.md", read("friction-log.md")),
    ]


def main(argv: list[str] | None = None, kit: Path = KIT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", required=True)
    parser.add_argument("--name")
    parser.add_argument("--unity-project")
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
    for rel, text in plan(kit, values):
        path = target / rel
        if path.exists():
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(rel)
    print(f"PASS init: wrote {len(written)} ({', '.join(written) or '-'}); SKIPPED existing {len(skipped)} ({', '.join(skipped) or '-'}); unity project '{unity}'")
    print(f"Next, in the target: python \"{(kit / 'scripts/core/setup_git.py').as_posix()}\" --repo .")
    return 0


if __name__ == "__main__":
    sys.exit(main())
