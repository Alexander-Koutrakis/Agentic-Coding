"""Git merge driver for Unity YAML: runs UnityYAMLMerge on copies that keep the file's extension.

Git hands drivers extension-less temp files, and UnityYAMLMerge picks its tool by extension, so calling
it directly fails ("Couldn't locate merge tool to handle extension"). Registered by setup_git.py as
    python unity_merge.py <UnityYAMLMerge> %O %B %A %P
Exit 0 = merged into %A. Non-zero = left %A untouched, git reports a conflict.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def merge(exe: str, base: str, theirs: str, ours: str, name: str) -> int:
    suffix = Path(name).suffix
    with tempfile.TemporaryDirectory() as tmp:
        copies = {}
        for label, src in (("base", base), ("theirs", theirs), ("ours", ours)):
            copies[label] = Path(tmp) / f"{label}{suffix}"
            shutil.copyfile(src, copies[label])
        result = subprocess.run(
            [exe, "merge", "-p", str(copies["base"]), str(copies["theirs"]), str(copies["ours"]), str(copies["ours"])],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stdout + result.stderr)
            return result.returncode
        shutil.copyfile(copies["ours"], ours)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 6:
        sys.exit("usage: unity_merge.py <UnityYAMLMerge> <base> <theirs> <ours> <path>")
    sys.exit(merge(*sys.argv[1:]))
