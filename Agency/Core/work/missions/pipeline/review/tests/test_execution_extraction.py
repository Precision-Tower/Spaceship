from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from typing import Any

from Agency.Core.work.missions.pipeline.review.execution import (
    ReviewExecutionDependencies,
    run_mission_review,
)


class ReviewExecutionExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.mission_dir = (
            Path(self.temp_dir.name) / "mission-123"
        )
        self.mission_dir.mkdir()

        self.proposal_path = (
            self.mission_dir / "proposal" / "proposal.json"
        )
        self.proposal_path.parent.mkdir()
        self.proposal_path.write_text(
            "{}",
            encoding="utf-8",
        )

        self.payloads: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.events: list[tuple[Any, ...]] = []
        self.pinboard_calls: list[dict[str, Any]] = []

        self.decision_json_path = (
            self.mission_dir / "review" / "decision.json"
        )
        self.decision_md_path = (
            self.mission_dir / "review" / "decision.md"
        )
        self.state_path = self.mission_dir / "state.json"

        self.args = argparse.Namespace(
            mission="mission-123",
            approve=True,
            reject=False,
            request_changes=False,
            notes="Approved.",
        )

    def make_dependencies(
        self,
        *,
        validate=None,
        resolve=None,
    ) -> ReviewExecutionDependencies:
        validation_calls = {"count": 0}

        def default_validate(
            args: argparse.Namespace,
            operator_notes: str = "",
        ):
            validation_calls["count"] += 1
            return "approved", (
                operator_notes or "Approved."
            ), None

        def review_failure(
            status: str,
            mission_id: str | None,
            reason: str,
            **kwargs: Any,
        ) -> int:
            self.failures.append({
                "status": status,
                "mission_id": mission_id,
                "reason": reason,
                **kwargs,
            })
            return int(kwargs.get("exit_code", 1))

        def atomic_json(
            path: Path,
            payload: dict[str, Any],
        ) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                repr(payload),
                encoding="utf-8",
            )

        def atomic_text(path: Path, value: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")

        return ReviewExecutionDependencies(
            schema_version=2,
            resolve_mission_dir=(
                resolve
                or (lambda mission: self.mission_dir)
            ),
            validate_review_request=(
                validate or default_validate
            ),
            review_failure=review_failure,
            mission_review_decision_json_path=(
                lambda mission_dir: self.decision_json_path
            ),
            mission_review_decision_md_path=(
                lambda mission_dir: self.decision_md_path
            ),
            mission_proposal_json_path=(
                lambda mission_dir: self.proposal_path
            ),
            load_review_inputs=lambda mission_dir: {
                "intent": {
                    "intent": "Extract Review execution."
                },
                "state": {
                    "schema_version": 2,
                },
                "plan": {
                    "created_at": "2026-01-01T00:00:00Z",
                    "schema_version": 2,
                },
                "proposal": {
                    "created_at": "2026-01-02T00:00:00Z",
                    "schema_version": 2,
                    "authority": "implementation_proposal",
                },
                "operator_notes": "",
            },
            now=lambda: "2026-01-03T00:00:00Z",
            review_next_action=lambda mission_id, decision: {
                "command": "implement",
                "mission_id": mission_id,
                "decision": decision,
            },
            stable=lambda path: path.as_posix(),
            mission_review_dir=(
                lambda mission_dir: mission_dir / "review"
            ),
            atomic_json=atomic_json,
            atomic_text=atomic_text,
            render_review_markdown=(
                lambda payload: "# Review\n"
            ),
            update_state_after_review=(
                lambda state, mission_id, decision, path: {
                    **state,
                    "status": "awaiting_implementation",
                    "next_action": decision["next_action"],
                }
            ),
            mission_state_path=(
                lambda mission_dir: self.state_path
            ),
            append_mission_event=(
                lambda *args: self.events.append(args)
            ),
            refresh_pinboard=(
                lambda **kwargs: self.pinboard_calls.append(
                    kwargs
                )
            ),
            emit_payload=self.payloads.append,
        )

    def test_approved_review_executes_full_boundary(self) -> None:
        result = run_mission_review(
            self.make_dependencies(),
            self.args,
        )

        self.assertEqual(result, 0)
        self.assertTrue(self.decision_json_path.exists())
        self.assertTrue(self.decision_md_path.exists())
        self.assertTrue(self.state_path.exists())
        self.assertEqual(len(self.events), 1)
        self.assertEqual(len(self.pinboard_calls), 1)
        self.assertEqual(len(self.payloads), 1)
        self.assertEqual(
            self.payloads[0]["status"],
            "awaiting_implementation",
        )
        self.assertTrue(
            self.payloads[0]["implementation_authorized"]
        )

    def test_missing_mission_uses_failure_boundary(self) -> None:
        def raise_missing(mission: str) -> Path:
            raise ValueError("mission does not exist")

        result = run_mission_review(
            self.make_dependencies(resolve=raise_missing),
            self.args,
        )

        self.assertEqual(result, 2)
        self.assertEqual(
            self.failures[0]["status"],
            "mission_not_found",
        )

    def test_existing_decision_is_idempotent(self) -> None:
        self.decision_json_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.decision_json_path.write_text(
            "{}",
            encoding="utf-8",
        )

        result = run_mission_review(
            self.make_dependencies(),
            self.args,
        )

        self.assertEqual(result, 0)
        self.assertEqual(
            self.payloads[0]["status"],
            "review_already_completed",
        )
        self.assertEqual(self.events, [])

    def test_missing_proposal_reports_required_action(self) -> None:
        self.proposal_path.unlink()

        result = run_mission_review(
            self.make_dependencies(),
            self.args,
        )

        self.assertEqual(result, 1)
        self.assertEqual(
            self.failures[0]["status"],
            "proposal_required",
        )
        self.assertEqual(
            self.failures[0]["next_action"]["authority"],
            "implementation_proposal",
        )

    def test_initial_validation_failure_stops_execution(self) -> None:
        def invalid(args: argparse.Namespace):
            return None, None, "decision required"

        result = run_mission_review(
            self.make_dependencies(validate=invalid),
            self.args,
        )

        self.assertEqual(result, 2)
        self.assertEqual(
            self.failures[0]["status"],
            "invalid_review_request",
        )
        self.assertFalse(self.decision_json_path.exists())


if __name__ == "__main__":
    unittest.main()
