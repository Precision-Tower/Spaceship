from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from Agency.Core.repository.inspection.state import (
    InspectionStateDependencies,
    mission_reconstruction,
    mission_status_payload,
)


class InspectionStateExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.mission_dir = Path(self.temp_dir.name) / "mission-001"
        self.mission_dir.mkdir()
        (self.mission_dir / "inspect").mkdir()
        (self.mission_dir / "review").mkdir()

        self.data: dict[str, dict[str, Any]] = {}
        self.next_action_calls: list[dict[str, Any]] = []

        def load_required(path: Path) -> dict[str, Any]:
            if str(path) not in self.data:
                raise FileNotFoundError(path)
            return self.data[str(path)]

        def load_optional(path: Path) -> dict[str, Any]:
            return self.data.get(str(path), {})

        def artifact(name: str):
            return lambda mission_dir: mission_dir / name

        def next_action(mission_dir: Path, **kwargs: Any) -> dict[str, Any]:
            self.next_action_calls.append({"mission_dir": mission_dir, **kwargs})
            return {"command": "next", "reason": "derived"}

        self.dependencies = InspectionStateDependencies(
            load_required_mission_json=load_required,
            load_optional_mission_json=load_optional,
            mission_intent_path=artifact("intent.json"),
            mission_state_path=artifact("state.json"),
            mission_plan_json_path=artifact("plan.json"),
            mission_proposal_json_path=artifact("proposal.json"),
            mission_review_decision_json_path=artifact("review.json"),
            mission_implementation_manifest_path=artifact("implementation.json"),
            mission_verification_report_json_path=artifact("verification.json"),
            mission_inspect_dir=lambda mission_dir: mission_dir / "inspect",
            mission_unit_progress=lambda mission_dir, proposal: {
                "total": 0,
                "complete": 0,
                "implementation_complete": False,
            },
            mission_next_command_from_artifacts=next_action,
            assess_plan_proposal_readiness=lambda plan: {"ready": True},
            mission_artifact_path_map=lambda mission_dir: {
                "intent": str(mission_dir / "intent.json")
            },
            mission_timestamps=lambda mission_dir: {"created": "now"},
            mission_event_files=lambda mission_dir: [],
            stable_path=lambda path: path.as_posix(),
        )

    def put(self, relative: str, value: dict[str, Any]) -> None:
        self.data[str(self.mission_dir / relative)] = value

    def test_status_payload_reads_required_artifacts(self) -> None:
        self.put("intent.json", {
            "intent": "Inspect architecture",
            "scopes": [{"path": "Agency"}],
        })
        self.put("state.json", {
            "phase": "inspection",
            "inspection_complete": False,
            "status": "running",
            "next_action": "continue",
        })
        pass_path = self.mission_dir / "inspect" / "pass_001.json"
        pass_path.write_text("{}", encoding="utf-8")

        result = mission_status_payload(
            self.mission_dir,
            dependencies=self.dependencies,
        )

        self.assertEqual(result["mission_id"], "mission-001")
        self.assertEqual(result["intent"], "Inspect architecture")
        self.assertEqual(result["inspection_passes"], 1)
        self.assertEqual(
            result["artifacts"]["inspection_passes"],
            [pass_path.as_posix()],
        )
        self.assertEqual(result["authority"], "read_only_mission_status")

    def test_reconstruction_defaults_to_created(self) -> None:
        self.put("intent.json", {"intent": "Inspect architecture"})
        self.put("state.json", {
            "phase": "created",
            "status": "ready_for_inspection",
        })

        result = mission_reconstruction(
            self.mission_dir,
            dependencies=self.dependencies,
        )

        self.assertEqual(result["phase"], "created")
        self.assertEqual(result["status"], "ready_for_inspection")
        self.assertTrue(result["checkpoints"]["created"])
        self.assertEqual(result["next_action"]["command"], "next")

    def test_reconstruction_marks_passed_verification_complete(self) -> None:
        self.put("intent.json", {"intent": "Inspect architecture"})
        self.put("state.json", {"phase": "verification"})
        self.put("verification.json", {
            "result": "passed",
            "mission_complete": True,
        })

        result = mission_reconstruction(
            self.mission_dir,
            dependencies=self.dependencies,
        )

        self.assertEqual(result["phase"], "complete")
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["checkpoints"]["complete"])

    def test_reconstruction_marks_inspected_mission_waiting_plan(self) -> None:
        self.put("intent.json", {"intent": "Inspect architecture"})
        self.put("state.json", {"phase": "inspection"})
        (self.mission_dir / "inspect" / "pass_001.json").write_text(
            "{}", encoding="utf-8"
        )

        result = mission_reconstruction(
            self.mission_dir,
            dependencies=self.dependencies,
        )

        self.assertEqual(result["phase"], "inspection")
        self.assertEqual(result["status"], "waiting_plan")
        self.assertTrue(result["checkpoints"]["inspected"])


if __name__ == "__main__":
    unittest.main()
