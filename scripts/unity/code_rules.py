"""Code-rules gate: Unity mistakes the compiler accepts, in changed non-test .cs files under Assets/.

  KIT001  UnityEditor in runtime code, outside an `#if UNITY_EDITOR` region
  KIT002  scene searches, SendMessage and BroadcastMessage inside Update/LateUpdate/FixedUpdate/OnGUI
  KIT003  LINQ calls inside those methods, in a file with `using System.Linq`
  KIT004  Debug.Log / Debug.LogFormat in runtime code

Only new violations fail: per file and rule, the hits now are compared with the hits at the merge-base
(the old path for a renamed file; a new file compares against 0). Suppress a hit with
`// kit-allow KIT00N: <reason>` on the same line, or alone on the line above; without a reason it does
not suppress. Comments and strings are blanked before matching, keeping line and column positions.
"""
from __future__ import annotations

import re
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from changed_files import Change, changed_files, merge_base, read_at, repo_root
from gate_common import exit_with, finish, parser, resolve_base, resolve_project
from scope_check import CODE_OR_COMMENT
from unity_assemblies import Assemblies

GATE = "code-rules"
EDITOR = "UNITY_EDITOR"
EDITOR_ONLY_SYMBOLS = ("UNITY_EDITOR_WIN", "UNITY_EDITOR_OSX", "UNITY_EDITOR_LINUX", "UNITY_EDITOR_64")  # imply UNITY_EDITOR

# A preprocessor line (kept apart: it is not code) or, as in scope_check, a string, char or comment.
SOURCE = re.compile(rf"(?P<directive>^[ \t]*#[^\n]*)|{CODE_OR_COMMENT.pattern}", re.S | re.M)
KIT_ALLOW = re.compile(r"^//\s*kit-allow\s+(?P<ids>KIT\d{3}(?:\s*,\s*KIT\d{3})*)\s*:\s*(?P<why>\S.*)$")

UNITY_EDITOR_REF = re.compile(r"(?<![\w.])UnityEditor\b")
DEBUG_LOG = re.compile(r"(?<!\w)Debug\s*\.\s*Log(?:Format)?\s*\(")
PER_FRAME = re.compile(r"\bvoid\s+(?P<name>Update|LateUpdate|FixedUpdate|OnGUI)\s*\(")
USING_LINQ = re.compile(r"\busing\s+(?:static\s+)?System\s*\.\s*Linq(?:\s*\.\s*Enumerable)?\s*;")
KIT002_CALL = re.compile(
    r"\bGameObject\s*\.\s*Find\w*\s*\("
    r"|\bFind(?:ObjectsOfType|ObjectOfType|FirstObjectByType|AnyObjectByType|ObjectsByType)\s*(?:<[^;()]*>\s*)?\("
    r"|\b(?:SendMessage|SendMessageUpwards|BroadcastMessage)\s*\(")
KIT003_CALL = re.compile(
    r"\.\s*(?:Where|Select|Any|All|First|FirstOrDefault|Last|OrderBy|ToList|ToArray|Count|Sum)\s*\(")


@dataclass(frozen=True)
class Hit:
    rule: str
    line: int
    col: int
    message: str
    suppressed: bool = False


# --- source preparation ------------------------------------------------------------------------------------

class Source:
    """A .cs file with comments, strings and preprocessor lines blanked, positions unchanged."""

    def __init__(self, text: str):
        self.directives: dict[int, str] = {}  # line -> directive text without its trailing comment
        self.comments: dict[int, str] = {}  # line -> the // comment on it
        self.starts = [0] + [i + 1 for i, ch in enumerate(text) if ch == "\n"]

        def blank(m: re.Match[str]) -> str:
            line = self.line_of(m.start())
            if m["directive"] is not None:
                self.directives[line] = re.sub(r"//.*", "", m[0]).strip()
            elif m["comment"] is not None and m["comment"].startswith("//"):
                self.comments[line] = m["comment"].rstrip()
            return re.sub(r"[^\r\n]", " ", m[0])  # strings, chars, comments, directives: same length, same lines

        self.code = SOURCE.sub(blank, text)
        self.lines = self.code.split("\n")

    def line_of(self, offset: int) -> int:
        return bisect_right(self.starts, offset)

    def position(self, offset: int) -> tuple[int, int]:
        line = self.line_of(offset)
        return line, offset - self.starts[line - 1] + 1


# --- #if tracking (KIT001) ---------------------------------------------------------------------------------

TOKEN = re.compile(r"\s*(?:(?P<op>\(|\)|!|&&|\|\|)|(?P<sym>[A-Za-z_]\w*))")


def parse_condition(cond: str):
    """Boolean expression of symbols, ! && || and parentheses -> tuple tree; None if it does not parse."""
    tokens, pos = [], 0
    cond = cond.strip()
    while pos < len(cond):
        m = TOKEN.match(cond, pos)
        if not m:
            return None
        tokens.append(m["op"] or m["sym"])
        pos = m.end()
    i = 0

    def peek():
        return tokens[i] if i < len(tokens) else None

    def eat():
        nonlocal i
        i += 1
        return tokens[i - 1]

    def p_or():
        node = p_and()
        while peek() == "||":
            eat()
            node = ("or", node, p_and())
        return node

    def p_and():
        node = p_not()
        while peek() == "&&":
            eat()
            node = ("and", node, p_not())
        return node

    def p_not():
        t = peek()
        if t == "!":
            eat()
            return ("not", p_not())
        if t == "(":
            eat()
            node = p_or()
            if peek() != ")":
                raise ValueError
            eat()
            return node
        if t is None or t in (")", "&&", "||"):
            raise ValueError
        eat()
        return ("const", t == "true") if t in ("true", "false") else ("sym", t)

    try:
        node = p_or()
    except ValueError:
        return None
    return node if i == len(tokens) else None


def symbols(node, out: set[str]) -> set[str]:
    if node[0] == "sym":
        out.add(node[1])
    elif node[0] in ("not", "and", "or"):
        for child in node[1:]:
            symbols(child, out)
    return out


def evaluate(node, env: dict[str, bool]) -> bool:
    kind = node[0]
    if kind == "const":
        return node[1]
    if kind == "sym":
        return env[node[1]]
    if kind == "not":
        return not evaluate(node[1], env)
    left = evaluate(node[1], env)
    right = evaluate(node[2], env)
    return (left and right) if kind == "and" else (left or right)


def implies_editor(node) -> bool:
    """True if the branch can only run when UNITY_EDITOR is defined."""
    off = {EDITOR, *EDITOR_ONLY_SYMBOLS}  # all false when the Editor is not the compiler
    others = sorted(symbols(node, set()) - off)
    if len(others) > 12:
        return False
    return not any(evaluate(node, {**dict.fromkeys(off, False), **dict(zip(others, values))})
                   for values in product([False, True], repeat=len(others)))


class IfFrame:
    """One #if ... #endif: the conditions of the branches so far, and whether the current one is editor-only."""

    def __init__(self, cond: str):
        self.earlier: list = []  # trees of the branch conditions already passed; None entries are unknown
        self.guarded = False
        self.branch(cond)

    def branch(self, cond: str | None) -> None:
        """Enter the #if/#elif branch with this condition, or the #else branch when cond is None."""
        tree = parse_condition(cond) if cond is not None else None
        if cond is not None and tree is None:  # does not parse: the literal rule, and later branches are unknown
            self.guarded = bool(re.search(rf"(?<!!)\b{EDITOR}\b", cond))
            self.earlier.append(None)
            return
        if None in self.earlier:
            self.guarded = False
        else:
            tree_here = tree
            for before in self.earlier:
                negated = ("not", before)
                tree_here = negated if tree_here is None else ("and", negated, tree_here)
            if tree_here is None:  # a bare #if with nothing before and no condition cannot happen
                tree_here = ("const", False)
            self.guarded = implies_editor(tree_here)
        if tree is not None:
            self.earlier.append(tree)


def editor_guarded_lines(src: Source) -> set[int]:
    """Lines that sit inside a branch which only runs when UNITY_EDITOR is defined (nesting included)."""
    guarded: set[int] = set()
    stack: list[IfFrame] = []
    for number in range(1, len(src.lines) + 1):
        directive = src.directives.get(number)
        if directive:
            m = re.match(r"#\s*(if|elif|else|endif)\b(.*)$", directive)
            if m:
                word, rest = m[1], m[2]
                if word == "if":
                    stack.append(IfFrame(rest))
                elif word == "elif" and stack:
                    stack[-1].branch(rest)
                elif word == "else" and stack:
                    stack[-1].branch(None)
                elif word == "endif" and stack:
                    stack.pop()
            continue
        if any(f.guarded for f in stack):
            guarded.add(number)
    return guarded


# --- rules ---------------------------------------------------------------------------------------------------

def per_frame_bodies(code: str):
    """(method name, start, end) of each body of Update, LateUpdate, FixedUpdate and OnGUI."""
    for m in PER_FRAME.finditer(code):
        i, depth = m.end(), 1
        while i < len(code) and depth:
            depth += {"(": 1, ")": -1}.get(code[i], 0)
            i += 1
        while i < len(code) and code[i].isspace():
            i += 1
        if code.startswith("{", i):
            start, depth = i, 0
            while i < len(code):
                depth += {"{": 1, "}": -1}.get(code[i], 0)
                i += 1
                if depth == 0:
                    break
            yield m["name"], start, i
        elif code.startswith("=>", i):
            end = code.find(";", i)
            yield m["name"], i, len(code) if end < 0 else end


def suppressed_rules(src: Source, line: int) -> set[str]:
    """Rules switched off for this line by a kit-allow comment (with a reason) on it or alone above it."""
    allowed: set[str] = set()
    for number in (line, line - 1):
        comment = src.comments.get(number)
        if comment is None or (number == line - 1 and src.lines[number - 1].strip()):
            continue  # the line above only counts when the comment is all there is on it
        m = KIT_ALLOW.match(comment)
        if m:
            allowed |= {r.strip() for r in m["ids"].split(",")}
    return allowed


def find_hits(text: str, editor_only: bool) -> list[Hit]:
    src = Source(text.lstrip("﻿"))
    raw: list[tuple[str, int, str]] = []  # rule, offset, message

    if not editor_only:
        guarded = editor_guarded_lines(src)
        for m in UNITY_EDITOR_REF.finditer(src.code):
            if src.line_of(m.start()) not in guarded:
                raw.append(("KIT001", m.start(), "UnityEditor in runtime code (wrap it in #if UNITY_EDITOR)"))
        for m in DEBUG_LOG.finditer(src.code):
            raw.append(("KIT004", m.start(), "Debug.Log left in runtime code"))

    has_linq = bool(USING_LINQ.search(src.code))
    for name, start, end in per_frame_bodies(src.code):
        for m in KIT002_CALL.finditer(src.code, start, end):
            call = re.sub(r"\s+", "", m[0]).rstrip("(")
            raw.append(("KIT002", m.start(), f"{call} in {name}() (per-frame code)"))
        if has_linq:
            for m in KIT003_CALL.finditer(src.code, start, end):
                call = re.sub(r"\s+", "", m[0]).rstrip("(")
                raw.append(("KIT003", m.start(), f"LINQ {call}() in {name}() (allocates every frame)"))

    hits = []
    for rule, offset, message in sorted(raw, key=lambda r: r[1]):
        line, col = src.position(offset)
        hits.append(Hit(rule, line, col, message, rule in suppressed_rules(src, line)))
    return hits


# --- gate ------------------------------------------------------------------------------------------------------

def counts(hits: list[Hit]) -> Counter[str]:
    return Counter(h.rule for h in hits if not h.suppressed)


def check_file(repo: Path, mb: str, asm: Assemblies, c: Change) -> tuple[list[str], int]:
    """(problems, suppressed hits) for one changed file."""
    old_path = c.old_path or c.path
    before_text = None if c.status == "A" else read_at(repo, mb, old_path)
    # Editor-only is judged separately for each side. The old text by where it lived at the merge-base, so
    # moving editor code into runtime shows its violations as new. The new text by the .asmdef on disk, and
    # for a file that already existed also by its place at the merge-base, so flipping an .asmdef or moving
    # a file in the same diff does not hide anything. A brand-new file trusts the disk (a new editor assembly
    # adds its .asmdef and files together).
    editor_now = asm.is_editor_only(c.path)
    editor_before = False
    if before_text is not None:
        editor_before = asm.is_editor_only(old_path, "base")
        editor_now = editor_now and editor_before
    now = find_hits((repo / c.path).read_text(encoding="utf-8", errors="replace"), editor_now)
    before = counts(find_hits(before_text, editor_before)) if before_text is not None else Counter()
    now_counts = counts(now)
    problems = []
    for rule in sorted(now_counts):
        if now_counts[rule] > before[rule]:
            problems += [f"{c.path}({h.line},{h.col}): {h.rule} {h.message}"
                         for h in now if h.rule == rule and not h.suppressed]
    return problems, sum(h.suppressed for h in now)


def main(argv: list[str] | None = None) -> int:
    p = parser(__doc__.splitlines()[0])
    args = p.parse_args(argv)
    repo = repo_root(args.repo)
    args.base = resolve_base(repo, args.base)
    project = resolve_project(repo, args.project)
    mb = merge_base(repo, args.base)
    asm = Assemblies(repo, project, mb)

    files = [c for c in changed_files(repo, args.base)
             if c.status != "D" and c.path.endswith(".cs") and c.path.startswith(f"{project}/Assets/")
             and not asm.is_test(c.path)]
    problems: list[str] = []
    suppressed = 0
    for c in files:
        found, skipped = check_file(repo, mb, asm, c)
        problems += found
        suppressed += skipped
    if problems:
        return finish(repo, GATE, False, problems[0], problems[1:])
    return finish(repo, GATE, True, f"{len(files)} files, 0 new violations, {suppressed} suppressed",
                  [c.path for c in files])


if __name__ == "__main__":
    exit_with(GATE, main)
