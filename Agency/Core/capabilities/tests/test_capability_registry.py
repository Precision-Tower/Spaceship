from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Agency.Core.agents.tooling.agent_spec import (
    build_agent_spec,
    validate_agent_spec,
)
from Agency.Core.agents.tooling.create_agent import render_action_policy_yaml
from Agency.Core.capabilities import (
    CAPABILITY_REGISTRY,
    CapabilityRegistryError,
    get_capability,
    require_capabilities,
    resolve_capabilities,
    resolve_policy_capabilities,
)


class CapabilityRegistryTest(unittest.TestCase):
    def test_engineering_is_registered_as_core_owned_capability(self) -> None:
        capability = get_capability("engineering")

        self.assertEqual("engineering", capability.name)
        self.assertEqual(
            "Agency.Core.capabilities.engineering",
            capability.runtime_owner,
        )
        self.assertIn("mission_create", capability.operations)
        self.assertIn("implement", capability.operations)
        self.assertIn("verify", capability.operations)

    def test_registry_rejects_unknown_capability(self) -> None:
        with self.assertRaises(CapabilityRegistryError):
            get_capability("definitely_not_a_capability")

    def test_registry_resolves_requested_capabilities_in_order(self) -> None:
        resolved = require_capabilities(
            ("read_context", "engineering", "prepare_handoff")
        )

        self.assertEqual(
            ("read_context", "engineering", "prepare_handoff"),
            tuple(item.name for item in resolved),
        )

    def test_resolver_returns_definitions_keyed_by_name(self) -> None:
        resolved = resolve_capabilities(
            ("read_context", "engineering", "prepare_handoff")
        )

        self.assertEqual(
            ("read_context", "engineering", "prepare_handoff"),
            tuple(resolved),
        )
        self.assertEqual(
            "Agency.Core.capabilities.engineering",
            resolved["engineering"].runtime_owner,
        )

    def test_resolver_rejects_duplicate_declarations(self) -> None:
        with self.assertRaisesRegex(
            CapabilityRegistryError,
            "duplicate capability declaration: engineering",
        ):
            resolve_capabilities(("engineering", "engineering"))

    def test_policy_capabilities_are_loaded_and_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy_path = Path(tmp) / "action_policy.yaml"
            policy_path.write_text(
                """CaliActionPolicy:
  capabilities:
    - read_context
    - engineering
""",
                encoding="utf-8",
            )

            resolved = resolve_policy_capabilities(policy_path, "Cali")

        self.assertEqual(("read_context", "engineering"), tuple(resolved))
        self.assertEqual(
            "Agency.Core.capabilities.engineering",
            resolved["engineering"].runtime_owner,
        )

    def test_agent_spec_accepts_engineering_capability(self) -> None:
        spec = build_agent_spec(
            name="CapabilityTestAgent",
            capabilities=("read_context", "engineering"),
        )

        errors = validate_agent_spec(spec)

        self.assertFalse(
            any("unknown capability: engineering" in error for error in errors),
            errors,
        )

    def test_factory_renders_engineering_into_action_policy(self) -> None:
        spec = build_agent_spec(
            name="CapabilityPolicyAgent",
            capabilities=("read_context", "engineering"),
        )

        rendered = render_action_policy_yaml(spec)

        self.assertIn("    - read_context", rendered)
        self.assertIn("    - engineering", rendered)

    def test_supported_registry_names_include_agent_spec_capabilities(self) -> None:
        self.assertIn("engineering", CAPABILITY_REGISTRY.names())


if __name__ == "__main__":
    unittest.main()
