from __future__ import annotations

from copy import deepcopy

import ast
import inspect
import unittest

from Agency.Core.work.missions import mission_runtime
from Agency.Core.work.planning import mission_planning, prompting


class MissionPlanningExtractionTest(unittest.TestCase):
    def test_core_planning_does_not_import_mission_runtime(self) -> None:
        source = inspect.getsource(mission_planning)
        self.assertNotIn("Agency.Agents.", source)

    def test_verified_planning_functions_are_owned_by_core(self) -> None:
        core_functions = {
            name
            for name, value in vars(mission_planning).items()
            if inspect.isfunction(value)
        }
        local_functions = {
            name
            for name, value in vars(mission_runtime).items()
            if inspect.isfunction(value)
            and value.__module__ == mission_runtime.__name__
        }
        expected = {
            "_load_inspection_passes",
            "_load_optional_knowledge_artifacts",
            "_load_mission_artifacts",
            "_normalize_inspection_evidence",
            "_assess_planning_readiness",
            "_planning_system_context",
            "_build_planning_context",
            "first_evidence_ref",
            "normalize_evidence_refs",
            "_normalize_plan_payload",
            "_validate_plan_payload",
            "_render_plan_markdown",
            "_update_state_after_plan",
            "_planning_failure",
            "_execute_mission_planning",
        }
        self.assertTrue(expected <= core_functions)
        self.assertFalse(expected & local_functions)



class PlanningPromptBuilderTests(unittest.TestCase):
    def _base_context(self) -> dict[str, object]:
        return {
            "mission_id": "mission-1",
            "intent": "Verify extraction",
            "coverage_summary": {},
            "inspection_status": {},
            "resourcefulness_context": [],
            "high_value_observations": [],
            "inspected_file_inventory": [],
            "declared_scopes": [],
            "next_files": [],
            "coverage_unresolved": [],
            "operator_notes": "",
        }

    def test_prompt_builder_does_not_mutate_context(self) -> None:
        context = self._base_context()
        original = deepcopy(context)

        prompt, metadata = prompting.build_planning_prompt(context)

        self.assertIsInstance(prompt, str)
        self.assertIsInstance(metadata, dict)
        self.assertEqual(context, original)

    def test_prompt_builder_reports_prompt_size(self) -> None:
        context = self._base_context()

        prompt, metadata = prompting.build_planning_prompt(context)

        self.assertEqual(metadata["planning_prompt_size"], len(prompt))

    def test_prompt_builder_without_resourcefulness_has_no_diagnostics(
        self,
    ) -> None:
        context = self._base_context()

        _, metadata = prompting.build_planning_prompt(context)

        self.assertNotIn(
            "resourcefulness_compression_diagnostics",
            metadata,
        )

if __name__ == "__main__":
    unittest.main()
