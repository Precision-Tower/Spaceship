from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from Agency.Core.repository.inspection.context import (
    InspectionContextDependencies,
    build_inspection_context,
)


class InspectionContextExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "sample.py"
        self.source.write_text(
            "import os\n\nclass Sample:\n    pass\n",
            encoding="utf-8",
        )

        self.dependencies = InspectionContextDependencies(
            dashboard_root=self.root,
            required_context_files=(),
            max_total_source_bytes=10000,
            max_prompt_source_chars=10000,
            max_prompt_chars=20000,
            candidate_files=lambda scopes: [self.source],
            manifest_candidate_paths=lambda paths: (
                [Path(path) for path in paths],
                [],
            ),
            path_in_validated_scopes=lambda path, scopes: True,
            skip_reason_for_path=lambda path: None,
            read_text_file=lambda path: (
                path.read_text(encoding="utf-8"),
                None,
            ),
            inspection_evidence_terms=lambda text: ["class"],
            extract_symbols=lambda path, text: [
                {"path": path.name, "name": "Sample"}
            ],
            extract_dependencies=lambda path, text: [
                {"path": path.name, "dependency": "os"}
            ],
            compact_json_context=lambda path: {"path": str(path)},
        )

    def test_builds_context_from_discovered_files(self) -> None:
        result = build_inspection_context(
            "inspect",
            [{"path": "."}],
            dependencies=self.dependencies,
            max_files=5,
        )

        self.assertEqual(result["discovered_files"], ["sample.py"])
        self.assertEqual(result["inspected_files"][0]["path"], "sample.py")
        self.assertEqual(result["symbols"][0]["name"], "Sample")
        self.assertEqual(
            result["dependencies"][0]["dependency"],
            "os",
        )

    def test_previously_inspected_file_is_skipped(self) -> None:
        result = build_inspection_context(
            "inspect",
            [{"path": "."}],
            dependencies=self.dependencies,
            previously_inspected={"sample.py"},
        )
        self.assertEqual(result["inspected_files"], [])

    def test_stop_at_limit_preserves_remaining_queue(self) -> None:
        second = self.root / "second.py"
        second.write_text("x = 1\n", encoding="utf-8")
        dependencies = InspectionContextDependencies(
            **{
                **self.dependencies.__dict__,
                "candidate_files": lambda scopes: [self.source, second],
            }
        )

        result = build_inspection_context(
            "inspect",
            [{"path": "."}],
            dependencies=dependencies,
            max_files=1,
            stop_at_file_limit=True,
        )

        self.assertEqual(
            [item["path"] for item in result["inspected_files"]],
            ["sample.py"],
        )
        self.assertEqual(result["remaining_files"], ["second.py"])

    def test_manifest_paths_preserve_initial_skips(self) -> None:
        dependencies = InspectionContextDependencies(
            **{
                **self.dependencies.__dict__,
                "manifest_candidate_paths": lambda paths: (
                    [self.source],
                    [{"path": "missing.py", "reason": "missing"}],
                ),
            }
        )

        result = build_inspection_context(
            "inspect",
            [{"path": "."}],
            dependencies=dependencies,
            candidate_paths=["ignored"],
        )

        self.assertEqual(
            result["skipped_files"],
            [{"path": "missing.py", "reason": "missing"}],
        )


if __name__ == "__main__":
    unittest.main()
