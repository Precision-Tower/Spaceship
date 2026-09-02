import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import run


class DashboardCliRoutingTests(unittest.TestCase):
    def test_agent_action_help_reports_migration_state(self):
        output = io.StringIO()

        with redirect_stdout(output):
            status = run.run_agent_command(["action", "-h"])

        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn("propose uses WorkPackets.", text)
        self.assertIn(
            "review and apply still use legacy ActionPackets.",
            text,
        )
        self.assertIn(
            "python run.py work-packet --help",
            text,
        )

    def test_review_emits_legacy_notice(self):
        output = io.StringIO()

        with patch(
            "Agency.Core.agents.tooling.agent_actions.review_action_packet",
            return_value=0,
        ) as review, redirect_stdout(output):
            status = run.run_agent_command(
                ["action", "review", "Editor", "packet.yaml"]
            )

        self.assertEqual(status, 0)
        self.assertIn(
            "LEGACY_ACTION_PACKET_COMMAND",
            output.getvalue(),
        )
        self.assertIn("command: review", output.getvalue())
        review.assert_called_once_with(
            "Editor",
            packet_arg="packet.yaml",
            latest=False,
        )

    def test_apply_emits_legacy_notice(self):
        output = io.StringIO()

        with patch(
            "Agency.Core.agents.tooling.agent_actions.apply_action_packet",
            return_value=0,
        ) as apply_packet, redirect_stdout(output):
            status = run.run_agent_command(
                [
                    "action",
                    "apply",
                    "Editor",
                    "packet.yaml",
                    "--approved",
                ]
            )

        self.assertEqual(status, 0)
        self.assertIn(
            "LEGACY_ACTION_PACKET_COMMAND",
            output.getvalue(),
        )
        self.assertIn("command: apply", output.getvalue())
        apply_packet.assert_called_once_with(
            "Editor",
            packet_arg="packet.yaml",
            latest=False,
            approved=True,
        )

    def test_work_packet_command_delegates(self):
        with patch(
            "Agency.Core.work.work_packets.execution.main",
            return_value=0,
        ) as work_packet_main:
            status = run.run_work_packet_command(
                ["show", "packet-id"]
            )

        self.assertEqual(status, 0)
        work_packet_main.assert_called_once_with(
            ["show", "packet-id"]
        )

    def test_main_routes_work_packet_before_dashboard_parser(self):
        argv = [
            "run.py",
            "work-packet",
            "show",
            "packet-id",
        ]

        with patch.object(run.sys, "argv", argv), patch(
            "Agency.Core.work.work_packets.execution.main",
            return_value=0,
        ) as work_packet_main:
            status = run.main()

        self.assertEqual(status, 0)
        work_packet_main.assert_called_once_with(
            ["show", "packet-id"]
        )


if __name__ == "__main__":
    unittest.main()
