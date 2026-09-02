from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from Agency.Core.capabilities.engineering.paths import (
    packet_relative_path,
)


NormalizeAgentName = Callable[[str], str]
EvaluateActionPolicy = Callable[
    [str, list[dict[str, Any]]],
    dict[str, Any],
]


CREATE_OR_WRITE_RE = re.compile(
    r"^\s*(?P<verb>create|write)(?:\s+file)?\s+"
    r"(?P<path>[^\s]+)\s+containing(?:\s+exactly)?\s+"
    r"(?P<content>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)

PATCH_PATH_RE = re.compile(
    r"^\s*(?:propose|apply)\s+patch(?:\s+from)?\s+"
    r"(?P<path>[^\s]+)\s*$",
    re.IGNORECASE,
)


def _strip_outer_quotes(value: str) -> str:
    value = value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]

    return value


def parse_action(
    prompt: str,
    *,
    dashboard_root: Path,
) -> dict[str, Any]:
    create_match = CREATE_OR_WRITE_RE.match(prompt)

    if create_match:
        verb = create_match.group("verb").lower()

        target_path = packet_relative_path(
            create_match.group("path"),
            dashboard_root,
        )

        content = _strip_outer_quotes(
            create_match.group("content")
        )

        return {
            "type": (
                "create_file"
                if verb == "create"
                else "write_file"
            ),
            "path": target_path,
            "content": content,
            "overwrite": verb == "write",
        }

    patch_match = PATCH_PATH_RE.match(prompt)

    if patch_match:
        diff_path = packet_relative_path(
            patch_match.group("path"),
            dashboard_root,
        )

        return {
            "type": "apply_patch",
            "diff_path": diff_path,
        }

    raise ValueError(
        "unsupported_action_request: expected create/write "
        "file containing text or apply patch from <diff_path>"
    )


def build_action_packet(
    agent_name: str,
    prompt: str,
    *,
    dashboard_root: Path,
    normalize_agent_name: NormalizeAgentName,
    evaluate_action_policy: EvaluateActionPolicy,
) -> dict[str, Any]:
    normalized_name = normalize_agent_name(agent_name)

    now = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    action_id = (
        f"{normalized_name.lower()}_action_{now}"
    )

    action = parse_action(
        prompt,
        dashboard_root=dashboard_root,
    )

    policy = evaluate_action_policy(
        normalized_name,
        [action],
    )

    return {
        "ActionPacket": {
            "id": action_id,
            "agent": normalized_name,
            "status": "proposed",
            "authority": (
                "proposed_action_only_not_execution_authority"
            ),
            "created_at": time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "workspace_root": str(dashboard_root),
            "approval_required": bool(
                policy["approval_required"]
            ),
            "approved": False,
            "review": {
                "status": (
                    "not_required"
                    if not policy["review_required"]
                    else "pending"
                ),
                "reviewed_at": None,
            },
            "policy": policy,
            "prompt": prompt,
            "actions": [action],
            "safety": {
                "write_sandbox": str(dashboard_root),
                "normal_agent_ask_writes_files": False,
                "requires_apply_command": True,
                "requires_approved_flag": bool(
                    policy["approval_required"]
                ),
                "auto_apply_allowed": bool(
                    policy["auto_apply_allowed"]
                ),
            },
        }
    }
