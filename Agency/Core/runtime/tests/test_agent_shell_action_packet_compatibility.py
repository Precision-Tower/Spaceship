import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from Agency.Core.runtime import agent_shell


class AgentShellActionPacketCompatibilityTests(unittest.TestCase):
    def test_review_latest_emits_legacy_notice_once(self):
        output = io.StringIO()

        with patch(
            "Agency.Core.agents.tooling.agent_actions.review_action_packet",
            return_value=0,
        ) as review, redirect_stdout(output):
            status = agent_shell._review_latest(raw=False)

        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertEqual(
            1,
            text.count("LEGACY_ACTION_PACKET_COMMAND"),
        )
        self.assertIn("command: /review latest", text)
        self.assertIn("preferred_model: WorkPacket", text)
        review.assert_called_once_with(
            agent_shell.AGENT_NAME,
            latest=True,
        )

    def test_apply_latest_emits_legacy_notice_once(self):
        output = io.StringIO()

        with patch.object(
            agent_shell,
            "AGENT_CAPABILITIES",
            {"engineering"},
        ), patch(
            "Agency.Core.agents.tooling.agent_actions.review_action_packet",
            return_value=0,
        ) as review, patch(
            "Agency.Core.agents.tooling.agent_actions.apply_action_packet",
            return_value=0,
        ) as apply_packet, redirect_stdout(output):
            status = agent_shell._apply_latest(raw=False)

        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertEqual(
            1,
            text.count("LEGACY_ACTION_PACKET_COMMAND"),
        )
        self.assertIn("command: /apply latest", text)
        review.assert_called_once_with(
            agent_shell.AGENT_NAME,
            latest=True,
        )
        apply_packet.assert_called_once_with(
            agent_shell.AGENT_NAME,
            latest=True,
            approved=True,
        )

    def test_greenlight_latest_emits_legacy_notice_once(self):
        output = io.StringIO()

        with patch.object(
            agent_shell,
            "AGENT_CAPABILITIES",
            {"engineering"},
        ), patch(
            "Agency.Core.agents.tooling.agent_actions.review_action_packet",
            return_value=0,
        ), patch(
            "Agency.Core.agents.tooling.agent_actions.apply_action_packet",
            return_value=0,
        ), redirect_stdout(output):
            status = agent_shell._greenlight_latest(
                raw=False,
                command="/greenlight latest",
            )

        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertEqual(
            1,
            text.count("LEGACY_ACTION_PACKET_COMMAND"),
        )
        self.assertIn("command: /greenlight latest", text)

    def test_greenlight_blocks_apply_when_review_fails(self):
        output = io.StringIO()

        with patch.object(
            agent_shell,
            "AGENT_CAPABILITIES",
            {"engineering"},
        ), patch(
            "Agency.Core.agents.tooling.agent_actions.review_action_packet",
            return_value=2,
        ), patch(
            "Agency.Core.agents.tooling.agent_actions.apply_action_packet",
        ) as apply_packet, redirect_stdout(output):
            status = agent_shell._greenlight_latest(
                raw=False,
                command="/greenlight latest",
            )

        self.assertEqual(status, 2)
        self.assertIn(
            "Greenlight blocked until review succeeds.",
            output.getvalue(),
        )
        apply_packet.assert_not_called()


if __name__ == "__main__":
    unittest.main()
