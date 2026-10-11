import asset_check
from conftest import CLEAN_CS, run_gate


def gate(repo):
    return run_gate(asset_check, repo)


def test_clean_project_passes(repo):
    repo.asset("Kit/Sub/B.cs", CLEAN_CS)
    repo.commit()

    code, out = gate(repo)

    assert code == 0
    assert out.startswith("PASS assets: ")


def test_missing_meta_fails(repo):
    repo.asset("Kit/B.cs", CLEAN_CS, meta=False)

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL assets: missing .meta: {repo.assets}/Kit/B.cs")


def test_folder_without_meta_fails(repo):
    repo.write(f"{repo.assets}/NewFolder/C.cs", CLEAN_CS)
    repo.meta(f"{repo.assets}/NewFolder/C.cs")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL assets: missing .meta: {repo.assets}/NewFolder")


def test_orphan_meta_fails(repo):
    repo.meta(f"{repo.assets}/Kit/Gone.cs")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL assets: orphan .meta: {repo.assets}/Kit/Gone.cs.meta")


def test_duplicate_guid_fails(repo):
    guid = "0123456789abcdef0123456789abcdef"
    repo.write(f"{repo.assets}/Kit/B.cs", CLEAN_CS)
    repo.meta(f"{repo.assets}/Kit/B.cs", guid)
    repo.write(f"{repo.assets}/Kit/C.cs", CLEAN_CS)
    repo.meta(f"{repo.assets}/Kit/C.cs", guid)

    code, out = gate(repo)

    assert code == 1
    assert out.startswith(f"FAIL assets: duplicate guid {guid}: ")


def test_bad_guid_line_fails(repo):
    repo.write(f"{repo.assets}/Kit/B.cs", CLEAN_CS)
    repo.write(f"{repo.assets}/Kit/B.cs.meta", "fileFormatVersion: 2\nguid: not-a-guid\n")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL assets: bad guid line: {repo.assets}/Kit/B.cs.meta")


def test_hidden_and_tilde_folders_are_skipped(repo):
    repo.write(f"{repo.assets}/.hidden/x.txt", "x")
    repo.write(f"{repo.assets}/Samples~/y.cs", CLEAN_CS)
    repo.write(f"{repo.assets}/Kit/scratch.tmp", "t")

    code, out = gate(repo)

    assert code == 0, out


def test_asset_committed_without_its_meta_fails_even_if_meta_is_on_disk(repo):
    rel = repo.asset("Kit/B.cs", CLEAN_CS)
    repo.git("add", rel)
    repo.git("commit", "-q", "-m", "forgot the meta")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL assets: staged without its .meta: {rel}")


def test_new_folder_committed_without_its_meta_fails(repo):
    rel = repo.asset("NewFolder/B.cs", CLEAN_CS)
    repo.git("add", rel, f"{rel}.meta")
    repo.git("commit", "-q", "-m", "forgot the folder meta")

    code, out = gate(repo)

    assert code == 1
    assert f"folder staged without its .meta: {repo.assets}/NewFolder" in out


def test_asset_renamed_without_its_meta_fails(repo):
    old, new = f"{repo.assets}/Kit/A.cs", f"{repo.assets}/Kit/B.cs"
    repo.git("mv", old, new)
    (repo.root / f"{old}.meta").rename(repo.root / f"{new}.meta")  # moved on disk, not in git

    code, out = gate(repo)

    assert code == 1
    assert f"staged without its .meta: {new}" in out
    assert f"removed but its .meta is still staged: {old}" in out


def test_asset_renamed_with_its_meta_passes(repo):
    old, new = f"{repo.assets}/Kit/A.cs", f"{repo.assets}/Kit/B.cs"
    repo.git("mv", old, new)
    repo.git("mv", f"{old}.meta", f"{new}.meta")

    code, out = gate(repo)

    assert code == 0, out


def test_asset_deleted_but_meta_still_staged_fails(repo):
    rel = f"{repo.assets}/Kit/A.cs"
    repo.git("rm", "-q", rel)
    (repo.root / f"{rel}.meta").unlink()  # gone on disk, still in the index

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL assets: removed but its .meta is still staged: {rel}")


def test_meta_staged_without_its_asset_fails(repo):
    rel = repo.asset("Kit/B.cs", CLEAN_CS)
    repo.git("add", f"{rel}.meta")

    code, out = gate(repo)

    assert (code, out.splitlines()[0]) == (1, f"FAIL assets: staged .meta without its asset: {rel}.meta")
