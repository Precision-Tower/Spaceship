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

from Agency.Core.capabilities.engineering import repository as engineering_repository

def resolve_workspace_path(raw_path: str) -> Path:
    return engineering_paths.resolve_workspace_path(
        raw_path,
        DASHBOARD_ROOT,
    )


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


def _format_diff(old_text: str, new_text: str, path: str) -> str:
    old_text = old_text.replace("\ufeff", "")
    new_text = new_text.replace("\ufeff", "")
    old_lines = [f"{line}\n" for line in old_text.splitlines()]
    new_lines = [f"{line}\n" for line in new_text.splitlines()]
    return "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )

def _review_block_for_action(action: dict[str, Any]) -> str:
    action_type = action.get("type")

    if action_type in {"create_file", "write_file"}:
        target = resolve_workspace_path(str(action.get("path", "")))
        rel = stable_path(target)
        new_text = str(action.get("content", ""))
        if target.exists():
            old_text = target.read_text(encoding="utf-8", errors="replace")
            diff = _format_diff(old_text, new_text, rel)
            return f"--- {action_type}: {rel} ---\n{diff or '(no content changes)'}"
        return f"--- {action_type}: {rel} ---\nnew file, {len(new_text.encode('utf-8'))} bytes"

    if action_type in {"apply_patch", "propose_patch"}:
        if "diff" in action:
            diff_text = str(action.get("diff", ""))
            label = "inline_diff"
        else:
            diff_path = resolve_workspace_path(str(action.get("diff_path", "")))
            diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
            label = stable_path(diff_path)
        return f"--- {action_type}: {label} ---\n{diff_text.rstrip()}"

    return f"--- unsupported action: {action_type} ---"

def review_action_packet(
    agent_name: str,
    packet_arg: str | None = None,
    *,
    latest: bool = False,
) -> int:
    try:
        packet_path = engineering_repository.resolve_packet_arg(agent_name, packet_arg, latest)
        data = engineering_repository._load_yaml(packet_path)
        packet = engineering_repository._action_packet(data)
        agent_name = engineering_repository._validate_packet_agent(packet, agent_name)
        actions = packet.get("actions") or []
        if not isinstance(actions, list) or not actions:
            raise ValueError("packet_has_no_actions")

        policy = evaluate_action_policy(agent_name, actions)
        packet["policy"] = policy

        print("ACTION_REVIEW")
        print(f"agent: {agent_name}")
        print(f"packet: {stable_path(packet_path)}")
        print(f"policy: {policy['decision']}")
        print(f"risk: {policy['risk']}")
        print(f"approval_required: {str(policy['approval_required']).lower()}")
        if policy["target_paths"]:
            print("targets:")
            for path in policy["target_paths"]:
                print(f"  - {path}")
        if policy["decision"] == "blocked":
            print(f"blocked_rules: {', '.join(policy['blocked_rules'])}")
            return 2

        print("changes:")
        for action in actions:
            print(_review_block_for_action(action).rstrip())

        packet["review"] = {
            "status": "reviewed",
            "reviewed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        engineering_repository._write_yaml(packet_path, {"ActionPacket": packet})
    except Exception as exc:
        print("ACTION_REVIEW_FAILED")
        print(f"reason: {exc}")
        return 1

    print("review_status: reviewed")
    return 0
