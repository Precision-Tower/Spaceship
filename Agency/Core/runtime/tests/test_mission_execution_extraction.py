from __future__ import annotations

import argparse
import unittest
from unittest import mock

from Agency.Core.runtime import resourcefulness
from Agency.Core.runtime import resourcefulness
from Agency.Core.runtime.mission_execution import (
    MissionExecutionHandlers,
    build_mission_execution_parser,
    run_mission_execution_commands,
)
import run as run_py


class MissionExecutionExtractionTest(unittest.TestCase):
    def make_handlers(self, calls: list[tuple[str, argparse.Namespace]]) -> MissionExecutionHandlers:
        def handler(name: str):
            def _run(args: argparse.Namespace) -> int:
                calls.append((name, args))
                return 0
            return _run

        return MissionExecutionHandlers(
            status=handler("status"),
            inspect=handler("inspect"),
            pinboard_refresh=handler("pinboard_refresh"),
            propose=handler("propose"),
            mission_create=handler("mission_create"),
            mission_status=handler("mission_status"),
            mission_list=handler("mission_list"),
            mission_show=handler("mission_show"),
            mission_resume=handler("mission_resume"),
            mission_inspect=handler("mission_inspect"),
            mission_plan=handler("mission_plan"),
            mission_replan=handler("mission_replan"),
            mission_resourcefulness=handler("mission_resourcefulness"),
            mission_propose=handler("mission_propose"),
            mission_review=handler("mission_review"),
            mission_implement=handler("mission_implement"),
            mission_verify=handler("mission_verify"),
        )

    def test_resourcefulness_runtime_module_is_authoritative_with_legacy_shim(self) -> None:
        self.assertIs(resourcefulness.ResourcefulnessContext, resourcefulness.ResourcefulnessContext)
        self.assertIs(resourcefulness.ResourcefulnessPlanner, resourcefulness.ResourcefulnessPlanner)
        self.assertIs(resourcefulness.default_planner, resourcefulness.default_planner)

    def test_runtime_mission_execution_dispatches_to_supplied_handlers(self) -> None:
        calls: list[tuple[str, argparse.Namespace]] = []
        handlers = self.make_handlers(calls)

        code = run_mission_execution_commands(
            ["mission", "resourcefulness", "--mission", "mission-1"],
            handlers,
        )

        self.assertEqual(0, code)
        self.assertEqual("mission_resourcefulness", calls[0][0])
        self.assertEqual("mission-1", calls[0][1].mission)

    def test_run_py_dispatches_named_agent_through_live_discovery(self) -> None:
        with mock.patch(
            "Agency.Core.agents.discovery.launch_agent",
            return_value=17,
        ) as routed:
            code = run_py.run_agent_command(["ExampleAgent", "status"])

        self.assertEqual(17, code)
        routed.assert_called_once_with("ExampleAgent", ["status"])

    def test_runtime_parser_exposes_existing_mission_command_surface(self) -> None:
        parser = build_mission_execution_parser(self.make_handlers([]))
        command_names: set[str] = set()
        mission_names: set[str] = set()
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if choices:
                command_names.update(choices.keys())
                mission_parser = choices.get("mission")
                for mission_action in mission_parser._actions:
                    mission_choices = getattr(mission_action, "choices", None)
                    if mission_choices:
                        mission_names.update(mission_choices.keys())

        self.assertEqual(
            {"status", "inspect", "pinboard-refresh", "propose", "mission"},
            command_names,
        )
        self.assertEqual(
            {
                "create",
                "status",
                "list",
                "show",
                "resume",
                "inspect",
                "plan",
                "replan",
                "resourcefulness",
                "propose",
                "review",
                "implement",
                "verify",
            },
            mission_names,
        )


if __name__ == "__main__":
    unittest.main()
