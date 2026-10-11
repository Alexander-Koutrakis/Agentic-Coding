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
