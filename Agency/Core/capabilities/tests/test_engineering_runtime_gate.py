from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from Agency.Core.runtime import agent_shell


class EngineeringRuntimeGateTest(unittest.TestCase):
    def test_propose_is_blocked_without_engineering_capability(self) -> None:
        with patch.object(agent_shell, "AGENT_CAPABILITIES", {}):
            output = io.StringIO()
            with redirect_stdout(output):
                code = agent_shell._propose("inspect repository", raw=False)

        self.assertEqual(2, code)
        self.assertIn(
            "Engineering capability is not enabled",
            output.getvalue(),
        )

    def test_apply_is_blocked_without_engineering_capability(self) -> None:
        with patch.object(agent_shell, "AGENT_CAPABILITIES", {}):
            with patch.object(agent_shell, "_review_latest") as review:
                output = io.StringIO()
                with redirect_stdout(output):
                    code = agent_shell._greenlight_latest(raw=False)

        self.assertEqual(2, code)
        review.assert_not_called()
        self.assertIn(
            "Engineering capability is not enabled",
            output.getvalue(),
        )

    def test_propose_delegates_when_engineering_is_enabled(self) -> None:
        sentinel = object()

        with patch.object(
            agent_shell,
            "AGENT_CAPABILITIES",
            {"engineering": sentinel},
        ):
            with patch.object(
                agent_shell,
                "_run_printing_command",
                return_value=0,
            ) as run_command:
                code = agent_shell._propose(
                    "inspect repository",
                    raw=False,
                )

        self.assertEqual(0, code)
        run_command.assert_called_once()

        function, agent_name, task = run_command.call_args.args
        self.assertEqual("propose_action", function.__name__)
        self.assertEqual(agent_shell.AGENT_NAME, agent_name)
        self.assertEqual("inspect repository", task)
        self.assertEqual(
            {"raw": False},
            run_command.call_args.kwargs,
        )


if __name__ == "__main__":
    unittest.main()
