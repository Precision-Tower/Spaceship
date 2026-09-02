from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Agency.Core.capabilities.engineering.paths import (
    diff_paths,
    packet_relative_path,
    resolve_workspace_path,
)


class EngineeringPathsTest(unittest.TestCase):
    def test_resolves_workspace_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            resolved = resolve_workspace_path(
                "Agency/example.txt",
                root,
            )

        self.assertEqual(
            root / "Agency" / "example.txt",
            resolved,
        )

    def test_rejects_workspace_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaisesRegex(
                ValueError,
                "path_traversal_rejected",
            ):
                resolve_workspace_path("../outside.txt", root)

    def test_packet_path_is_workspace_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            relative = packet_relative_path(
                "Agency/example.txt",
                root,
            )

        self.assertEqual("Agency/example.txt", relative)

    def test_extracts_paths_from_git_diff(self) -> None:
        paths = diff_paths(
            """diff --git a/Agency/old.py b/Agency/new.py
--- a/Agency/old.py
+++ b/Agency/new.py
"""
        )

        self.assertEqual(
            [
                "Agency/old.py",
                "Agency/new.py",
                "Agency/old.py",
                "Agency/new.py",
            ],
            paths,
        )


if __name__ == "__main__":
    unittest.main()
