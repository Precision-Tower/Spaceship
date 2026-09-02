from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.agents.tooling import agent_actions


def policy_result(
    *,
    decision: str = "review_required",
    risk: str = "workspace",
    approval_required: bool = True,
    review_required: bool = True,
    auto_apply_allowed: bool = False,
) -> dict[str, object]:
    return {
        "policy_file": "Agency/Agents/Atlas/action_policy.yaml",
        "decision": decision,
        "risk": risk,
        "target_paths": [],
        "sandbox_paths": [],
        "core_paths": [],
        "blocked_rules": [],
        "auto_apply_allowed": auto_apply_allowed,
        "review_required": review_required,
        "approval_required": approval_required,
    }


class EngineeringPacketContractTest(unittest.TestCase):
    def test_builds_create_file_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "evaluate_action_policy",
                return_value=policy_result(),
            ):
                document = agent_actions.build_action_packet(
                    "atlas",
                    "create file scratch/example.txt containing hello",
                )

        packet = document["ActionPacket"]

        self.assertEqual("Atlas", packet["agent"])
        self.assertEqual("proposed", packet["status"])
        self.assertEqual(
            "proposed_action_only_not_execution_authority",
            packet["authority"],
        )
        self.assertEqual(str(dashboard_root), packet["workspace_root"])
        self.assertEqual(
            [
                {
                    "type": "create_file",
                    "path": "scratch/example.txt",
                    "content": "hello",
                    "overwrite": False,
                }
            ],
            packet["actions"],
        )
        self.assertRegex(
            packet["id"],
            re.compile(
                r"^atlas_action_\d{8}_\d{6}_\d{6}$"
            ),
        )

    def test_builds_patch_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "evaluate_action_policy",
                return_value=policy_result(),
            ):
                document = agent_actions.build_action_packet(
                    "Atlas",
                    "apply patch from scratch/change.diff",
                )

        packet = document["ActionPacket"]

        self.assertEqual(
            [
                {
                    "type": "apply_patch",
                    "diff_path": "scratch/change.diff",
                }
            ],
            packet["actions"],
        )

    def test_policy_controls_review_and_safety_metadata(self) -> None:
        policy = policy_result(
            decision="auto_apply_allowed",
            risk="low",
            approval_required=False,
            review_required=False,
            auto_apply_allowed=True,
        )

        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "evaluate_action_policy",
                return_value=policy,
            ) as evaluate:
                document = agent_actions.build_action_packet(
                    "Atlas",
                    "write file scratch/example.txt containing updated",
                )

        packet = document["ActionPacket"]

        evaluate.assert_called_once_with(
            "Atlas",
            [
                {
                    "type": "write_file",
                    "path": "scratch/example.txt",
                    "content": "updated",
                    "overwrite": True,
                }
            ],
        )

        self.assertIs(packet["policy"], policy)
        self.assertFalse(packet["approval_required"])
        self.assertFalse(packet["approved"])
        self.assertEqual(
            {
                "status": "not_required",
                "reviewed_at": None,
            },
            packet["review"],
        )
        self.assertEqual(
            {
                "write_sandbox": str(dashboard_root),
                "normal_agent_ask_writes_files": False,
                "requires_apply_command": True,
                "requires_approved_flag": False,
                "auto_apply_allowed": True,
            },
            packet["safety"],
        )


if __name__ == "__main__":
    unittest.main()
