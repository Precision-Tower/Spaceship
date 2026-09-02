from __future__ import annotations
import unittest
from Agency.Core.capabilities.context_bites import (
    BitePolicy,
    ValidationFeedback,
    run_investigation,
    run_refinement,
)

def answer(observed="fact", unresolved="unknown", proposal="candidate"):
    return f"""Observed:
- {observed}
Inferred:
- cautious
Unresolved:
- {unresolved}
Evidence:
- Agency/example.py:symbol
Next target:
Agency/next.py
Proposal:
{proposal}
"""

class ContextBitesTests(unittest.TestCase):
    def test_investigation_ready_on_second_bite(self):
        outputs = iter([answer(proposal="not ready"), answer(observed="new fact", proposal="ready")])
        result = run_investigation(
            objective="trace seam",
            repository_context="context",
            invoke=lambda _: next(outputs),
            ready=lambda item: item.proposal == "ready",
        )
        self.assertEqual("ready", result.status)
        self.assertEqual(2, len(result.artifacts))

    def test_investigation_escalates_without_information_gain(self):
        result = run_investigation(
            objective="trace seam",
            repository_context="context",
            invoke=lambda _: answer(),
            ready=lambda _: False,
            policy=BitePolicy(investigation_budget=3, minimum_information_gain=1),
        )
        self.assertEqual("no_information_gain", result.reason)

    def test_refinement_uses_validator_feedback(self):
        outputs = iter([answer(proposal="still bad"), answer(proposal="good")])
        def validate(candidate):
            return ValidationFeedback(candidate == "good", () if candidate == "good" else ("wrong scope",))
        result = run_refinement(
            objective="produce patch",
            candidate="bad",
            invoke=lambda _: next(outputs),
            validate=validate,
        )
        self.assertEqual("ready", result.status)
        self.assertEqual("good", result.final_output)

    # BEGIN patch_009b_candidate_extractor_tests
    def test_refinement_preserves_structured_proposal_default(self):
        outputs = iter([
            answer(proposal="still bad"),
            answer(proposal="good"),
        ])

        def validate(candidate):
            return ValidationFeedback(
                candidate == "good",
                () if candidate == "good" else ("wrong scope",),
            )

        result = run_refinement(
            objective="produce patch",
            candidate="bad",
            invoke=lambda _: next(outputs),
            validate=validate,
        )

        self.assertEqual("ready", result.status)
        self.assertEqual("good", result.final_output)
        self.assertEqual(2, len(result.artifacts))

    def test_refinement_can_extract_raw_response(self):
        responses = iter([
            "still bad",
            "good",
        ])

        def validate(candidate):
            return ValidationFeedback(
                candidate == "good",
                () if candidate == "good" else ("wrong scope",),
            )

        result = run_refinement(
            objective="produce patch",
            candidate="bad",
            invoke=lambda _: next(responses),
            validate=validate,
            candidate_extractor=lambda artifact: artifact.response,
        )

        self.assertEqual("ready", result.status)
        self.assertEqual("good", result.final_output)
        self.assertEqual("still bad", result.artifacts[0].response)
        self.assertEqual("", result.artifacts[0].proposal)

    def test_empty_extracted_candidate_preserves_current_candidate(self):
        calls = []

        def validate(candidate):
            calls.append(candidate)
            return ValidationFeedback(
                False,
                ("wrong scope",),
            )

        result = run_refinement(
            objective="produce patch",
            candidate="original",
            invoke=lambda _: "raw response",
            validate=validate,
            candidate_extractor=lambda _: "",
            policy=BitePolicy(refinement_budget=2),
        )

        self.assertEqual("escalated", result.status)
        self.assertEqual("repeated_same_failure", result.reason)
        self.assertEqual("original", result.final_output)
        self.assertEqual(
            ["original", "original", "original"],
            calls,
        )
    # END patch_009b_candidate_extractor_tests

    # BEGIN patch_009c_prompt_builder_tests
    def test_refinement_accepts_explicit_prompt_builder(self):
        prompts = []

        def build_prompt(
            objective,
            candidate,
            feedback,
            prior,
            number,
        ):
            self.assertEqual("produce patch", objective)
            self.assertEqual("bad", candidate)
            self.assertEqual(("wrong scope",), feedback.errors)
            self.assertEqual((), prior)
            self.assertEqual(1, number)
            return "RETURN ONLY THE REPAIRED CANDIDATE"

        def invoke(prompt):
            prompts.append(prompt)
            return "good"

        def validate(candidate):
            return ValidationFeedback(
                candidate == "good",
                () if candidate == "good" else ("wrong scope",),
            )

        result = run_refinement(
            objective="produce patch",
            candidate="bad",
            invoke=invoke,
            validate=validate,
            candidate_extractor=lambda artifact: artifact.response,
            prompt_builder=build_prompt,
        )

        self.assertEqual("ready", result.status)
        self.assertEqual("good", result.final_output)
        self.assertEqual(
            ["RETURN ONLY THE REPAIRED CANDIDATE"],
            prompts,
        )
        self.assertEqual(
            "RETURN ONLY THE REPAIRED CANDIDATE",
            result.artifacts[0].prompt,
        )

    def test_default_refinement_prompt_remains_structured(self):
        prompts = []

        def invoke(prompt):
            prompts.append(prompt)
            return answer(proposal="good")

        def validate(candidate):
            return ValidationFeedback(
                candidate == "good",
                () if candidate == "good" else ("wrong scope",),
            )

        result = run_refinement(
            objective="produce patch",
            candidate="bad",
            invoke=invoke,
            validate=validate,
        )

        self.assertEqual("ready", result.status)
        self.assertIn("Observed:", prompts[0])
        self.assertIn("Proposal:", prompts[0])
    # END patch_009c_prompt_builder_tests

if __name__ == "__main__":
    unittest.main()
