import json

import pytest

import code_rules
from conftest import PROJECT, Repo, run_gate

LOG = "Debug.Log(\"x\");"


def runtime(body: str, usings: str = "using UnityEngine;") -> str:
    return f"{usings}\n\npublic class Foo : MonoBehaviour\n{{\n{body}\n}}\n"


def update(statement: str, usings: str = "using UnityEngine;") -> str:
    return runtime(f"    void Update()\n    {{\n        {statement}\n    }}", usings)


def gate(repo: Repo, rel: str, text: str, *, base_text: str | None = None) -> tuple[int, str]:
    """Run the gate with Assets/<rel> holding text. base_text: what main already has at that path."""
    if base_text is not None:
        repo.git("switch", "-q", "main")
        repo.asset(rel, base_text)
        repo.commit("base file")
        repo.git("switch", "-q", "task")
        repo.git("rebase", "-q", "main")
    repo.asset(rel, text)
    return run_gate(code_rules, repo)


def ok(result: tuple[int, str]) -> None:
    assert result[0] == 0, result[1]
    assert result[1].startswith("PASS code-rules:"), result[1]


def fails(result: tuple[int, str], *needles: str) -> None:
    assert result[0] == 1, result[1]
    assert result[1].startswith("FAIL code-rules:"), result[1]
    for needle in needles:
        assert needle in result[1], result[1]


# --- KIT004 ------------------------------------------------------------------------------------------------

def test_debug_log_in_runtime_code_fails_with_position(repo):
    fails(gate(repo, "Kit/Foo.cs", runtime(f"    void Start()\n    {{\n        {LOG}\n    }}")),
          "Kit/Foo.cs(7,9): KIT004 Debug.Log left in runtime code")


def test_debug_log_format_fails(repo):
    fails(gate(repo, "Kit/Foo.cs", runtime("    void Start() { Debug.LogFormat(\"{0}\", 1); }")), "KIT004")


@pytest.mark.parametrize("call", ["Debug.LogWarning(\"x\");", "Debug.LogError(\"x\");", "Debug.LogException(e);"])
def test_other_debug_calls_pass(repo, call):
    ok(gate(repo, "Kit/Foo.cs", runtime(f"    void Start() {{ {call} }}")))


def test_log_in_comment_or_string_passes(repo):
    body = "    void Start()\n    {\n        // Debug.Log(\"x\");\n        /* Debug.Log(\"y\"); */\n        var s = \"Debug.Log(1)\";\n    }"
    ok(gate(repo, "Kit/Foo.cs", runtime(body)))


def test_debug_log_in_editor_folder_passes(repo):
    ok(gate(repo, "Kit/Editor/Tool.cs", runtime(f"    void Start() {{ {LOG} }}")))


def test_user_class_named_xdebug_passes(repo):
    ok(gate(repo, "Kit/Foo.cs", runtime("    void Start() { MyDebug.Log(\"x\"); }")))


# --- KIT001 ------------------------------------------------------------------------------------------------

def editor_file(directives: list[str], inside: str = "using UnityEditor;") -> str:
    return "\n".join([*directives, inside, "#endif" if directives else "", "", "public class Foo { }", ""])


def test_using_unity_editor_in_runtime_code_fails(repo):
    fails(gate(repo, "Kit/Foo.cs", "using UnityEditor;\n\npublic class Foo { }\n"),
          "Foo.cs(1,7): KIT001 UnityEditor in runtime code")


def test_qualified_unity_editor_name_fails(repo):
    fails(gate(repo, "Kit/Foo.cs", runtime("    void Start() { UnityEditor.EditorApplication.isPlaying = false; }")), "KIT001")


def test_unity_editor_guarded_passes(repo):
    ok(gate(repo, "Kit/Foo.cs", editor_file(["#if UNITY_EDITOR"])))


def test_unity_editor_in_else_branch_fails(repo):
    text = "#if UNITY_EDITOR\n#else\nusing UnityEditor;\n#endif\n\npublic class Foo { }\n"
    fails(gate(repo, "Kit/Foo.cs", text), "Foo.cs(3,7): KIT001")


def test_negated_unity_editor_fails(repo):
    fails(gate(repo, "Kit/Foo.cs", editor_file(["#if !UNITY_EDITOR"])), "KIT001")


def test_else_of_negated_unity_editor_passes(repo):
    text = "#if !UNITY_EDITOR\n#else\nusing UnityEditor;\n#endif\n\npublic class Foo { }\n"
    ok(gate(repo, "Kit/Foo.cs", text))


def test_nested_if_with_and_passes(repo):
    text = "#if UNITY_EDITOR && DEBUG\nusing UnityEditor;\n#endif\n\npublic class Foo { }\n"
    ok(gate(repo, "Kit/Foo.cs", text))


def test_unity_editor_inside_nested_non_editor_if_passes(repo):
    text = "#if UNITY_EDITOR\n#if DEBUG\nusing UnityEditor;\n#endif\n#endif\n\npublic class Foo { }\n"
    ok(gate(repo, "Kit/Foo.cs", text))


def test_unity_editor_after_endif_fails(repo):
    text = "#if UNITY_EDITOR\nusing UnityEditor.Callbacks;\n#endif\nusing UnityEditor;\n\npublic class Foo { }\n"
    fails(gate(repo, "Kit/Foo.cs", text), "Foo.cs(4,7): KIT001")


def test_or_with_another_symbol_is_not_editor_only(repo):
    text = "#if UNITY_EDITOR || DEVELOPMENT_BUILD\nusing UnityEditor;\n#endif\n\npublic class Foo { }\n"
    fails(gate(repo, "Kit/Foo.cs", text), "KIT001")


def test_elif_branch_is_not_guarded_by_the_if(repo):
    text = "#if UNITY_EDITOR\n#elif UNITY_ANDROID\nusing UnityEditor;\n#endif\n\npublic class Foo { }\n"
    fails(gate(repo, "Kit/Foo.cs", text), "KIT001")


def test_unity_editor_in_comment_or_string_passes(repo):
    ok(gate(repo, "Kit/Foo.cs", runtime("    // using UnityEditor;\n    string s = \"UnityEditor.Foo\";")))


def test_namespace_that_merely_contains_the_word_passes(repo):
    ok(gate(repo, "Kit/Foo.cs", "using Kit.UnityEditorTools;\nusing MyUnityEditor.Util;\n\npublic class Foo { }\n"))


def write_asmdef(repo: Repo, rel: str, **data) -> None:
    repo.asset(rel, json.dumps({"name": "Kit.Thing", **data}))


def test_editor_only_asmdef_passes(repo):
    write_asmdef(repo, "Kit/Tool/Kit.Tool.asmdef", includePlatforms=["Editor"])
    ok(gate(repo, "Kit/Tool/Tool.cs", "using UnityEditor;\n\npublic class Tool { }\n"))


def test_editor_only_asmdef_with_bom_passes(repo):
    repo.asset("Kit/Tool/Kit.Tool.asmdef", "﻿" + json.dumps({"name": "Kit.Tool", "includePlatforms": ["Editor"]}))
    ok(gate(repo, "Kit/Tool/Tool.cs", "using UnityEditor;\n\npublic class Tool { }\n"))


def test_runtime_asmdef_fails(repo):
    write_asmdef(repo, "Kit/Tool/Kit.Tool.asmdef", includePlatforms=[])
    fails(gate(repo, "Kit/Tool/Tool.cs", "using UnityEditor;\n\npublic class Tool { }\n"), "KIT001")


def test_editor_folder_inside_a_runtime_asmdef_is_still_runtime(repo):
    write_asmdef(repo, "Kit/Tool/Kit.Tool.asmdef")
    fails(gate(repo, "Kit/Tool/Editor/Tool.cs", "using UnityEditor;\n\npublic class Tool { }\n"), "KIT001")


def test_editor_folder_without_asmdef_passes(repo):
    ok(gate(repo, "Kit/Editor/Tool.cs", "using UnityEditor;\n\npublic class Tool { }\n"))


# --- KIT002 ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("statement", [
    "var go = GameObject.Find(\"Player\");",
    "var go = GameObject.FindWithTag(\"Player\");",
    "var go = GameObject.FindGameObjectWithTag(\"Player\");",
    "var a = FindObjectOfType<Foo>();",
    "var a = Object.FindObjectsOfType<Foo>();",
    "var a = FindFirstObjectByType<Foo>();",
    "var a = Object.FindAnyObjectByType(typeof(Foo));",
    "var a = FindObjectsByType<Foo>(FindObjectsSortMode.None);",
    "SendMessage(\"Hit\");",
    "gameObject.BroadcastMessage(\"Hit\");",
])
def test_scene_search_or_message_in_update_fails(repo, statement):
    fails(gate(repo, "Kit/Foo.cs", update(statement)), "KIT002", "in Update()")


@pytest.mark.parametrize("method", ["LateUpdate", "FixedUpdate", "OnGUI"])
def test_other_per_frame_methods_fail(repo, method):
    body = f"    private void {method}()\n    {{\n        GameObject.Find(\"x\");\n    }}"
    fails(gate(repo, "Kit/Foo.cs", runtime(body)), "KIT002", f"in {method}()")


def test_same_call_in_start_passes(repo):
    body = "    void Start()\n    {\n        GameObject.Find(\"x\");\n    }"
    ok(gate(repo, "Kit/Foo.cs", runtime(body)))


def test_call_after_update_body_ends_passes(repo):
    body = ("    void Update()\n    {\n        if (true)\n        {\n            Move();\n        }\n    }\n\n"
            "    void Start()\n    {\n        GameObject.Find(\"x\");\n    }")
    ok(gate(repo, "Kit/Foo.cs", runtime(body)))


def test_expression_bodied_update_fails(repo):
    body = "    void Update() => GameObject.Find(\"x\");\n\n    void Start()\n    {\n        GameObject.Find(\"y\");\n    }"
    result = gate(repo, "Kit/Foo.cs", runtime(body))
    fails(result, "Foo.cs(5,22): KIT002")
    assert "(9," not in result[1]


def test_call_in_comment_or_string_in_update_passes(repo):
    statement = "// GameObject.Find(\"x\");\n        var s = \"FindObjectOfType<Foo>()\";\n        /* SendMessage(1); */"
    ok(gate(repo, "Kit/Foo.cs", update(statement)))


def test_update_declaration_without_a_body_passes(repo):
    ok(gate(repo, "Kit/IFoo.cs", "public interface IFoo\n{\n    void Update();\n}\n"))


def test_braces_in_strings_do_not_end_the_body_early(repo):
    statement = "var s = \"}\";\n        GameObject.Find(\"x\");"
    fails(gate(repo, "Kit/Foo.cs", update(statement)), "KIT002")


def test_scene_search_in_update_of_editor_code_still_fails(repo):
    fails(gate(repo, "Kit/Editor/Foo.cs", update("GameObject.Find(\"x\");")), "KIT002")


# --- KIT003 ------------------------------------------------------------------------------------------------

LINQ = "using UnityEngine;\nusing System.Linq;"


@pytest.mark.parametrize("call", ["Where", "Select", "Any", "All", "First", "FirstOrDefault", "Last", "OrderBy",
                                  "ToList", "ToArray", "Count", "Sum"])
def test_linq_in_update_fails(repo, call):
    fails(gate(repo, "Kit/Foo.cs", update(f"var r = items.{call}(x => x);", LINQ)), "KIT003", f".{call}()")


def test_linq_in_start_passes(repo):
    body = "    void Start()\n    {\n        var r = items.Where(x => x);\n    }"
    ok(gate(repo, "Kit/Foo.cs", runtime(body, LINQ)))


def test_linq_without_using_system_linq_passes(repo):
    ok(gate(repo, "Kit/Foo.cs", update("var r = items.Where(x => x);")))


def test_linq_in_comment_in_update_passes(repo):
    ok(gate(repo, "Kit/Foo.cs", update("// var r = items.Where(x => x);", LINQ)))


def test_count_property_and_mathf_calls_pass(repo):
    ok(gate(repo, "Kit/Foo.cs", update("var n = list.Count + Mathf.Max(1, 2);", LINQ)))


# --- suppression -------------------------------------------------------------------------------------------

def test_kit_allow_with_reason_on_the_same_line_passes_and_is_counted(repo):
    body = f"    void Start()\n    {{\n        {LOG} // kit-allow KIT004: startup banner\n    }}"
    code, out = gate(repo, "Kit/Foo.cs", runtime(body))
    assert code == 0 and out.startswith("PASS code-rules: 1 files, 0 new violations, 1 suppressed"), out


def test_kit_allow_on_the_line_above_passes(repo):
    body = f"    void Start()\n    {{\n        // kit-allow KIT004: startup banner\n        {LOG}\n    }}"
    code, out = gate(repo, "Kit/Foo.cs", runtime(body))
    assert code == 0 and "1 suppressed" in out, out


def test_kit_allow_without_a_reason_does_not_suppress(repo):
    body = f"    void Start()\n    {{\n        {LOG} // kit-allow KIT004:\n    }}"
    fails(gate(repo, "Kit/Foo.cs", runtime(body)), "KIT004")


def test_kit_allow_without_a_colon_does_not_suppress(repo):
    body = f"    void Start()\n    {{\n        // kit-allow KIT004\n        {LOG}\n    }}"
    fails(gate(repo, "Kit/Foo.cs", runtime(body)), "KIT004")


def test_kit_allow_for_another_rule_does_not_suppress(repo):
    body = f"    void Start()\n    {{\n        {LOG} // kit-allow KIT001: not this rule\n    }}"
    fails(gate(repo, "Kit/Foo.cs", runtime(body)), "KIT004")


def test_trailing_kit_allow_on_the_previous_code_line_does_not_reach_the_next(repo):
    body = f"    void Start()\n    {{\n        int a = 1; // kit-allow KIT004: only this line\n        {LOG}\n    }}"
    fails(gate(repo, "Kit/Foo.cs", runtime(body)), "KIT004")


def test_kit_allow_lists_several_rules(repo):
    statement = "GameObject.Find(\"x\"); // kit-allow KIT002, KIT003: cached by the caller"
    ok(gate(repo, "Kit/Foo.cs", update(statement)))


# --- new violations only -----------------------------------------------------------------------------------

def test_violation_already_at_the_merge_base_passes(repo):
    old = runtime(f"    void Start() {{ {LOG} }}")
    ok(gate(repo, "Kit/Foo.cs", old + "// touched\n", base_text=old))


def test_one_more_violation_fails_and_lists_all_of_that_rule_in_the_file(repo):
    old = runtime(f"    void Start() {{ {LOG} }}")
    new = runtime(f"    void Start() {{ {LOG} }}\n    void Stop() {{ {LOG} }}")
    result = gate(repo, "Kit/Foo.cs", new, base_text=old)
    fails(result, "(5,", "(6,")


def test_fewer_violations_pass(repo):
    old = runtime(f"    void Start() {{ {LOG} {LOG} }}")
    ok(gate(repo, "Kit/Foo.cs", runtime(f"    void Start() {{ {LOG} }}"), base_text=old))


def test_a_new_violation_of_another_rule_fails(repo):
    old = runtime(f"    void Start() {{ {LOG} }}")
    new = runtime(f"    void Start() {{ {LOG} }}\n    void Update() {{ GameObject.Find(\"x\"); }}")
    fails(gate(repo, "Kit/Foo.cs", new, base_text=old), "KIT002")


def test_renamed_file_keeps_its_old_violations(repo):
    old = runtime(f"    void Start() {{ {LOG} }}")
    repo.git("switch", "-q", "main")
    repo.asset("Kit/Old.cs", old)
    repo.commit("old file")
    repo.git("switch", "-q", "task")
    repo.git("rebase", "-q", "main")
    repo.git("mv", f"{repo.assets}/Kit/Old.cs", f"{repo.assets}/Kit/New.cs")
    repo.git("mv", f"{repo.assets}/Kit/Old.cs.meta", f"{repo.assets}/Kit/New.cs.meta")
    (repo.root / repo.assets / "Kit/New.cs").write_text(old + "// renamed\n", encoding="utf-8", newline="")
    ok(run_gate(code_rules, repo))


def test_renamed_file_with_an_added_violation_fails(repo):
    old = runtime(f"    void Start() {{ {LOG} }}")
    repo.git("switch", "-q", "main")
    repo.asset("Kit/Old.cs", old)
    repo.commit("old file")
    repo.git("switch", "-q", "task")
    repo.git("rebase", "-q", "main")
    repo.git("mv", f"{repo.assets}/Kit/Old.cs", f"{repo.assets}/Kit/New.cs")
    repo.git("mv", f"{repo.assets}/Kit/Old.cs.meta", f"{repo.assets}/Kit/New.cs.meta")
    new = runtime(f"    void Start() {{ {LOG} {LOG} }}")
    (repo.root / repo.assets / "Kit/New.cs").write_text(new, encoding="utf-8", newline="")
    fails(run_gate(code_rules, repo), "Kit/New.cs")


def test_new_file_compares_against_zero(repo):
    fails(gate(repo, "Kit/Brand.cs", runtime(f"    void Start() {{ {LOG} }}")), "Brand.cs")


# --- which files are checked ---------------------------------------------------------------------------------

def test_test_code_is_skipped(repo):
    text = runtime(f"    void Update() {{ {LOG} GameObject.Find(\"x\"); }}")
    ok(gate(repo, "Kit/Tests/FooTests.cs", "using UnityEditor;\n" + text))


def test_test_assembly_is_skipped(repo):
    write_asmdef(repo, "Kit/Checks/Kit.Checks.asmdef", defineConstraints=["UNITY_INCLUDE_TESTS"])
    ok(gate(repo, "Kit/Checks/FooChecks.cs", runtime(f"    void Start() {{ {LOG} }}")))


def test_no_changed_cs_files_passes_with_zero_files(repo):
    repo.write("docs/notes.md", "x\n")
    code, out = run_gate(code_rules, repo)
    assert code == 0 and out.startswith("PASS code-rules: 0 files, 0 new violations, 0 suppressed"), out


def test_cs_files_outside_assets_are_ignored(repo):
    repo.write(f"{PROJECT}/Packages/Local/Foo.cs", runtime(f"    void Start() {{ {LOG} }}"))
    ok(run_gate(code_rules, repo))


def test_deleted_file_is_not_read(repo):
    (repo.root / repo.assets / "Kit/A.cs").unlink()
    ok(run_gate(code_rules, repo))


def test_crlf_and_bom_keep_positions(repo):
    text = "﻿using UnityEngine;\r\n\r\npublic class Foo\r\n{\r\n    void Start() { Debug.Log(1); }\r\n}\r\n"
    fails(gate(repo, "Kit/Foo.cs", text), "Foo.cs(5,20): KIT004")


def test_details_are_capped_and_logged(repo):
    body = "\n".join(f"    void M{i}() {{ {LOG} }}" for i in range(15))
    code, out = gate(repo, "Kit/Foo.cs", runtime(body))
    assert code == 1
    assert len(out.splitlines()) == 11 and "more in .agent/logs/code-rules.txt" in out, out
    assert len((repo.root / ".agent/logs/code-rules.txt").read_text().splitlines()) == 15


# --- unit: the #if evaluator --------------------------------------------------------------------------------

@pytest.mark.parametrize("cond,expected", [
    ("UNITY_EDITOR", True),
    (" (UNITY_EDITOR) ", True),
    ("UNITY_EDITOR && DEBUG", True),
    ("DEBUG && UNITY_EDITOR", True),
    ("!UNITY_EDITOR", False),
    ("UNITY_EDITOR || DEBUG", False),
    ("DEBUG", False),
    ("!(!UNITY_EDITOR)", True),
    ("UNITY_EDITOR && !UNITY_EDITOR", True),  # never runs, so vacuously editor-only
])
def test_implies_editor(cond, expected):
    assert code_rules.implies_editor(code_rules.parse_condition(cond)) is expected


@pytest.mark.parametrize("cond", ["UNITY_EDITOR &&", "(UNITY_EDITOR", "A == B", "", "&& A"])
def test_unparseable_conditions_return_none(cond):
    assert code_rules.parse_condition(cond) is None
