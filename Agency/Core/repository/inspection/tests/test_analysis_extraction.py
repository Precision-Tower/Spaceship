from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from Agency.Core.repository.inspection.analysis import (
    InspectionAnalysisDependencies,
    classify_mission_files,
    coverage_evidence_from_context,
    mission_next_command_from_artifacts,
)

from Agency.Core.runtime.commands import mission_command


COVERAGE_CATEGORIES = (
    "route_ownership",
    "workspace_host",
    "workbench_root",
    "creation_lifecycle",
    "cleanup_lifecycle",
    "expected_modified_files",
    "verification_surfaces",
)


class InspectionAnalysisExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.repo_root = Path(self.temp_dir.name)

        def dedupe(entries: list[Any]) -> list[str]:
            result: list[str] = []
            seen: set[str] = set()

            for entry in entries:
                value = str(entry)

                if value in seen:
                    continue

                seen.add(value)
                result.append(value)

            return result

        def classify(
            path: Path,
            *,
            intent_requests: set[str],
        ) -> dict[str, str]:
            if path.suffix == ".gd":
                return {
                    "path": path.name,
                    "class": "primary",
                }

            if path.suffix == ".md":
                return {
                    "path": path.name,
                    "class": "evidence",
                }

            return {
                "path": path.name,
                "class": "ignored",
                "reason": "unsupported",
            }

        self.plan_calls: list[dict[str, Any]] = []

        def next_action_after_plan(
            mission_id: str,
            plan: dict[str, Any],
            *,
            state: dict[str, Any],
        ) -> dict[str, Any]:
            self.plan_calls.append({
                "mission_id": mission_id,
                "plan": plan,
                "state": state,
            })
            return {
                "command": "propose",
                "reason": "Plan is ready.",
            }

        self.dependencies = InspectionAnalysisDependencies(
            dashboard_root=self.repo_root,
            inspection_classes=(
                "primary",
                "secondary",
                "evidence",
                "ignored",
            ),
            mission_coverage_categories=COVERAGE_CATEGORIES,
            dedupe_manifest_paths=dedupe,
            classify_inspection_file=classify,
            sort_class_paths=lambda paths, references: sorted(
                paths
            ),
            next_action_after_plan=next_action_after_plan,
        )

    def test_classifies_existing_files_and_missing_paths(
        self,
    ) -> None:
        source = self.repo_root / "UI" / "Main.gd"
        source.parent.mkdir(parents=True)
        source.write_text("extends Node", encoding="utf-8")

        evidence = self.repo_root / "audit.md"
        evidence.write_text("evidence", encoding="utf-8")

        result, skipped = classify_mission_files(
            [
                "UI/Main.gd",
                "audit.md",
                "missing.gd",
                "UI/Main.gd",
            ],
            intent_requests=set(),
            referenced_paths={"UI/Main.gd"},
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["primary"],
            ["UI/Main.gd"],
        )
        self.assertEqual(
            result["evidence"],
            ["audit.md"],
        )
        self.assertEqual(
            result["ignored"],
            ["missing.gd"],
        )
        self.assertEqual(
            skipped,
            [{
                "path": "missing.gd",
                "reason": "missing",
            }],
        )

    def test_rejects_absolute_and_parent_paths(self) -> None:
        result, skipped = classify_mission_files(
            [
                "/tmp/outside.gd",
                "../outside.gd",
            ],
            intent_requests=set(),
            referenced_paths=set(),
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["ignored"],
            [
                "../outside.gd",
                "/tmp/outside.gd",
            ],
        )
        self.assertEqual(
            {
                item["reason"]
                for item in skipped
            },
            {"invalid_manifest_path"},
        )

    def test_derives_coverage_evidence(self) -> None:
        result = coverage_evidence_from_context(
            {
                "inspected_files": [
                    {
                        "path": "UI/Main/Main.gd",
                        "class": "primary",
                        "evidence_terms": [
                            "route",
                            "instantiate",
                        ],
                    },
                    {
                        "path": "tests/workspace_audit.md",
                        "class": "evidence",
                        "evidence_terms": [
                            "workspace",
                            "verify",
                        ],
                    },
                ],
            },
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["route_ownership"][0]["path"],
            "UI/Main/Main.gd",
        )
        self.assertEqual(
            result["creation_lifecycle"][0]["path"],
            "UI/Main/Main.gd",
        )
        self.assertEqual(
            result["workspace_host"][0]["path"],
            "tests/workspace_audit.md",
        )
        self.assertEqual(
            result["verification_surfaces"][0]["path"],
            "tests/workspace_audit.md",
        )

    def test_completed_verification_has_no_next_command(
        self,
    ) -> None:
        result = mission_next_command_from_artifacts(
            Path("/missions/mission-123"),
            state={},
            plan={},
            proposed=True,
            planned=True,
            approved=True,
            review_decision="approved",
            unit_progress={
                "implementation_complete": True,
            },
            verification_report={
                "result": "passed",
            },
            inspection_passes=[],
            dependencies=self.dependencies,
        )

        self.assertIsNone(result["command"])
        self.assertEqual(
            result["reason"],
            "Mission completed successfully.",
        )

    def test_planned_mission_delegates_to_plan_analysis(
        self,
    ) -> None:
        state = {
            "inspection_complete": True,
        }
        plan = {
            "ready": True,
        }

        result = mission_next_command_from_artifacts(
            Path("/missions/mission-123"),
            state=state,
            plan=plan,
            proposed=False,
            planned=True,
            approved=False,
            review_decision="",
            unit_progress={},
            verification_report={},
            inspection_passes=[
                Path("inspect/pass_001.json"),
            ],
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["command"],
            "propose",
        )
        self.assertEqual(len(self.plan_calls), 1)
        self.assertEqual(
            self.plan_calls[0]["mission_id"],
            "mission-123",
        )
        self.assertIs(
            self.plan_calls[0]["state"],
            state,
        )

    def test_uninspected_mission_routes_to_inspection(
        self,
    ) -> None:
        result = mission_next_command_from_artifacts(
            Path("/missions/mission-123"),
            state={},
            plan={},
            proposed=False,
            planned=False,
            approved=False,
            review_decision="",
            unit_progress={},
            verification_report={},
            inspection_passes=[],
            dependencies=self.dependencies,
        )

        self.assertEqual(
            result["command"],
            mission_command("inspect", "mission-123"),
        )


if __name__ == "__main__":
    unittest.main()
