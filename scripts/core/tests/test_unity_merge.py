import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import setup_git  # noqa: E402
import unity_merge  # noqa: E402

SCENE = "%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!1 &1\nGameObject:\n  m_Name: {name}\n  m_TagString: {tag}\n"


def files(tmp_path, base, theirs, ours):
    paths = []
    for label, text in (("base", base), ("theirs", theirs), ("ours", ours)):
        path = tmp_path / f"{label}_noext"  # git's temp files have no extension
        path.write_text(text, encoding="utf-8")
        paths.append(str(path))
    return paths


def test_tool_sees_the_extension_and_result_lands_in_ours(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, **kwargs):
        seen.append([Path(a).suffix for a in cmd[3:]])
        Path(cmd[-1]).write_text("merged", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(unity_merge.subprocess, "run", fake_run)
    base, theirs, ours = files(tmp_path, "b", "t", "o")

    assert unity_merge.merge("tool", base, theirs, ours, "Assets/Scenes/A.unity") == 0

    assert seen == [[".unity"] * 4]
    assert Path(ours).read_text(encoding="utf-8") == "merged"


def test_tool_failure_leaves_ours_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(unity_merge.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    base, theirs, ours = files(tmp_path, "b", "t", "mine")

    assert unity_merge.merge("tool", base, theirs, ours, "A.unity") == 1
    assert Path(ours).read_text(encoding="utf-8") == "mine"


@pytest.mark.skipif(setup_git.find_yaml_merge() is None, reason="UnityYAMLMerge not installed")
def test_real_tool_merges_edits_that_plain_git_conflicts_on(tmp_path):
    exe = str(setup_git.find_yaml_merge())
    base, theirs, ours = files(
        tmp_path,
        SCENE.format(name="Cam", tag="MainCamera"),
        SCENE.format(name="CamX", tag="MainCamera"),
        SCENE.format(name="Cam", tag="Untagged"),
    )

    assert unity_merge.merge(exe, base, theirs, ours, "A.unity") == 0

    merged = Path(ours).read_text(encoding="utf-8")
    assert "m_Name: CamX" in merged and "m_TagString: Untagged" in merged
