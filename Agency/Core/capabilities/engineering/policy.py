from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.capabilities.engineering.paths import (
    diff_paths,
    packet_relative_path,
    resolve_workspace_path,
)


NormalizeAgentName = Callable[[str], str]
StablePath = Callable[[Path], str]


def default_action_policy() -> dict[str, Any]:
    return {
        "default_decision": "review_required",
        "sandbox_paths": [],
        "core_paths": [
            "Agency/",
            "UI/",
            "Engineering/",
            "CE-OS/",
            "screen/",
            "run.py",
            "lineage.md",
        ],
        "blocked_paths": [
            ".git/",
            ".godot/",
            ".env",
            ".env.local",
            "Agency/Archive/",
            "Agency/Agents/*/runtime/",
            "Agency/Agents/*/work/",
            "local/*.gguf",
            "local/*.bin",
            "local/*.safetensors",
        ],
    }


def normalize_policy_shape(
    policy: dict[str, Any],
) -> dict[str, Any]:
    normalized = default_action_policy()
    normalized.update(
        {
            key: value
            for key, value in policy.items()
            if value is not None
        }
    )

    decision = str(
        normalized.get(
            "default_decision",
            "review_required",
        )
    )
    direct_mutation = str(
        normalized.get(
            "direct_source_mutation",
            "",
        )
    )

    if (
        decision in {"mutation_forbidden", "blocked"}
        or direct_mutation == "forbidden"
    ):
        normalized["sandbox_paths"] = []
        normalized["blocked_paths"] = sorted(
            set(
                [
                    *normalized.get("blocked_paths", []),
                    "*",
                ]
            )
        )

    return normalized


def policy_path(
    agent_name: str,
    *,
    agents_root: Path,
    normalize_agent_name: NormalizeAgentName,
) -> Path:
    return (
        agents_root
        / normalize_agent_name(agent_name)
        / "action_policy.yaml"
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    data = (
        yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
        or {}
    )
    return data if isinstance(data, dict) else {}


def load_policy(
    agent_name: str,
    *,
    agents_root: Path,
    normalize_agent_name: NormalizeAgentName,
) -> dict[str, Any]:
    normalized_name = normalize_agent_name(agent_name)
    path = policy_path(
        normalized_name,
        agents_root=agents_root,
        normalize_agent_name=normalize_agent_name,
    )

    if path.exists():
        data = _load_yaml(path)
        policy_keys = (
            f"{normalized_name}ActionPolicy",
            "ActionPolicy",
            "CaliActionPolicy",
        )

        for key in policy_keys:
            policy = data.get(key, {})
            if isinstance(policy, dict) and policy:
                return normalize_policy_shape(policy)

    return default_action_policy()


def normalize_relative_path(value: str) -> str:
    return (
        value
        .replace("\\", "/")
        .strip()
        .lstrip("./")
    )


def path_matches_rule(
    path: str,
    rule: str,
) -> bool:
    path = normalize_relative_path(path)
    rule = normalize_relative_path(rule)

    if not rule:
        return False

    if any(token in rule for token in "*?["):
        return fnmatch.fnmatch(path, rule)

    if rule.endswith("/"):
        return path.startswith(rule)

    return (
        path == rule
        or path.startswith(f"{rule}/")
    )


def action_target_paths(
    action: dict[str, Any],
    *,
    dashboard_root: Path,
) -> list[str]:
    action_type = action.get("type")

    if action_type in {"create_file", "write_file"}:
        return [
            packet_relative_path(
                str(action.get("path", "")),
                dashboard_root,
            )
        ]

    if action_type in {
        "apply_patch",
        "propose_patch",
    }:
        if "diff" in action:
            diff_text = str(action.get("diff", ""))
        else:
            diff_path = resolve_workspace_path(
                str(action.get("diff_path", "")),
                dashboard_root,
            )

            if not diff_path.exists():
                return []

            diff_text = diff_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        return sorted(
            {
                packet_relative_path(
                    path,
                    dashboard_root,
                )
                for path in diff_paths(diff_text)
            }
        )

    return []


def evaluate_action_policy(
    agent_name: str,
    actions: list[dict[str, Any]],
    *,
    agents_root: Path,
    dashboard_root: Path,
    normalize_agent_name: NormalizeAgentName,
    stable_path: StablePath,
) -> dict[str, Any]:
    normalized_name = normalize_agent_name(agent_name)

    policy = load_policy(
        normalized_name,
        agents_root=agents_root,
        normalize_agent_name=normalize_agent_name,
    )

    target_paths: list[str] = []

    for action in actions:
        target_paths.extend(
            action_target_paths(
                action,
                dashboard_root=dashboard_root,
            )
        )

    target_paths = sorted(
        dict.fromkeys(target_paths)
    )

    blocked_rules = [
        rule
        for path in target_paths
        for rule in policy.get("blocked_paths", [])
        if path_matches_rule(path, str(rule))
    ]

    sandbox_paths = [
        path
        for path in target_paths
        if any(
            path_matches_rule(path, str(rule))
            for rule in policy.get(
                "sandbox_paths",
                [],
            )
        )
    ]

    core_paths = [
        path
        for path in target_paths
        if any(
            path_matches_rule(path, str(rule))
            for rule in policy.get(
                "core_paths",
                [],
            )
        )
    ]

    if blocked_rules:
        decision = "blocked"
        risk = "blocked"
        auto_apply_allowed = False
        review_required = False
        approval_required = False

    elif (
        target_paths
        and len(sandbox_paths) == len(target_paths)
    ):
        decision = "auto_apply_allowed"
        risk = "low"
        auto_apply_allowed = True
        review_required = False
        approval_required = False

    else:
        decision = "review_required"
        risk = "core" if core_paths else "workspace"
        auto_apply_allowed = False
        review_required = True
        approval_required = True

    path = policy_path(
        normalized_name,
        agents_root=agents_root,
        normalize_agent_name=normalize_agent_name,
    )

    return {
        "policy_file": stable_path(path),
        "decision": decision,
        "risk": risk,
        "target_paths": target_paths,
        "sandbox_paths": sandbox_paths,
        "core_paths": core_paths,
        "blocked_rules": sorted(
            set(str(rule) for rule in blocked_rules)
        ),
        "auto_apply_allowed": auto_apply_allowed,
        "review_required": review_required,
        "approval_required": approval_required,
    }
