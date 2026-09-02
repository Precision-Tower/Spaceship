"""Engineering implementation extracted from agent_actions."""
from __future__ import annotations

import re
import subprocess
import time
import difflib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from Agency.Core.foundation.paths import AGENTS_ROOT, DASHBOARD_ROOT, stable_path
from Agency.Core.capabilities.engineering import policy as engineering_policy
ACTION_ID_RE = re.compile(r"[^A-Za-z0-9_]+")
CREATE_OR_WRITE_RE = re.compile(
    r"^\s*(?P<verb>create|write)(?:\s+file)?\s+"
    r"(?P<path>[^\s]+)\s+containing(?:\s+exactly)?\s+"
    r"(?P<content>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
PATCH_PATH_RE = re.compile(
    r"^\s*(?:propose|apply)\s+patch(?:\s+from)?\s+(?P<path>[^\s]+)\s*$",
    re.IGNORECASE,
)

from Agency.Core.capabilities.engineering.naming import normalize_agent_name
from Agency.Core.capabilities.engineering import repository as engineering_repository
from Agency.Core.capabilities.engineering.parser import EngineeringParser
from Agency.Core.work.work_packets.proposal_contracts import (
    PROPOSAL_CAPABILITIES,
)
from Agency.Core.work.work_packets.proposals import create_proposal

def evaluate_action_policy(
    agent_name: str,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return engineering_policy.evaluate_action_policy(
        agent_name,
        actions,
        agents_root=AGENTS_ROOT,
        dashboard_root=DASHBOARD_ROOT,
        normalize_agent_name=normalize_agent_name,
        stable_path=stable_path,
    )


def propose_action(agent_name: str, prompt: str) -> int:
    agent_name = normalize_agent_name(agent_name)
    agent_dir = engineering_repository._agent_dir(agent_name)

    if not agent_dir.exists():
        print(f"ERR: agent not found: {agent_name}")
        return 1

    try:
        request = EngineeringParser.parse(prompt)
    except ValueError as exc:
        print(f"ACTION_PROPOSAL_BLOCKED: {exc}")
        return 2

    payload = create_proposal(
        play_owner=agent_name,
        request=request,
    )

    if not payload.get("ok"):
        print("ACTION_PROPOSAL_BLOCKED")
        print(f"reason: {payload.get('code', 'proposal_rejected')}")
        print(f"operation: {payload.get('intent', 'unknown')}")

        for error in payload.get("errors", []):
            print(f"error: {error}")

        print("supported_syntax:")
        for capability in PROPOSAL_CAPABILITIES.values():
            if capability["enabled"]:
                print(f"  - {capability['syntax']}")

        unavailable = [
            kind.value
            for kind, capability in PROPOSAL_CAPABILITIES.items()
            if not capability["enabled"]
        ]

        if unavailable:
            print("recognized_but_unavailable:")
            for intent in unavailable:
                print(f"  - {intent}")

        return 2

    print("ACTION_PROPOSED")
    print(f"agent: {agent_name}")
    print(f"packet_id: {payload['packet_id']}")
    print(f"packet: {payload['persistence_path']}")
    print(f"status: {payload['status']}")
    print(f"intent: {payload['proposal_intent']}")
    print("writes_performed: false")
    return 0
