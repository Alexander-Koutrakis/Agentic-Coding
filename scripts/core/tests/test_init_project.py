import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import init_project  # noqa: E402

KIT = Path(__file__).resolve().parents[3]


@pytest.fixture
def target(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "Game/Assets").mkdir(parents=True)
    (tmp_path / "Game/ProjectSettings").mkdir()
    (tmp_path / "Game/ProjectSettings/ProjectVersion.txt").write_text("m_EditorVersion: 6000.3.10f1\n")
    return tmp_path


def test_writes_files_with_filled_placeholders(target, capsys):
    assert init_project.main(["--target", str(target), "--name", "Demo"]) == 0

    claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# Demo" in claude and "`Game/`" in claude and "{{" not in claude
    assert "{{" not in (target / "docs/HANDOFF.md").read_text(encoding="utf-8")
    assert (target / "logs/friction-log.md").is_file()
    assert "PASS init: wrote 4" in capsys.readouterr().out


def test_attributes_come_from_the_kit(target):
    init_project.main(["--target", str(target)])

    text = (target / ".gitattributes").read_text(encoding="utf-8")
    assert "merge=unityyamlmerge" in text and "filter=lfs" in text
    assert "Test Environments" not in text and "Test[[:space:]]Environments" not in text


def test_never_overwrites(target, capsys):
    (target / "CLAUDE.md").write_text("mine", encoding="utf-8")

    assert init_project.main(["--target", str(target)]) == 0

    assert (target / "CLAUDE.md").read_text(encoding="utf-8") == "mine"
    assert "SKIPPED existing 1 (CLAUDE.md)" in capsys.readouterr().out


def test_needs_one_unity_project(tmp_path, capsys):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    assert init_project.main(["--target", str(tmp_path)]) == 2
    assert "Unity project" in capsys.readouterr().out


def test_not_a_repo_is_exit_2(tmp_path):
    assert init_project.main(["--target", str(tmp_path)]) == 2


def test_real_templates_have_no_unknown_placeholders():
    values = {"name": "n", "unity_project": "u", "date": "d"}
    for _, text in init_project.plan(KIT, values):
        assert "{{" not in text
