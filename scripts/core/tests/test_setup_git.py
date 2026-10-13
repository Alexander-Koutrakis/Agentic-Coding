import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import setup_git  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


@pytest.fixture
def exe(tmp_path_factory):
    path = tmp_path_factory.mktemp("unity") / setup_git.TOOL
    path.write_text("")
    return path


def test_find_prefers_env_then_newest_editor(tmp_path):
    for version in ("6000.0.1f1", "6000.3.10f1", "2022.3.5f1"):
        tool = tmp_path / version / "Editor/Data/Tools" / setup_git.TOOL
        tool.parent.mkdir(parents=True)
        tool.write_text("")

    found = setup_git.find_yaml_merge((tmp_path,), env={})
    assert found.parts[-5] == "6000.3.10f1"

    explicit = tmp_path / "mine.exe"
    explicit.write_text("")
    assert setup_git.find_yaml_merge((tmp_path,), env={"UNITY_YAML_MERGE": str(explicit)}) == explicit


def test_find_returns_none_when_nothing_installed(tmp_path):
    assert setup_git.find_yaml_merge((tmp_path / "missing",), env={}) is None
    assert setup_git.find_yaml_merge((tmp_path,), env={"UNITY_YAML_MERGE": str(tmp_path / "gone")}) is None


def test_check_reports_unconfigured_repo(repo, exe):
    problems = setup_git.check(repo, exe)

    assert any("merge driver" in p for p in problems)


def test_main_configures_driver_and_check_passes(repo, exe, capsys):
    assert setup_git.main(["--repo", str(repo), "--yaml-merge", str(exe)]) == 0
    assert capsys.readouterr().out.startswith("PASS setup_git")

    assert setup_git.configured_driver(repo) == setup_git.driver_command(exe)
    assert setup_git.main(["--repo", str(repo), "--yaml-merge", str(exe), "--check"]) == 0


def test_check_mode_changes_nothing(repo, exe, capsys):
    assert setup_git.main(["--repo", str(repo), "--yaml-merge", str(exe), "--check"]) == 1

    assert setup_git.configured_driver(repo) == ""
    assert capsys.readouterr().out.startswith("FAIL setup_git")


def test_bad_repo_is_exit_2(tmp_path, exe):
    assert setup_git.main(["--repo", str(tmp_path), "--yaml-merge", str(exe)]) == 2
