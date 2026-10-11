"""Scope gate: the branch only changes files its task card allows, and does not delete or weaken tests.

Reads the first ```scope block of the card:

    allow:
      - scripts/unity/**
      - docs/HANDOFF.md
    tests: may-not-change        # or: may-change

Globs are repo-relative; "*" stays inside one folder, "**" crosses folders. A .meta is allowed when its
asset (file or folder) is allowed. Changes under <project>/ProjectSettings/ or <project>/Packages/ always
fail as "needs approval". With tests: may-not-change, a deleted test file, or a test file with fewer test
attributes or Assert calls than at the merge-base, fails.
"""
from __future__ import annotations

import re
from pathlib import Path

from changed_files import Change, changed_files, merge_base, read_at, repo_root
from gate_common import GateError, exit_with, finish, parser, resolve_project
from unity_assemblies import Assemblies

GATE = "scope"
SCOPE_BLOCK = re.compile(r"^```scope[ \t]*\r?\n(.*?)^```", re.S | re.M)
# An attribute right after "[" or "," (so "[Test, Category(..)]" counts twice, "void Test()" not at all).
TEST_ATTR = re.compile(r"[\[,]\s*(?:(?:NUnit\.Framework|UnityEngine\.TestTools)\.)?(?:Test|UnityTest|TestCase|TestCaseSource)(?:Attribute)?\s*(?=[\](,])")
ASSERT = re.compile(r"\bAssert\.")
# Strings are matched (and kept) first so "//" inside a string is not taken for a comment.
CODE_OR_COMMENT = re.compile(
    r'@"(?:""|[^"])*"|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|(?P<comment>//[^\n]*|/\*.*?\*/)', re.S)
CARD_COMMENT = re.compile(r"(?:^|\s)#.*$")


class CardError(Exception):
    pass


def parse_card(text: str) -> tuple[list[str], str]:
    m = SCOPE_BLOCK.search(text)
    if not m:
        raise CardError("card has no scope block")
    allow: list[str] = []
    tests = None
    in_allow = False
    for raw in m.group(1).splitlines():
        line = CARD_COMMENT.sub("", raw).rstrip()  # "# note" is a comment, "docs/C#/x" is not
        if not line.strip():
            continue
        if line.startswith("allow:"):
            if line[len("allow:"):].strip():
                raise CardError("scope block: put each allow glob on its own '  - ' line")
            in_allow = True
        elif line.startswith("tests:"):
            tests = line.split(":", 1)[1].strip()
            in_allow = False
        elif in_allow and line.strip().startswith("- "):
            allow.append(line.strip()[2:].strip().strip("\"'"))
        else:
            raise CardError(f"scope block: unrecognised line '{line.strip()}'")
    if tests not in ("may-change", "may-not-change"):
        raise CardError(f"scope block: tests must be may-change or may-not-change, got '{tests}'")
    return allow, tests


def glob_regex(glob: str) -> re.Pattern[str]:
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out))


class Scope:
    def __init__(self, globs: list[str]):
        self.patterns = [glob_regex(g) for g in globs]

    def _match(self, path: str) -> bool:
        return any(p.fullmatch(path) for p in self.patterns)

    def allows(self, path: str) -> bool:
        if self._match(path):
            return True
        if path.endswith(".meta"):
            asset = path[:-5]
            return self._match(asset) or self._match(f"{asset}/\0")  # file, or folder with allowed contents
        return False


def strip_comments(code: str) -> str:
    return CODE_OR_COMMENT.sub(lambda m: "" if m["comment"] else m[0], code)


def count(text: str) -> tuple[int, int]:
    code = strip_comments(text)
    return len(TEST_ATTR.findall(code)), len(ASSERT.findall(code))


def check_tests(repo: Path, mb: str, tests: Assemblies, changes: list[Change]) -> list[str]:
    problems = []
    for c in changes:
        old = c.old_path or c.path
        if c.status == "A" or not tests.is_test(old):
            continue
        if c.status == "D":
            problems.append(f"test file deleted: {old}")
            continue
        before = read_at(repo, mb, old)
        if before is None:
            continue
        after = (repo / c.path).read_text(encoding="utf-8", errors="replace")
        (attrs_b, asserts_b), (attrs_a, asserts_a) = count(before), count(after)
        if attrs_a < attrs_b:
            problems.append(f"fewer tests in {c.path}: {attrs_b} -> {attrs_a} test attributes")
        if asserts_a < asserts_b:
            problems.append(f"fewer asserts in {c.path}: {asserts_b} -> {asserts_a} Assert calls")
    return problems


def main(argv: list[str] | None = None) -> int:
    p = parser(__doc__.splitlines()[0])
    p.add_argument("--card", required=True, help="task card, relative to the repo root")
    args = p.parse_args(argv)
    repo = repo_root(args.repo)
    project = resolve_project(repo, args.project)
    card = repo / args.card
    if not card.is_file():
        raise GateError(f"task card not found: {args.card}")
    try:
        text = card.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise GateError(f"task card is not UTF-8: {args.card}") from None
    try:
        allow, tests_rule = parse_card(text)
    except CardError as e:
        return finish(repo, GATE, False, str(e), [f"card: {args.card}"])

    scope = Scope(allow)
    changes = changed_files(repo, args.base)
    protected = (f"{project}/ProjectSettings/", f"{project}/Packages/")
    problems: list[str] = []
    for c in changes:
        for path in filter(None, (c.path, c.old_path)):
            if path.startswith(protected):
                problems.append(f"needs approval (ProjectSettings/Packages): {path}")
            elif not scope.allows(path):
                problems.append(f"outside card scope: {path}")
    if tests_rule == "may-not-change":
        mb = merge_base(repo, args.base)
        problems += check_tests(repo, mb, Assemblies(repo, project, mb), changes)

    problems = list(dict.fromkeys(problems))
    if problems:
        return finish(repo, GATE, False, problems[0], problems[1:])
    return finish(repo, GATE, True, f"{len(changes)} changed files in scope, tests {tests_rule}",
                  [f"{c.status} {c.path}" for c in changes])


if __name__ == "__main__":
    exit_with(GATE, main)
