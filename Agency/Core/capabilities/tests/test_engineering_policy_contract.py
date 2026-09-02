from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.agents.tooling import agent_actions


class EngineeringPolicyContractTest(unittest.TestCase):
    def test_workspace_path_rejects_traversal(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "path_traversal_rejected",
        ):
            agent_actions.resolve_workspace_path("../outside.txt")

    def test_core_path_requires_review_and_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)
            agents_root = dashboard_root / "Agency" / "Agents"
            agent_dir = agents_root / "Cali"
            agent_dir.mkdir(parents=True)

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "AGENTS_ROOT",
                agents_root,
            ):
                policy = agent_actions.evaluate_action_policy(
                    "Cali",
                    [
                        {
                            "type": "create_file",
                            "path": "Agency/example.txt",
                            "content": "hello",
                        }
                    ],
                )

        self.assertEqual("review_required", policy["decision"])
        self.assertEqual("core", policy["risk"])
        self.assertTrue(policy["review_required"])
        self.assertTrue(policy["approval_required"])
        self.assertFalse(policy["auto_apply_allowed"])

    def test_sandbox_path_allows_auto_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)
            agents_root = dashboard_root / "Agency" / "Agents"
            agent_dir = agents_root / "Cali"
            agent_dir.mkdir(parents=True)

            (agent_dir / "action_policy.yaml").write_text(
                """CaliActionPolicy:
  sandbox_paths:
    - scratch/
  core_paths:
    - Agency/
  blocked_paths:
    - .git/
""",
                encoding="utf-8",
            )

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "AGENTS_ROOT",
                agents_root,
            ):
                policy = agent_actions.evaluate_action_policy(
                    "Cali",
                    [
                        {
                            "type": "create_file",
                            "path": "scratch/example.txt",
                            "content": "hello",
                        }
                    ],
                )

        self.assertEqual("auto_apply_allowed", policy["decision"])
        self.assertEqual("low", policy["risk"])
        self.assertFalse(policy["review_required"])
        self.assertFalse(policy["approval_required"])
        self.assertTrue(policy["auto_apply_allowed"])

    def test_blocked_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)
            agents_root = dashboard_root / "Agency" / "Agents"
            agent_dir = agents_root / "Cali"
            agent_dir.mkdir(parents=True)

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "AGENTS_ROOT",
                agents_root,
            ):
                policy = agent_actions.evaluate_action_policy(
                    "Cali",
                    [
                        {
                            "type": "create_file",
                            "path": ".git/config",
                            "content": "nope",
                        }
                    ],
                )

        self.assertEqual("blocked", policy["decision"])
        self.assertEqual("blocked", policy["risk"])
        self.assertTrue(policy["blocked_rules"])
        self.assertFalse(policy["review_required"])
        self.assertFalse(policy["approval_required"])


if __name__ == "__main__":
    unittest.main()
