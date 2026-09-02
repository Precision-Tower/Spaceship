from __future__ import annotations

import ast
import inspect
import unittest

from Agency.Core.work.missions import mission_runtime
from Agency.Core.work.planning import proposal_generation


class ProposalGenerationExtractionTest(unittest.TestCase):
    def test_core_proposal_generation_does_not_import_mission_runtime(self) -> None:
        source = inspect.getsource(proposal_generation)
        self.assertNotIn("Agency.Agents.", source)

    def test_verified_proposal_functions_are_owned_by_core(self) -> None:
        core_functions = {
            name
            for name, value in vars(proposal_generation).items()
            if inspect.isfunction(value)
        }
        local_functions = {
            name
            for name, value in vars(mission_runtime).items()
            if inspect.isfunction(value)
            and value.__module__ == mission_runtime.__name__
        }
        expected = {
            "_load_proposal_inputs",
            "_assess_proposal_readiness",
            "_proposal_system_context",
            "_build_mission_proposal_prompt",
            "_plan_finding_ids",
            "_first_finding_ids",
            "_normalize_change_item",
            "_normalize_supported_by",
            "_normalize_proposal_acceptance_criteria",
            "_normalize_proposal_visual_checks",
            "_normalize_proposal_payload",
            "_validate_proposal",
            "_render_proposal_markdown",
            "_update_state_after_proposal",
            "_proposal_failure",
            "run_mission_propose",
        }
        self.assertTrue(expected <= core_functions)
        self.assertFalse((expected - {"run_mission_propose"}) & local_functions)


if __name__ == "__main__":
    unittest.main()
