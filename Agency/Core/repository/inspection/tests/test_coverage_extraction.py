from __future__ import annotations

import unittest
from typing import Any

from Agency.Core.repository.inspection.coverage import (
    InspectionCoverageDependencies,
    update_inspection_coverage,
)


COVERAGE_CATEGORIES = (
    "route_ownership",
    "workspace_host",
)


class InspectionCoverageExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence_calls: list[dict[str, Any]] = []

        def evidence_from_context(
            context: dict[str, Any],
        ) -> dict[str, list[dict[str, str]]]:
            self.evidence_calls.append(context)

            return {
                "route_ownership": [
                    {
                        "path": "UI/Main/Main.gd",
                        "reason": "inspected route-related path or marker",
                    }
                ],
                "workspace_host": [],
            }

        self.dependencies = InspectionCoverageDependencies(
            schema_version=7,
            coverage_categories=COVERAGE_CATEGORIES,
            coverage_evidence_from_context=evidence_from_context,
        )

    def test_updates_partial_coverage_and_unresolved_items(
        self,
    ) -> None:
        context = {
            "inspected_files": [
                {
                    "path": "UI/Main/Main.gd",
                }
            ],
        }

        result = update_inspection_coverage(
            {},
            context,
            timestamp="2026-07-25T12:00:00Z",
            inspection_complete=False,
            next_files=["UI/Workbench/Main.gd"],
            dependencies=self.dependencies,
        )

        self.assertEqual(
            self.evidence_calls,
            [context],
        )
        self.assertEqual(result["schema_version"], 7)
        self.assertEqual(
            result["categories"],
            {
                "route_ownership": "partial",
                "workspace_host": "not_started",
            },
        )
        self.assertEqual(
            result["next_inspection"],
            ["UI/Workbench/Main.gd"],
        )
        self.assertEqual(
            result["unresolved"][0],
            "Inspection remains incomplete: 1 next files queued.",
        )
        self.assertIn(
            "workspace_host has no supporting inspection evidence yet.",
            result["unresolved"],
        )

    def test_preserves_complete_status(self) -> None:
        result = update_inspection_coverage(
            {
                "categories": {
                    "route_ownership": "complete",
                    "workspace_host": "not_started",
                },
            },
            {},
            timestamp="2026-07-25T12:00:00Z",
            inspection_complete=True,
            next_files=[],
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["categories"]["route_ownership"],
            "complete",
        )

    def test_deduplicates_evidence_by_path_and_reason(
        self,
    ) -> None:
        evidence_item = {
            "path": "UI/Main/Main.gd",
            "reason": "inspected route-related path or marker",
        }

        result = update_inspection_coverage(
            {
                "evidence": {
                    "route_ownership": [
                        evidence_item,
                    ],
                },
            },
            {},
            timestamp="2026-07-25T12:00:00Z",
            inspection_complete=True,
            next_files=[],
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["evidence"]["route_ownership"],
            [evidence_item],
        )

    def test_replaces_invalid_existing_shapes(self) -> None:
        result = update_inspection_coverage(
            {
                "categories": [],
                "evidence": "invalid",
            },
            {},
            timestamp="2026-07-25T12:00:00Z",
            inspection_complete=True,
            next_files=[],
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["categories"]["route_ownership"],
            "partial",
        )
        self.assertIsInstance(result["evidence"], dict)


if __name__ == "__main__":
    unittest.main()
