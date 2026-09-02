from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.runtime import agent_shell


class RuntimeCapabilityConfigurationTest(unittest.TestCase):
    def test_configure_resolves_policy_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agency_root = Path(tmp) / "Agency"
            agent_dir = agency_root / "Agents" / "Cali"
            agent_dir.mkdir(parents=True)

            (agent_dir / "action_policy.yaml").write_text(
                """CaliActionPolicy:
  capabilities:
    - read_context
    - engineering
""",
                encoding="utf-8",
            )

            with patch.object(agent_shell, "AGENCY_ROOT", agency_root):
                agent_shell.configure("Cali")
                payload = agent_shell.status()

        self.assertEqual(
            ["read_context", "engineering"],
            payload["capabilities"],
        )
        self.assertEqual(
            "Agency.Core.capabilities.engineering",
            agent_shell.AGENT_CAPABILITIES[
                "engineering"
            ].runtime_owner,
        )

    def test_existing_policy_without_capabilities_resolves_no_capabilities(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agency_root = Path(tmp) / "Agency"
            agent_dir = agency_root / "Agents" / "Cali"
            agent_dir.mkdir(parents=True)

            (agent_dir / "action_policy.yaml").write_text(
                """CaliActionPolicy:
  owner: Cali
""",
                encoding="utf-8",
            )

            with patch.object(agent_shell, "AGENCY_ROOT", agency_root):
                agent_shell.configure("Cali")
                payload = agent_shell.status()

        self.assertEqual([], payload["capabilities"])


    def test_missing_policy_resolves_no_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agency_root = Path(tmp) / "Agency"

            with patch.object(agent_shell, "AGENCY_ROOT", agency_root):
                agent_shell.configure("BareAgent")
                payload = agent_shell.status()

        self.assertEqual([], payload["capabilities"])


if __name__ == "__main__":
    unittest.main()
