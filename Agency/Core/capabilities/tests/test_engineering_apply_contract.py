from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from Agency.Core.agents.tooling import agent_actions


def policy_result(
    *,
    decision: str = "review_required",
    approval_required: bool = True,
    review_required: bool = True,
    auto_apply_allowed: bool = False,
    blocked_rules: list[str] | None = None,
) -> dict[str, object]:
    return {
        "decision": decision,
        "risk": "workspace",
        "target_paths": ["scratch/example.txt"],
        "sandbox_paths": [],
        "core_paths": [],
        "blocked_rules": blocked_rules or [],
        "auto_apply_allowed": auto_apply_allowed,
        "review_required": review_required,
        "approval_required": approval_required,
    }


class EngineeringApplyContractTest(unittest.TestCase):
    def test_blocked_policy_stops_before_execution(self) -> None:
        packet = {
            "id": "cali_action_1",
            "agent": "Cali",
            "actions": [
                {
                    "type": "write_file",
                    "path": "forbidden/example.txt",
                    "content": "nope",
                }
            ],
            "review": {
                "status": "reviewed",
            },
        }

        output = io.StringIO()

        with patch.object(
            agent_actions,
            "resolve_packet_arg",
            return_value=Path("/tmp/packet.yaml"),
        ), patch.object(
            agent_actions,
            "_load_yaml",
            return_value={"ActionPacket": packet},
        ), patch.object(
            agent_actions,
            "evaluate_action_policy",
            return_value=policy_result(
                decision="blocked",
                blocked_rules=["forbidden/**"],
            ),
        ), patch.object(
            agent_actions,
            "_apply_action",
        ) as apply_action, redirect_stdout(output):
            status = agent_actions.apply_action_packet(
                "Cali",
                "packet.yaml",
                approved=True,
            )

        self.assertEqual(2, status)
        self.assertIn(
            "ACTION_APPLY_BLOCKED",
            output.getvalue(),
        )
        self.assertIn(
            "dangerous_path_blocked: forbidden/**",
            output.getvalue(),
        )
        apply_action.assert_not_called()

    def test_review_required_stops_before_execution(self) -> None:
        packet = {
            "id": "cali_action_2",
            "agent": "Cali",
            "actions": [
                {
                    "type": "write_file",
                    "path": "scratch/example.txt",
                    "content": "hello",
                }
            ],
            "review": {
                "status": "pending",
            },
        }

        output = io.StringIO()

        with patch.object(
            agent_actions,
            "resolve_packet_arg",
            return_value=Path("/tmp/packet.yaml"),
        ), patch.object(
            agent_actions,
            "_load_yaml",
            return_value={"ActionPacket": packet},
        ), patch.object(
            agent_actions,
            "evaluate_action_policy",
            return_value=policy_result(),
        ), patch.object(
            agent_actions,
            "_apply_action",
        ) as apply_action, redirect_stdout(output):
            status = agent_actions.apply_action_packet(
                "Cali",
                "packet.yaml",
                approved=True,
            )

        self.assertEqual(2, status)
        self.assertIn("reason: review_required", output.getvalue())
        self.assertIn(
            "python run.py agent action review Cali --latest",
            output.getvalue(),
        )
        apply_action.assert_not_called()

    def test_approval_required_stops_without_flag(self) -> None:
        packet = {
            "id": "cali_action_3",
            "agent": "Cali",
            "actions": [
                {
                    "type": "write_file",
                    "path": "scratch/example.txt",
                    "content": "hello",
                }
            ],
            "review": {
                "status": "reviewed",
            },
        }

        output = io.StringIO()

        with patch.object(
            agent_actions,
            "resolve_packet_arg",
            return_value=Path("/tmp/packet.yaml"),
        ), patch.object(
            agent_actions,
            "_load_yaml",
            return_value={"ActionPacket": packet},
        ), patch.object(
            agent_actions,
            "evaluate_action_policy",
            return_value=policy_result(),
        ), patch.object(
            agent_actions,
            "_apply_action",
        ) as apply_action, redirect_stdout(output):
            status = agent_actions.apply_action_packet(
                "Cali",
                "packet.yaml",
                approved=False,
            )

        self.assertEqual(2, status)
        self.assertIn(
            "reason: --approved required",
            output.getvalue(),
        )
        apply_action.assert_not_called()

    def test_success_updates_packet_and_writes_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_path = root / "packet.yaml"
            result_path = root / "result.yaml"

            packet = {
                "id": "cali_action_4",
                "agent": "Cali",
                "status": "proposed",
                "approved": False,
                "actions": [
                    {
                        "type": "write_file",
                        "path": "scratch/example.txt",
                        "content": "hello",
                    }
                ],
                "review": {
                    "status": "reviewed",
                },
            }

            policy = policy_result(
                decision="auto_apply_allowed",
                approval_required=False,
                review_required=False,
                auto_apply_allowed=True,
            )

            written: list[tuple[Path, dict[str, object]]] = []

            output = io.StringIO()

            with patch.object(
                agent_actions,
                "resolve_packet_arg",
                return_value=packet_path,
            ), patch.object(
                agent_actions,
                "_load_yaml",
                return_value={"ActionPacket": packet},
            ), patch.object(
                agent_actions,
                "evaluate_action_policy",
                return_value=policy,
            ), patch.object(
                agent_actions,
                "_apply_action",
                return_value={
                    "type": "write_file",
                    "status": "applied",
                    "path": "scratch/example.txt",
                    "bytes_written": 5,
                },
            ), patch.object(
                agent_actions,
                "_result_path",
                return_value=result_path,
            ), patch.object(
                agent_actions,
                "_write_yaml",
                side_effect=lambda path, data: written.append(
                    (Path(path), data)
                ),
            ), patch.object(
                agent_actions,
                "stable_path",
                side_effect=lambda path: Path(path).name,
            ), redirect_stdout(output):
                status = agent_actions.apply_action_packet(
                    "Cali",
                    "packet.yaml",
                    approved=False,
                )

            self.assertEqual(0, status)
            self.assertEqual("applied", packet["status"])
            self.assertFalse(packet["approved"])
            self.assertTrue(packet["auto_applied"])
            self.assertIn("applied_at", packet)
            self.assertIs(packet["policy"], policy)

            self.assertEqual(2, len(written))

            packet_write_path, packet_document = written[0]
            result_write_path, result_document = written[1]

            self.assertEqual(packet_path, packet_write_path)
            self.assertEqual(
                {"ActionPacket": packet},
                packet_document,
            )
            self.assertEqual(result_path, result_write_path)

            result = result_document["ActionResult"]

            self.assertEqual("cali_action_4", result["id"])
            self.assertEqual("Cali", result["agent"])
            self.assertEqual("applied", result["status"])
            self.assertEqual("packet.yaml", result["packet"])
            self.assertFalse(result["writes_approved"])
            self.assertTrue(result["auto_applied"])
            self.assertIs(result["policy"], policy)
            self.assertEqual(
                "scratch/example.txt",
                result["results"][0]["path"],
            )

            rendered = output.getvalue()

            self.assertIn("ACTION_APPLIED", rendered)
            self.assertIn("approval_used: false", rendered)
            self.assertIn("auto_applied: true", rendered)
            self.assertIn(
                "wrote: scratch/example.txt",
                rendered,
            )

    def test_execution_failure_returns_one(self) -> None:
        packet = {
            "id": "cali_action_5",
            "agent": "Cali",
            "actions": [
                {
                    "type": "write_file",
                    "path": "scratch/example.txt",
                    "content": "hello",
                }
            ],
            "review": {
                "status": "reviewed",
            },
        }

        output = io.StringIO()

        with patch.object(
            agent_actions,
            "resolve_packet_arg",
            return_value=Path("/tmp/packet.yaml"),
        ), patch.object(
            agent_actions,
            "_load_yaml",
            return_value={"ActionPacket": packet},
        ), patch.object(
            agent_actions,
            "evaluate_action_policy",
            return_value=policy_result(),
        ), patch.object(
            agent_actions,
            "_apply_action",
            side_effect=RuntimeError("disk_on_fire"),
        ), redirect_stdout(output):
            status = agent_actions.apply_action_packet(
                "Cali",
                "packet.yaml",
                approved=True,
            )

        self.assertEqual(1, status)
        self.assertIn("ACTION_APPLY_FAILED", output.getvalue())
        self.assertIn("reason: disk_on_fire", output.getvalue())


if __name__ == "__main__":
    unittest.main()
