"""Fixtures: a throwaway git repo with a fake Unity project (folder name with a space, like the real one).

Negative cases for the asset gate exist only here: never break .meta files in the real test project.
"""
from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT = "Game Project"


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.assets = f"{PROJECT}/Assets"

    def git(self, *args: str) -> str:
        proc = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True)
        return proc.stdout

    def write(self, rel: str, text: str = "") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def meta(self, rel: str, guid: str | None = None) -> Path:
        return self.write(f"{rel}.meta", f"fileFormatVersion: 2\nguid: {guid or uuid.uuid4().hex}\n")

    def asset(self, rel_in_assets: str, text: str = "", meta: bool = True) -> str:
        """Write Assets/<rel> (+ .meta), and .meta files for any new folders on the way."""
        rel = f"{self.assets}/{rel_in_assets}"
        parts = rel_in_assets.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            folder = f"{self.assets}/{'/'.join(parts[:i])}"
            if not (self.root / f"{folder}.meta").exists():
                (self.root / folder).mkdir(parents=True, exist_ok=True)
                self.meta(folder)
        self.write(rel, text)
        if meta:
            self.meta(rel)
        return rel

    def commit(self, message: str = "change") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)


CLEAN_CS = "namespace Kit\n{\n    public class A\n    {\n        public int Value;\n    }\n}\n"


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    r = Repo(tmp_path / "repo")
    r.root.mkdir()
    r.git("init", "-q", "-b", "main")
    r.git("config", "user.name", "Test")
    r.git("config", "user.email", "test@example.com")
    r.git("config", "core.autocrlf", "false")
    r.write("README.md", "fixture\n")
    (r.root / r.assets).mkdir(parents=True)
    r.asset("Kit/A.cs", CLEAN_CS)
    r.commit("base")
    r.git("switch", "-q", "-c", "task")
    return r


def run_gate(module, repo: Repo, *extra: str) -> tuple[int, str]:
    """Run a gate in-process; return (exit code, stdout)."""
    import io
    from contextlib import redirect_stdout

    import gate_common

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = gate_common.run(module.GATE, module.main, ["--repo", str(repo.root), "--project", PROJECT, *extra])
    return code, buf.getvalue()
