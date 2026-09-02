from __future__ import annotations

import argparse
import unittest

from Agency.Core.work.missions.pipeline.review.helpers import (
    _real_operator_notes,
    _render_review_markdown,
    _review_next_action,
    _validate_review_request,
)


class ReviewHelperExtractionTests(unittest.TestCase):
    def test_real_operator_notes_removes_placeholder_content(self) -> None:
        notes = _real_operator_notes(
            """
            # Operator Notes

            No operator review has been recorded.

            Keep the dependency boundary explicit.
            """
        )

        self.assertEqual(
            notes,
            "Keep the dependency boundary explicit.",
        )

    def test_validate_review_request_requires_exactly_one_decision(self) -> None:
        args = argparse.Namespace(
            approve=False,
            reject=False,
            request_changes=False,
            note="",
        )

        decision, note, error = _validate_review_request(args)

        self.assertIsNone(decision)
        self.assertEqual(note, "")
        self.assertIn("Exactly one", str(error))

    def test_request_changes_uses_existing_operator_notes(self) -> None:
        args = argparse.Namespace(
            approve=False,
            reject=False,
            request_changes=True,
            note="",
        )

        decision, note, error = _validate_review_request(
            args,
            "Revise the verification plan.",
        )

        self.assertEqual(decision, "changes_requested")
        self.assertEqual(note, "Revise the verification plan.")
        self.assertIsNone(error)

    def test_approved_next_action_targets_implementation(self) -> None:
        result = _review_next_action("mission-123", "approved")

        self.assertEqual(result["authority"], "operator_approval")
        self.assertIn("mission implement", result["command"])
        self.assertIn("mission-123", result["command"])

    def test_render_review_markdown_preserves_decision_data(self) -> None:
        markdown = _render_review_markdown(
            {
                "decision": "approved",
                "notes": "Proceed.",
                "implementation_authorized": True,
                "next_action": {
                    "command": "run implementation",
                    "reason": "Approved by operator.",
                },
            }
        )

        self.assertIn("# Mission Review", markdown)
        self.assertIn("approved", markdown)
        self.assertIn("Proceed.", markdown)
        self.assertIn("run implementation", markdown)
        self.assertIn("true", markdown)


if __name__ == "__main__":
    unittest.main()
