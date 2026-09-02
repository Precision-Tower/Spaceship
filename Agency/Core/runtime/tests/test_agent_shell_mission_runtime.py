from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.work.missions import mission_runtime

AGENT_SHELL_PATH = Path(__file__).resolve().parents[1] / 'agent_shell.py'
_AGENT_SHELL_SPEC = importlib.util.spec_from_file_location(
    'agent_shell_mission_runtime_test_module',
    AGENT_SHELL_PATH,
)
agent_shell = importlib.util.module_from_spec(_AGENT_SHELL_SPEC)
assert _AGENT_SHELL_SPEC.loader is not None
_AGENT_SHELL_SPEC.loader.exec_module(agent_shell)


class AgentShellMissionRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "missions"
        self.root.mkdir(parents=True)
        self.patches = [
            patch.object(mission_runtime, "MISSIONS_ROOT", self.root),
            patch.object(
                mission_runtime,
                "agency_blocks_dependent_operations",
                return_value=[],
            ),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def run_shell(self, argv: list[str]) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = agent_shell.main("Scout", argv)
        return code, output.getvalue()

    def parse_json(self, text: str) -> dict:
        return json.loads(text)

    def test_argv_mission_lifecycle_uses_shared_runtime(self) -> None:
        code, created_text = self.run_shell([
            "mission",
            "create",
            "--intent",
            "Shell mission lifecycle",
            "--scope",
            "UI/Main",
        ])
        created = self.parse_json(created_text)

        status_code, status_text = self.run_shell([
            "mission",
            "status",
            "--mission",
            "1",
        ])
        inspect_code, inspect_text = self.run_shell([
            "mission",
            "inspect",
            "--mission",
            "1",
        ])
        listed_code, listed_text = self.run_shell([
            "mission",
            "list",
            "--raw",
        ])
        show_code, show_text = self.run_shell([
            "mission",
            "show",
            "1",
            "--raw",
        ])

        self.assertEqual(0, code)
        self.assertEqual("mission_created", created["status"])
        self.assertTrue((self.root / "mission-1" / "intent.json").exists())
        self.assertEqual(0, status_code)
        self.assertEqual("mission-1", self.parse_json(status_text)["mission_id"])
        self.assertEqual(0, inspect_code)
        self.assertEqual("mission-1", self.parse_json(inspect_text)["mission_id"])
        self.assertTrue((self.root / "mission-1" / "inspect" / "pass_001.json").exists())
        self.assertEqual(0, listed_code)
        self.assertEqual("mission-1", self.parse_json(listed_text)["missions"][0]["mission_id"])
        self.assertEqual(0, show_code)
        self.assertEqual("Shell mission lifecycle", self.parse_json(show_text)["intent"])


    def test_remaining_phase_commands_route_to_shared_runtime(self) -> None:
        self.run_shell([
            "mission",
            "create",
            "--intent",
            "Shell remaining phases",
            "--scope",
            "UI/Main",
        ])

        cases = [
            (["mission", "plan", "--mission", "1"], 1, "planning_not_ready"),
            (["mission", "resourcefulness", "--mission", "1"], 1, "resourcefulness_plan_required"),
            (["mission", "propose", "--mission", "1"], 1, "plan_required"),
            (["mission", "review", "--mission", "1", "--approve"], 1, "proposal_required"),
            (["mission", "implement", "--mission", "1"], 1, "proposal_required"),
            (["mission", "verify", "--mission", "1"], 1, "proposal_required"),
        ]
        for argv, expected_code, expected_status in cases:
            with self.subTest(argv=argv):
                code, text = self.run_shell(argv)
                self.assertEqual(expected_code, code)
                self.assertEqual(expected_status, self.parse_json(text)["status"])

        code, text = self.run_shell(["mission", "resume", "--mission", "1", "--raw"])
        self.assertEqual(0, code)
        self.assertEqual("mission-1", self.parse_json(text)["mission_id"])

    def test_slash_mission_command_routes_to_shared_runtime(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            raw, keep_running, code = agent_shell._handle_command(
                "/mission create --intent 'Slash mission' --scope UI/Main",
                raw=False,
            )

        self.assertFalse(raw)
        self.assertTrue(keep_running)
        self.assertEqual(0, code)
        self.assertTrue((self.root / "mission-1" / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
