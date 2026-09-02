from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from Agency.Core.work.missions.pipeline.review.state import (
    ReviewStateDependencies,
    _load_operator_notes,
    _load_proposal,
    _load_review_inputs,
    _mission_review_decision_md_path,
    _review_failure,
    _update_state_after_review,
)


class ReviewStateExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payloads: list[dict[str, Any]] = []

        self.documents = {
            "intent.json": {
                "intent": "Extract Review state.",
            },
            "state.json": {
                "schema_version": "test-schema",
                "unresolved": [
                    "No implementation proposal exists.",
                    "Preserve operator authority.",
                ],
            },
            "proposal.json": {
                "authority": "implementation_proposal",
                "created_at": "2026-01-01T00:00:00Z",
            },
        }

        def load_json(path: Path) -> dict[str, Any]:
            return dict(self.documents[path.name])

        self.dependencies = ReviewStateDependencies(
            load_required_mission_json=load_json,
            mission_intent_path=lambda mission_dir: (
                mission_dir / "intent.json"
            ),
            mission_state_path=lambda mission_dir: (
                mission_dir / "state.json"
            ),
            mission_proposal_json_path=lambda mission_dir: (
                mission_dir / "proposal.json"
            ),
            mission_review_dir=lambda mission_dir: (
                mission_dir / "review"
            ),
            load_plan=lambda mission_dir: {
                "created_at": "2026-01-01T00:00:00Z",
                "schema_version": "test-schema",
            },
            now=lambda: "2026-01-02T00:00:00Z",
            stable=lambda path: path.as_posix(),
            schema_version="test-schema",
            emit_payload=self.payloads.append,
        )

    def test_operator_notes_are_loaded_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mission_dir = Path(directory)
            review_dir = mission_dir / "review"
            review_dir.mkdir()

            content = "x" * 2500
            (review_dir / "operator_notes.md").write_text(
                content,
                encoding="utf-8",
            )

            result = _load_operator_notes(mission_dir)

        self.assertEqual(len(result), 2000)

    def test_decision_markdown_path_uses_review_directory(self) -> None:
        mission_dir = Path("/tmp/example-mission")

        result = _mission_review_decision_md_path(
            mission_dir,
            self.dependencies,
        )

        self.assertEqual(
            result,
            mission_dir / "review" / "decision.md",
        )

    def test_load_proposal_rejects_wrong_authority(self) -> None:
        self.documents["proposal.json"]["authority"] = "wrong"

        with self.assertRaisesRegex(
            ValueError,
            "proposal authority",
        ):
            _load_proposal(
                Path("/tmp/example-mission"),
                self.dependencies,
            )

    def test_load_review_inputs_collects_persisted_artifacts(self) -> None:
        result = _load_review_inputs(
            Path("/tmp/example-mission"),
            self.dependencies,
        )

        self.assertEqual(
            result["intent"]["intent"],
            "Extract Review state.",
        )
        self.assertEqual(
            result["proposal"]["authority"],
            "implementation_proposal",
        )
        self.assertIn("plan", result)
        self.assertEqual(result["operator_notes"], "")

    def test_approved_review_updates_state(self) -> None:
        result = _update_state_after_review(
            self.documents["state.json"],
            "mission-123",
            {
                "decision": "approved",
                "reviewed_at": "2026-01-03T00:00:00Z",
                "next_action": {
                    "command": "implement",
                },
            },
            Path("review/decision.json"),
            self.dependencies,
        )

        self.assertEqual(result["phase"], "approved")
        self.assertEqual(result["status"], "awaiting_implementation")
        self.assertTrue(result["implementation_authorized"])
        self.assertTrue(result["implementation_enabled"])
        self.assertNotIn(
            "No implementation proposal exists.",
            result["unresolved"],
        )
        self.assertIn(
            "Implementation has not started.",
            result["unresolved"],
        )

    def test_review_failure_emits_payload_and_returns_exit_code(self) -> None:
        result = _review_failure(
            "invalid_review_request",
            "mission-123",
            "Decision required.",
            exit_code=2,
            dependencies=self.dependencies,
        )

        self.assertEqual(result, 2)
        self.assertEqual(len(self.payloads), 1)
        self.assertEqual(
            self.payloads[0]["status"],
            "invalid_review_request",
        )
        self.assertEqual(
            self.payloads[0]["authority"],
            "operator_review",
        )


if __name__ == "__main__":
    unittest.main()
