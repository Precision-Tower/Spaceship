from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.capabilities.base import CapabilityDefinition
from Agency.Core.capabilities.registry import resolve_capabilities


def resolve_policy_capabilities(
    policy_path: Path,
    agent_name: str,
) -> dict[str, CapabilityDefinition]:
    """Load and resolve capabilities declared by one agent policy."""

    data: dict[str, Any] = (
        yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    )

    policy = data.get(f"{agent_name}ActionPolicy")
    if not isinstance(policy, dict):
        policy = data.get("ActionPolicy")

    if not isinstance(policy, dict):
        raise ValueError(f"action policy not found for agent: {agent_name}")

    declared = policy.get("capabilities", [])
    if not isinstance(declared, list):
        raise ValueError("action policy capabilities must be a list")

    return resolve_capabilities(str(name) for name in declared)
