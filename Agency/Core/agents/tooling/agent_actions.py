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
from Agency.Core.capabilities.engineering import paths as engineering_paths
from Agency.Core.capabilities.engineering import policy as engineering_policy
from Agency.Core.capabilities.engineering import packet as engineering_packet
from Agency.Core.capabilities.engineering import execution as engineering_execution
from Agency.Core.capabilities.engineering import apply as engineering_apply
from Agency.Core.capabilities.engineering import repository as engineering_repository
from Agency.Core.capabilities.engineering import proposal as engineering_proposal
from Agency.Core.capabilities.engineering import review as engineering_review


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


def normalize_agent_name(raw: str) -> str:
    cleaned = ACTION_ID_RE.sub("", raw.strip())
    if not cleaned:
        raise ValueError("agent_name_empty")
    return cleaned[:1].upper() + cleaned[1:]


def _strip_outer_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def resolve_workspace_path(raw_path: str) -> Path:
    return engineering_paths.resolve_workspace_path(
        raw_path,
        DASHBOARD_ROOT,
    )


def _packet_rel_path(path: str) -> str:
    return engineering_paths.packet_relative_path(
        path,
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


def _parse_action(prompt: str) -> dict[str, Any]:
    return engineering_packet.parse_action(
        prompt,
        dashboard_root=DASHBOARD_ROOT,
    )


def build_action_packet(
    agent_name: str,
    prompt: str,
) -> dict[str, Any]:
    return engineering_packet.build_action_packet(
        agent_name,
        prompt,
        dashboard_root=DASHBOARD_ROOT,
        normalize_agent_name=normalize_agent_name,
        evaluate_action_policy=evaluate_action_policy,
    )


def _write_file_action(
    action: dict[str, Any],
) -> dict[str, Any]:
    return engineering_execution.write_file_action(
        action,
        resolve_workspace_path=resolve_workspace_path,
        stable_path=stable_path,
    )


def _diff_paths(diff_text: str) -> list[str]:
    return engineering_paths.diff_paths(diff_text)


def _validate_diff_paths(diff_text: str) -> None:
    return engineering_execution.validate_diff_paths(
        diff_text,
        diff_paths=_diff_paths,
        resolve_workspace_path=resolve_workspace_path,
    )


def _git_apply_base() -> tuple[Path, list[str]]:
    return engineering_execution.git_apply_base(
        dashboard_root=DASHBOARD_ROOT,
        run=subprocess.run,
    )


def _patch_action(
    action: dict[str, Any],
) -> dict[str, Any]:
    return engineering_execution.patch_action(
        action,
        resolve_workspace_path=resolve_workspace_path,
        stable_path=stable_path,
        validate_diff_paths=_validate_diff_paths,
        git_apply_base=_git_apply_base,
        run=subprocess.run,
    )


def _apply_action(
    action: dict[str, Any],
) -> dict[str, Any]:
    return engineering_execution.apply_action(
        action,
        write_file_action=_write_file_action,
        patch_action=_patch_action,
    )


def apply_action_packet(
    agent_name: str,
    packet_arg: str | None = None,
    *,
    latest: bool = False,
    approved: bool = False,
) -> int:
    return engineering_apply.apply_action_packet(
        agent_name,
        packet_arg,
        latest=latest,
        approved=approved,
        resolve_packet_arg=resolve_packet_arg,
        load_document=_load_yaml,
        action_packet=_action_packet,
        validate_packet_agent=_validate_packet_agent,
        evaluate_action_policy=evaluate_action_policy,
        apply_action=_apply_action,
        write_document=_write_yaml,
        result_path=_result_path,
        stable_path=stable_path,
    )

# Compatibility façade; implementation lives in Engineering.

def _agent_dir(*args, **kwargs):
    return engineering_repository._agent_dir(*args, **kwargs)

def _proposal_dir(*args, **kwargs):
    return engineering_repository._proposal_dir(*args, **kwargs)

def _result_dir(*args, **kwargs):
    return engineering_repository._result_dir(*args, **kwargs)

def _packet_path(*args, **kwargs):
    return engineering_repository._packet_path(*args, **kwargs)

def _result_path(*args, **kwargs):
    return engineering_repository._result_path(*args, **kwargs)

def _load_yaml(*args, **kwargs):
    return engineering_repository._load_yaml(*args, **kwargs)

def _write_yaml(*args, **kwargs):
    return engineering_repository._write_yaml(*args, **kwargs)

def latest_packet_path(*args, **kwargs):
    return engineering_repository.latest_packet_path(*args, **kwargs)

def resolve_packet_arg(*args, **kwargs):
    return engineering_repository.resolve_packet_arg(*args, **kwargs)

def _action_packet(*args, **kwargs):
    return engineering_repository._action_packet(*args, **kwargs)

def _validate_packet_agent(*args, **kwargs):
    return engineering_repository._validate_packet_agent(*args, **kwargs)

# Compatibility façade; implementation lives in Engineering.

def propose_action(*args, **kwargs):
    return engineering_proposal.propose_action(*args, **kwargs)

# Compatibility façade; implementation lives in Engineering.

def _format_diff(*args, **kwargs):
    return engineering_review._format_diff(*args, **kwargs)

def _review_block_for_action(*args, **kwargs):
    return engineering_review._review_block_for_action(*args, **kwargs)

def review_action_packet(*args, **kwargs):
    return engineering_review.review_action_packet(*args, **kwargs)

