from changed_files import changed_files
from conftest import CLEAN_CS


def by_path(changes):
    return {c.path: c for c in changes}


def test_committed_staged_unstaged_and_untracked_are_all_reported(repo):
    repo.write("committed.txt", "a\n")
    repo.commit()
    repo.write("staged.txt", "b\n")
    repo.git("add", "staged.txt")
    repo.write("README.md", "edited\n")
    repo.write("dir with space/untracked.txt", "c\n")

    changes = by_path(changed_files(repo.root, "main"))

    assert {p: c.status for p, c in changes.items()} == {
        "committed.txt": "A",
        "staged.txt": "A",
        "README.md": "M",
        "dir with space/untracked.txt": "A",
    }


def test_rename_keeps_old_path(repo):
    repo.git("mv", f"{repo.assets}/Kit/A.cs", f"{repo.assets}/Kit/B.cs")
    repo.commit()

    c = by_path(changed_files(repo.root, "main"))[f"{repo.assets}/Kit/B.cs"]

    assert (c.status, c.old_path) == ("R", f"{repo.assets}/Kit/A.cs")


def test_index_view_ignores_unstaged_and_untracked(repo):
    repo.write("staged.txt", "b\n")
    repo.git("add", "staged.txt")
    repo.write("untracked.txt", "c\n")
    repo.write(f"{repo.assets}/Kit/A.cs", CLEAN_CS + "// edit\n")

    assert set(by_path(changed_files(repo.root, "main", worktree=False))) == {"staged.txt"}


def test_agent_runtime_files_are_never_reported(repo):
    repo.write(".agent/logs/format.txt", "PASS\n")

    assert changed_files(repo.root, "main") == []
