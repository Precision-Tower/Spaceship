from __future__ import annotations

import ast
import inspect
import unittest
from dataclasses import fields

from Agency.Core.work.missions import mission_runtime
from Agency.Core.work.missions.pipeline.implementation import execution


class ImplementationExecutionExtractionTest(unittest.TestCase):
    def test_core_execution_does_not_import_mission_runtime(self) -> None:
        source = inspect.getsource(execution)
        self.assertNotIn("Agency.Agents.", source)

    def test_execution_functions_are_owned_by_core(self) -> None:
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
            "_load_implementation_inputs",
            "_normalize_implementation_units",
            "_implementation_execution_order",
            "_implementation_manifest_from_units",
            "_write_implementation_manifest",
            "_select_next_implementation_unit",
            "_validate_implementation_authority",
            "_capture_unit_file_context",
            "_build_implementation_prompt",
            "_normalize_implementation_response",
            "_validate_implementation_response",
            "_apply_file_changes",
            "_run_unit_verification",
            "_implementation_state_payload",
            "_record_implementation_unit_failure",
            "run_mission_implement",
        }
        self.assertTrue(expected <= core_functions)
        self.assertFalse((expected - {"run_mission_implement"}) & local_functions)

    def test_dependency_binder_supplies_every_declared_dependency(self) -> None:
        deps = mission_runtime._implementation_execution_dependencies()
        expected = {field.name for field in fields(execution.ImplementationExecutionDependencies)}
        self.assertEqual(expected, set(vars(deps)))


if __name__ == "__main__":
    unittest.main()
