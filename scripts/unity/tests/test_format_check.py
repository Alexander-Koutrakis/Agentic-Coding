import shutil

import pytest

import format_check
from conftest import CLEAN_CS, PROJECT, run_gate

needs_sdk = pytest.mark.skipif(not format_check.sdk_available(shutil.which("dotnet")), reason="no .NET SDK")

EDITORCONFIG = (
    "root = true\n\n[*.cs]\nindent_style = space\nindent_size = {size}\n"
    "trim_trailing_whitespace = true\ninsert_final_newline = true\n"
)


@pytest.fixture
def project(repo):
    repo.write(f"{PROJECT}/.editorconfig", EDITORCONFIG.format(size=4))
    repo.commit("editorconfig")
    return repo


@needs_sdk
def test_clean_changed_file_passes(project):
    project.asset("Kit/B.cs", CLEAN_CS.replace("class A", "class B"))

    code, out = run_gate(format_check, project)

    assert (code, out.splitlines()[0]) == (0, "PASS format: 1 files")


@needs_sdk
def test_trailing_whitespace_fails_with_file_line_and_column(project):
    project.asset("Kit/B.cs", CLEAN_CS.replace("public int Value;", "public int Value;   "))

    code, out = run_gate(format_check, project)

    assert code == 1
    assert out.startswith(f"FAIL format: {PROJECT}/Assets/Kit/B.cs(5,")
    assert "error WHITESPACE" in out


@needs_sdk
def test_wrong_indentation_fails(project):
    project.asset("Kit/B.cs", "namespace Kit\n{\n  public class B\n  {\n  }\n}\n")

    code, out = run_gate(format_check, project)

    assert code == 1
    assert "Kit/B.cs(" in out


@needs_sdk
def test_editorconfig_at_project_root_applies_with_assets_workspace(project):
    # 2-space indentation passes only if the project-root .editorconfig (indent_size = 2) is read.
    project.write(f"{PROJECT}/.editorconfig", EDITORCONFIG.format(size=2))
    project.commit("two spaces")
    project.asset("Kit/B.cs", "namespace Kit\n{\n  public class B\n  {\n  }\n}\n")

    code, out = run_gate(format_check, project)

    assert (code, out.splitlines()[0]) == (0, "PASS format: 1 files")


@needs_sdk
def test_unchanged_files_are_not_checked(project):
    project.asset("Kit/Old.cs", "namespace Kit\n{\n  class Old { }   \n}\n")
    project.commit("bad file already on main")
    project.git("switch", "-q", "main")
    project.git("merge", "-q", "task")
    project.git("switch", "-q", "-c", "task2")

    code, out = run_gate(format_check, project)

    assert (code, out.strip()) == (0, "PASS format: 0 files")


def test_no_changed_cs_files_passes(project):
    project.write("notes.txt", "not C#\n")

    code, out = run_gate(format_check, project)

    assert (code, out.strip()) == (0, "PASS format: 0 files")


def test_missing_sdk_fails_never_skips(project, tmp_path):
    project.asset("Kit/B.cs", CLEAN_CS.replace("class A", "class B"))

    code, out = run_gate(format_check, project, "--dotnet", str(tmp_path / "no-such-dotnet.exe"))

    assert code == 1
    assert out.startswith("FAIL format: no .NET SDK (dotnet format unavailable)")


def test_bad_project_path_is_an_environment_error(repo):
    code, out = run_gate(format_check, repo, "--project", "Nope")

    assert code == 2
    assert out.startswith("ERROR format: no Assets folder")
