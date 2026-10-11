"""Which Unity assembly owns a .cs file, and what kind it is. Shared by the scope and code-rules gates.

The owning assembly is the nearest .asmdef going up from the file, up to <project>/Assets. It is looked up
on disk and at the merge-base (a change must not unlock a file by editing its .asmdef in the same diff).
With no .asmdef the file is in one of Unity's predefined assemblies (Assembly-CSharp, or
Assembly-CSharp-Editor when a folder on the way is called Editor).
"""
from __future__ import annotations

import json
from pathlib import Path

from changed_files import read_at, tree_files


class Assemblies:
    def __init__(self, repo: Path, project: str, mb: str):
        self.repo, self.mb = repo, mb
        self.assets = f"{project}/Assets"
        self.base_tracked = tree_files(repo, mb, f"{self.assets}/")
        self._cache: dict[tuple[str, str], list[dict] | None] = {}

    @staticmethod
    def _parse(text: str) -> dict:
        try:
            data = json.loads(text.lstrip("﻿"))  # Unity and Visual Studio may write a BOM
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}

    def _asmdefs(self, folder: str, view: str) -> list[dict] | None:
        """The .asmdef files directly in folder in this view ("disk" or "base"), parsed; None if it holds none."""
        key = (folder, view)
        if key not in self._cache:
            if view == "disk":
                disk = sorted((self.repo / folder).glob("*.asmdef")) if (self.repo / folder).is_dir() else []
                texts = [p.read_text(encoding="utf-8", errors="replace") for p in disk]
            else:
                at_base = sorted(p for p in self.base_tracked if p.endswith(".asmdef") and p.rsplit("/", 1)[0] == folder)
                texts = [read_at(self.repo, self.mb, p) or "" for p in at_base]
            self._cache[key] = [self._parse(t) for t in texts] if texts else None
        return self._cache[key]

    def _nearest(self, path: str, view: str) -> list[dict] | None:
        folder = path.rsplit("/", 1)[0]
        while len(folder) >= len(self.assets):
            found = self._asmdefs(folder, view)
            if found is not None:
                return found
            folder = folder.rsplit("/", 1)[0]
        return None

    def _under_assets(self, path: str) -> bool:
        return path.endswith(".cs") and path.startswith(f"{self.assets}/")

    @staticmethod
    def _is_test_asmdef(data: dict) -> bool:
        return "UNITY_INCLUDE_TESTS" in data.get("defineConstraints", []) or \
            "TestAssemblies" in data.get("optionalUnityReferences", [])

    def _in_test_assembly(self, path: str, view: str) -> bool:
        found = self._nearest(path, view)
        return found is not None and any(self._is_test_asmdef(d) for d in found)

    def is_test(self, path: str) -> bool:
        """Test code: under a Tests/ folder, or in a test assembly (on disk or at the merge-base)."""
        if not self._under_assets(path):
            return False
        if "Tests" in path[len(self.assets) + 1:].split("/")[:-1]:
            return True
        return self._in_test_assembly(path, "disk") or self._in_test_assembly(path, "base")

    def is_editor_only(self, path: str) -> bool:
        """Editor-only code: the owning .asmdef has includePlatforms == ["Editor"] on disk.

        With no .asmdef, a folder called Editor below Assets (Unity's Assembly-CSharp-Editor).
        """
        if not self._under_assets(path):
            return False
        found = self._nearest(path, "disk")
        if found is not None:
            return any(d.get("includePlatforms") == ["Editor"] for d in found)
        return "Editor" in path[len(self.assets) + 1:].split("/")[:-1]
