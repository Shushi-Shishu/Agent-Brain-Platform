"""Tests for the POC 6c artifact commitment."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from artifact_manifest import build_manifest, verify_manifest


class ArtifactManifestTests(unittest.TestCase):
    def test_manifest_is_stable_and_detects_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b.txt").write_text("beta", encoding="utf-8")
            (root / "nested").mkdir()
            (root / "nested" / "a.txt").write_text("alpha", encoding="utf-8")
            first = build_manifest(root)
            second = build_manifest(root)
            self.assertEqual(first, second)
            self.assertEqual(verify_manifest(root, first), [])
            (root / "b.txt").write_text("changed", encoding="utf-8")
            self.assertIn(
                "changed files: ['b.txt']",
                verify_manifest(root, first),
            )

    def test_manifest_file_and_cache_are_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "keep.md").write_text("kept", encoding="utf-8")
            (root / "MANIFEST.json").write_text("self", encoding="utf-8")
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "x.pyc").write_bytes(b"cache")
            manifest = build_manifest(root)
            self.assertEqual(
                [record["path"] for record in manifest["files"]],
                ["keep.md"],
            )


if __name__ == "__main__":
    unittest.main()
