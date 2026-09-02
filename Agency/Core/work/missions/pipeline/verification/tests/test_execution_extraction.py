from __future__ import annotations

import ast
import inspect
import unittest
from dataclasses import fields

from Agency.Core.work.missions import mission_runtime
from Agency.Core.work.missions.pipeline.verification import execution


class VerificationExecutionExtractionTest(unittest.TestCase):
    def test_core_execution_does_not_import_mission_runtime(self) -> None:
        source = inspect.getsource(execution)
        self.assertNotIn("Agency.Agents.", source)

    def test_verification_functions_are_owned_by_core(self) -> None:
        core_functions = {
            name
            for name, value in vars(execution).items()
            if inspect.isfunction(value)
        }
        local_functions = {
            name
            for name, value in vars(mission_runtime).items()
            if inspect.isfunction(value)
            and value.__module__ == mission_runtime.__name__
        }
        expected = {
            "_validate_verification_readiness",
            "_assess_implementation_unit_artifacts",
            "_compare_file_integrity",
            "_collect_visual_capture_requests",
            "_execute_visual_capture",
            "_collect_verification_evidence",
            "_validate_evidence_manifest",
            "_run_final_verification_commands",
            "_assess_acceptance_criteria",
            "_build_verification_report",
            "_write_verification_artifacts",
            "_update_state_after_verification",
            "run_mission_verify",
        }
        self.assertTrue(expected <= core_functions)
        self.assertFalse((expected - {"run_mission_verify"}) & local_functions)

    def test_dependency_binder_supplies_every_declared_dependency(self) -> None:
        deps = mission_runtime._verification_execution_dependencies()
        expected = {field.name for field in fields(execution.VerificationExecutionDependencies)}
        self.assertEqual(expected, set(vars(deps)))


if __name__ == "__main__":
    unittest.main()
