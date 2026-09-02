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
from Agency.Core.capabilities.engineering.naming import normalize_agent_name
from Agency.Core.capabilities.engineering import paths as engineering_paths
from Agency.Core.capabilities.engineering import policy as engineering_policy
from Agency.Core.capabilities.engineering import packet as engineering_packet
from Agency.Core.capabilities.engineering import execution as engineering_execution
from Agency.Core.capabilities.engineering import apply as engineering_apply
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

def _agent_dir(agent_name: str) -> Path:
    return AGENTS_ROOT / normalize_agent_name(agent_name)

def _proposal_dir(agent_name: str) -> Path:
    return _agent_dir(agent_name) / "actions" / "proposals"

def _result_dir(agent_name: str) -> Path:
    return _agent_dir(agent_name) / "actions" / "results"

def _packet_path(agent_name: str, action_id: str) -> Path:
    return _proposal_dir(agent_name) / f"{action_id}.yaml"

def _result_path(agent_name: str, action_id: str) -> Path:
    return _result_dir(agent_name) / f"{action_id}_result.yaml"

def _load_yaml(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("invalid_action_document")

    return data

def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

def latest_packet_path(agent_name: str) -> Path:
    proposal_dir = _proposal_dir(agent_name)
    packets = sorted(proposal_dir.glob("*.yaml"), key=lambda path: path.stat().st_mtime)
    if not packets:
        raise FileNotFoundError(f"no action packets found for {normalize_agent_name(agent_name)}")
    return packets[-1]

def resolve_packet_arg(agent_name: str, packet_arg: str | None, latest: bool) -> Path:
    if latest:
        return latest_packet_path(agent_name)
    if not packet_arg:
        raise ValueError("missing_packet_path_or_latest")

    candidate = Path(packet_arg)
    if not candidate.is_absolute():
        by_agent = _proposal_dir(agent_name) / candidate
        if by_agent.exists():
            return by_agent
        candidate = DASHBOARD_ROOT / candidate

    resolved = candidate.resolve()
    if not _is_within(resolved, DASHBOARD_ROOT):
        raise ValueError(f"packet_outside_workspace_rejected: {packet_arg}")
    if ".." in Path(packet_arg).parts:
        raise ValueError(f"packet_path_traversal_rejected: {packet_arg}")
    return resolved

def _action_packet(data: dict[str, Any]) -> dict[str, Any]:
    packet = data.get("ActionPacket", data)
    if not isinstance(packet, dict):
        raise ValueError("invalid_action_packet")
    return packet

def _validate_packet_agent(packet: dict[str, Any], agent_name: str) -> str:
    expected = normalize_agent_name(agent_name)
    actual = normalize_agent_name(str(packet.get("agent", "")))
    if actual != expected:
        raise ValueError(f"packet_agent_mismatch: expected {expected}, got {actual}")
    return expected
