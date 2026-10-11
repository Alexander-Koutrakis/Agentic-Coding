import pytest

import scope_check
from conftest import CLEAN_CS, PROJECT, run_gate

TESTS_CS = (
    "using NUnit.Framework;\n\nnamespace Kit.Tests\n{\n    public class ATests\n    {\n"
    "        [Test]\n        public void One() { Assert.AreEqual(1, 1); }\n\n"
    "        [Test, Category(\"x\")]\n        public void Two() { Assert.IsTrue(true); Assert.IsFalse(false); }\n"
    "    }\n}\n"
)


def card(repo, allow, tests="may-not-change"):
    lines = "\n".join(f"  - {g}" for g in allow)
    repo.write("docs/card.md", f"# Card\n\n```scope\nallow:\n{lines}\ntests: {tests}\n```\n")


def gate(repo):
    return run_gate(scope_check, repo, "--card", "docs/card.md")


@pytest.fixture
def with_tests(repo):
    repo.asset("Kit/Tests/ATests.cs", TESTS_CS)
    repo.commit("tests")
    repo.git("switch", "-q", "main")
    repo.git("merge", "-q", "task")
    repo.git("switch", "-q", "-c", "task2")
    return repo


def test_changes_inside_scope_pass(repo):
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/Kit/**"])
    repo.asset("Kit/Deep/B.cs", CLEAN_CS)

    code, out = gate(repo)

    assert code == 0, out
    assert out.startswith("PASS scope: ")


def test_file_outside_scope_fails(repo):
    card(repo, ["docs/card.md"])
    repo.write("scripts/other.py", "x = 1\n")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, "FAIL scope: outside card scope: scripts/other.py")


def test_single_star_does_not_cross_folders(repo):
    card(repo, ["docs/card.md", "docs/*"])
    repo.write("docs/sub/deep.md", "x\n")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, "FAIL scope: outside card scope: docs/sub/deep.md")


def test_meta_is_allowed_through_its_asset_and_folder(repo):
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/Kit/New/**", f"{PROJECT}/Assets/Kit/B.cs"])
    repo.asset("Kit/New/C.cs", CLEAN_CS)  # also writes Kit/New.meta
    repo.asset("Kit/B.cs", CLEAN_CS)

    code, out = gate(repo)

    assert code == 0, out


def test_project_settings_need_approval_even_when_allowed(repo):
    card(repo, ["docs/card.md", f"{PROJECT}/**"])
    repo.write(f"{PROJECT}/ProjectSettings/ProjectSettings.asset", "x\n")

    code, out = gate(repo)

    assert code == 1
    assert out.startswith(f"FAIL scope: needs approval (ProjectSettings/Packages): {PROJECT}/ProjectSettings/")


def test_packages_need_approval(repo):
    card(repo, ["docs/card.md", f"{PROJECT}/**"])
    repo.write(f"{PROJECT}/Packages/manifest.json", "{}\n")

    code, out = gate(repo)

    assert code == 1
    assert "needs approval" in out


def test_deleted_test_fails(with_tests):
    repo = with_tests
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])
    repo.git("rm", "-q", f"{repo.assets}/Kit/Tests/ATests.cs", f"{repo.assets}/Kit/Tests/ATests.cs.meta")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL scope: test file deleted: {repo.assets}/Kit/Tests/ATests.cs")


def test_removed_assert_fails(with_tests):
    repo = with_tests
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])
    repo.write(f"{repo.assets}/Kit/Tests/ATests.cs", TESTS_CS.replace(" Assert.IsFalse(false);", ""))

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (
        1, f"FAIL scope: fewer asserts in {repo.assets}/Kit/Tests/ATests.cs: 3 -> 2 Assert calls")


def test_removed_test_attribute_fails(with_tests):
    repo = with_tests
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])
    repo.write(f"{repo.assets}/Kit/Tests/ATests.cs", TESTS_CS.replace("[Test, Category(\"x\")]", "[Category(\"x\")]"))

    code, out = gate(repo)

    assert code == 1
    assert "fewer tests in" in out and "2 -> 1 test attributes" in out


def test_added_tests_pass(with_tests):
    repo = with_tests
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])
    extra = "        [Test]\n        public void Three() { Assert.Pass(); }\n    }\n}\n"
    repo.write(f"{repo.assets}/Kit/Tests/ATests.cs", TESTS_CS[: TESTS_CS.rindex("    }\n}")] + extra)

    code, out = gate(repo)

    assert code == 0, out


def test_may_change_allows_the_same_diff(with_tests):
    repo = with_tests
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"], tests="may-change")
    repo.git("rm", "-q", f"{repo.assets}/Kit/Tests/ATests.cs", f"{repo.assets}/Kit/Tests/ATests.cs.meta")

    code, out = gate(repo)

    assert code == 0, out


def test_test_assembly_found_through_asmdef(repo):
    asmdef = '{\n    "name": "Kit.Checks",\n    "defineConstraints": [\n        "UNITY_INCLUDE_TESTS"\n    ]\n}\n'
    repo.asset("Checks/Kit.Checks.asmdef", asmdef)
    repo.asset("Checks/Deep/Probe.cs", TESTS_CS)
    repo.commit("test asmdef without a Tests folder")
    repo.git("switch", "-q", "main")
    repo.git("merge", "-q", "task")
    repo.git("switch", "-q", "-c", "task2")
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])
    repo.git("rm", "-q", f"{repo.assets}/Checks/Deep/Probe.cs", f"{repo.assets}/Checks/Deep/Probe.cs.meta")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL scope: test file deleted: {repo.assets}/Checks/Deep/Probe.cs")


def test_runtime_code_is_not_test_code(repo):
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])
    repo.git("rm", "-q", f"{repo.assets}/Kit/A.cs", f"{repo.assets}/Kit/A.cs.meta")

    code, out = gate(repo)

    assert code == 0, out


def test_card_without_scope_block_fails(repo):
    repo.write("docs/card.md", "# Card\n\nNo block here.\n")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, "FAIL scope: card has no scope block")


def test_bad_tests_rule_fails(repo):
    card(repo, ["docs/card.md"], tests="sometimes")

    code, out = gate(repo)

    assert code == 1
    assert "tests must be may-change or may-not-change" in out


def test_missing_card_is_an_environment_error(repo):
    code, out = run_gate(scope_check, repo, "--card", "docs/nope.md")

    assert code == 2
    assert out.startswith("ERROR scope: task card not found")


def test_globs_with_spaces(repo):
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/Kit/My Folder/**"])
    repo.asset("Kit/My Folder/B.cs", CLEAN_CS)  # + B.cs.meta + "My Folder.meta"
    repo.write("other folder/x.txt", "x\n")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, "FAIL scope: outside card scope: other folder/x.txt")
    assert "My Folder" not in out


# --- Regressions from the Task 002 review ---------------------------------------------------------

@pytest.mark.parametrize("spelling", ["./Game Project", "Game Project/", "ABSOLUTE", "game project"])
def test_project_path_spellings_are_not_a_silent_pass(repo, spelling):
    if spelling == "ABSOLUTE":
        spelling = str(repo.root / PROJECT)
    if spelling == "game project" and not (repo.root / spelling).exists():
        pytest.skip("case-sensitive file system")
    card(repo, ["docs/card.md", f"{PROJECT}/**"])
    repo.write(f"{PROJECT}/ProjectSettings/X.asset", "x\n")

    code, out = run_gate(scope_check, repo, "--card", "docs/card.md", "--project", spelling)

    assert code == 1
    assert out.startswith("FAIL scope: needs approval")


def test_project_outside_the_repo_is_an_environment_error(repo, tmp_path):
    (tmp_path / "elsewhere" / "Assets").mkdir(parents=True)
    card(repo, ["docs/card.md"])

    code, out = run_gate(scope_check, repo, "--card", "docs/card.md", "--project", str(tmp_path / "elsewhere"))

    assert code == 2
    assert out.startswith("ERROR scope: project")


def test_commented_out_test_fails(with_tests):
    repo = with_tests
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])
    weakened = TESTS_CS.replace("        [Test]\n        public void One() { Assert.AreEqual(1, 1); }",
                                "        // [Test]\n        // public void One() { Assert.AreEqual(1, 1); }")
    repo.write(f"{repo.assets}/Kit/Tests/ATests.cs", weakened)

    code, out = gate(repo)

    assert code == 1
    assert "2 -> 1 test attributes" in out and "3 -> 2 Assert calls" in out


def test_block_comment_and_strings_are_handled():
    code = 'var s = "// not a comment"; /* [Test] Assert.X */ Assert.IsTrue(true); // Assert.Y\n'
    assert scope_check.count(code) == (0, 1)


def test_method_named_test_is_not_an_attribute():
    assert scope_check.count("[Test]\npublic void Test() { }\n[Test, Category(\"x\")]\n") == (2, 0)


def _commit_test_assembly(repo, asmdef_text):
    repo.asset("Checks/Kit.Checks.asmdef", asmdef_text)
    repo.asset("Checks/Probe.cs", TESTS_CS)
    repo.commit("test asmdef")
    repo.git("switch", "-q", "main")
    repo.git("merge", "-q", "task")
    repo.git("switch", "-q", "-c", "task2")
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/**"])


TEST_ASMDEF = '{\n    "name": "Kit.Checks",\n    "defineConstraints": [\n        "UNITY_INCLUDE_TESTS"\n    ]\n}\n'


def test_asmdef_with_bom_is_recognised(repo):
    _commit_test_assembly(repo, "\ufeff" + TEST_ASMDEF)
    repo.git("rm", "-q", f"{repo.assets}/Checks/Probe.cs", f"{repo.assets}/Checks/Probe.cs.meta")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL scope: test file deleted: {repo.assets}/Checks/Probe.cs")


def test_dropping_the_test_constraint_does_not_unlock_the_tests(repo):
    _commit_test_assembly(repo, TEST_ASMDEF)
    repo.write(f"{repo.assets}/Checks/Kit.Checks.asmdef", '{\n    "name": "Kit.Checks"\n}\n')
    repo.git("rm", "-q", f"{repo.assets}/Checks/Probe.cs", f"{repo.assets}/Checks/Probe.cs.meta")

    code, out = gate(repo)

    assert code == 1
    assert f"test file deleted: {repo.assets}/Checks/Probe.cs" in out


def test_meta_whose_asset_is_not_allowed_fails(repo):
    card(repo, ["docs/card.md", f"{PROJECT}/Assets/Kit/B.cs"])
    repo.asset("Kit/C.cs", CLEAN_CS)

    code, out = gate(repo)

    assert code == 1
    assert f"outside card scope: {repo.assets}/Kit/C.cs.meta" in out


def test_hash_inside_a_glob_is_not_a_comment(repo):
    repo.write("docs/card.md", "```scope\nallow:\n  - docs/card.md\n  - docs/C#/**   # C# notes\ntests: may-change\n```\n")
    repo.write("docs/C#/note.md", "x\n")

    code, out = gate(repo)

    assert code == 0, out


def test_inline_allow_value_is_rejected(repo):
    repo.write("docs/card.md", "```scope\nallow: docs/**\ntests: may-change\n```\n")

    code, out = gate(repo)

    assert code == 1
    assert "own '  - ' line" in out


def test_card_that_is_not_utf8_is_an_environment_error(repo):
    (repo.root / "docs").mkdir(exist_ok=True)
    (repo.root / "docs" / "card.md").write_bytes(b"```scope\nallow:\n  - caf\xe9\n```\n")

    code, out = gate(repo)

    assert code == 2
    assert out.startswith("ERROR scope: task card is not UTF-8")


def test_details_are_capped_at_ten_lines(repo):
    card(repo, ["docs/card.md"])
    for i in range(15):
        repo.write(f"extra/f{i:02}.txt", "x\n")

    code, out = gate(repo)
    lines = out.splitlines()

    assert code == 1
    assert len(lines) == 11  # result line (problem 1) + 9 details + the "more" line = 10 detail lines
    assert lines[-1] == "  ... 5 more in .agent/logs/scope.txt"
    assert (repo.root / ".agent/logs/scope.txt").read_text().count("outside card scope") == 15


def test_folder_that_is_not_a_git_repo_is_an_environment_error(tmp_path):
    (tmp_path / "P" / "Assets").mkdir(parents=True)
    import gate_common

    code = gate_common.run(scope_check.GATE, scope_check.main,
                           ["--repo", str(tmp_path), "--project", "P", "--card", "c.md"])

    assert code == 2
