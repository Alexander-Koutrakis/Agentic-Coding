import pytest

import file_gates
from conftest import PROJECT

CARD = "docs/tasks/001-t.md"
CARD_TEXT = "# card\n\n```scope\nallow:\n  - Game Project/Assets/Kit/Task/**\ntests: may-not-change\n```\n"
ARGS = ["--project", PROJECT]


def gates(repo, cmd, *argv):
    return file_gates.main([cmd, "--repo", str(repo.root), *argv])


@pytest.fixture
def task(repo):
    """Branch 'task' with an earlier, already committed change that is outside the card's scope."""
    repo.write(CARD, CARD_TEXT)
    repo.asset("Kit/Earlier/Old.txt", "old")
    repo.commit("earlier work, brief and card")
    return repo


def test_begin_gives_every_gate_the_same_base_so_earlier_commits_are_not_flagged(task, capsys):
    assert gates(task, "begin", *ARGS, "--card", CARD) == 0
    task.asset("Kit/Task/New.txt", "new")

    code = gates(task, "run", *ARGS)

    out = capsys.readouterr().out
    assert code == 0
    assert "PASS file-gates:" in out and "scope ok" in out and "Earlier" not in out


def test_without_begin_the_base_is_main_and_scope_flags_earlier_work(task, capsys):
    task.asset("Kit/Task/New.txt", "new")

    code = gates(task, "run", *ARGS, "--card", CARD)

    assert code == 1
    assert "FAIL scope: outside card scope" in capsys.readouterr().out


def test_run_stops_at_the_first_failing_gate_and_prints_its_line(task, capsys):
    gates(task, "begin", *ARGS, "--card", CARD)
    task.asset("Kit/Task/NoMeta.txt", "x", meta=False)

    code = gates(task, "run", *ARGS)

    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL assets:" in out
    assert "PASS file-gates" not in out


def test_run_without_card_says_so_in_the_line(task, capsys):
    task.asset("Kit/Task/New.txt", "new")

    code = gates(task, "run", *ARGS)

    assert code == 0
    assert "scope: no card" in capsys.readouterr().out


def test_run_with_another_card_than_the_recorded_one_is_an_error(task):
    gates(task, "begin", *ARGS, "--card", CARD)

    with pytest.raises(file_gates.GateError, match="base was recorded for"):
        gates(task, "run", *ARGS, "--card", "docs/tasks/002-other.md")


def test_finish_composes_the_line_from_the_verified_file_gates(task, capsys):
    gates(task, "begin", *ARGS, "--card", CARD)
    task.asset("Kit/Task/New.txt", "new")
    gates(task, "run", *ARGS)
    capsys.readouterr()

    code = gates(task, "finish", *ARGS, "--editor", "18/18 EditMode (Kit.Tests)", "--errors", "0", "--warnings", "2")

    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out.startswith("PASS 18/18 EditMode (Kit.Tests), format ok (0 files), assets ok")
    assert out.endswith("0 errors, 2 warnings")


def test_finish_fails_when_files_changed_after_the_gates_ran(task, capsys):
    gates(task, "begin", *ARGS, "--card", CARD)
    gates(task, "run", *ARGS)
    task.asset("Kit/Task/Late.txt", "late")
    capsys.readouterr()

    code = gates(task, "finish", *ARGS, "--editor", "1/1 EditMode (A)", "--errors", "0", "--warnings", "0")

    assert code == 1
    assert capsys.readouterr().out.startswith("FAIL stale")


def test_finish_without_a_file_gate_run_is_an_error(task):
    with pytest.raises(file_gates.GateError, match="run 'file_gates.py run' first"):
        gates(task, "finish", *ARGS, "--editor", "1/1 EditMode (A)", "--errors", "0", "--warnings", "0")


@pytest.mark.parametrize("editor, errors, expected", [
    ("0/0 EditMode (A)", "0", "FAIL tests: 0 tests ran"),
    ("2/3 EditMode (A)", "0", "FAIL tests 2/3"),
    ("3/3 EditMode (A)", "4", "FAIL console: 4 errors"),
])
def test_finish_rejects_inconsistent_editor_results(task, capsys, editor, errors, expected):
    gates(task, "begin", *ARGS, "--card", CARD)
    gates(task, "run", *ARGS)
    capsys.readouterr()

    code = gates(task, "finish", *ARGS, "--editor", editor, "--errors", errors, "--warnings", "0")

    assert code == 1
    assert capsys.readouterr().out.startswith(expected)


def test_a_base_recorded_on_another_branch_is_ignored(task, capsys):
    gates(task, "begin", *ARGS, "--card", CARD)
    task.git("switch", "-q", "main")

    code = gates(task, "run", *ARGS)

    out = capsys.readouterr().out
    assert code == 0
    assert "scope: no card" in out and out.strip().endswith("base main")
