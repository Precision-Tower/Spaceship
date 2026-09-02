from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable


ResolvePacketArg = Callable[
    [str, str | None, bool],
    Path,
]

LoadDocument = Callable[
    [Path],
    dict[str, Any],
]

ActionPacket = Callable[
    [dict[str, Any]],
    dict[str, Any],
]

ValidatePacketAgent = Callable[
    [dict[str, Any], str],
    str,
]

EvaluateActionPolicy = Callable[
    [str, list[dict[str, Any]]],
    dict[str, Any],
]

ApplyAction = Callable[
    [dict[str, Any]],
    dict[str, Any],
]

WriteDocument = Callable[
    [Path, dict[str, Any]],
    None,
]

ResultPath = Callable[
    [str, str],
    Path,
]

StablePath = Callable[
    [Path],
    str,
]


def apply_action_packet(
    agent_name: str,
    packet_arg: str | None = None,
    *,
    latest: bool = False,
    approved: bool = False,
    resolve_packet_arg: ResolvePacketArg,
    load_document: LoadDocument,
    action_packet: ActionPacket,
    validate_packet_agent: ValidatePacketAgent,
    evaluate_action_policy: EvaluateActionPolicy,
    apply_action: ApplyAction,
    write_document: WriteDocument,
    result_path: ResultPath,
    stable_path: StablePath,
) -> int:
    try:
        packet_path = resolve_packet_arg(
            agent_name,
            packet_arg,
            latest,
        )

        data = load_document(packet_path)
        packet = action_packet(data)

        agent_name = validate_packet_agent(
            packet,
            agent_name,
        )

        actions = packet.get("actions") or []

        if not isinstance(actions, list) or not actions:
            raise ValueError(
                "packet_has_no_actions"
            )

        policy = evaluate_action_policy(
            agent_name,
            actions,
        )

        packet["policy"] = policy

        if policy["decision"] == "blocked":
            print("ACTION_APPLY_BLOCKED")
            print(
                "reason: dangerous_path_blocked: "
                + ", ".join(
                    policy["blocked_rules"]
                )
            )
            return 2

        review = packet.get("review", {})

        if (
            policy["review_required"]
            and review.get("status") != "reviewed"
        ):
            print("ACTION_APPLY_BLOCKED")
            print("reason: review_required")
            print(
                "next: python run.py agent action review "
                f"{agent_name} --latest"
            )
            return 2

        if (
            policy["approval_required"]
            and not approved
        ):
            print("ACTION_APPLY_BLOCKED")
            print("reason: --approved required")
            return 2

        results = [
            apply_action(action)
            for action in actions
        ]

        action_id = str(
            packet.get(
                "id",
                packet_path.stem,
            )
        )

        auto_applied = bool(
            policy["auto_apply_allowed"]
            and not approved
        )

        packet["status"] = "applied"
        packet["approved"] = bool(approved)
        packet["auto_applied"] = auto_applied
        packet["applied_at"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        write_document(
            packet_path,
            {
                "ActionPacket": packet,
            },
        )

        write_document(
            result_path(
                agent_name,
                action_id,
            ),
            {
                "ActionResult": {
                    "id": action_id,
                    "agent": agent_name,
                    "status": "applied",
                    "packet": stable_path(
                        packet_path
                    ),
                    "writes_approved": bool(
                        approved
                    ),
                    "auto_applied": auto_applied,
                    "policy": policy,
                    "results": results,
                }
            },
        )

    except Exception as exc:
        print("ACTION_APPLY_FAILED")
        print(f"reason: {exc}")
        return 1

    print("ACTION_APPLIED")
    print(f"agent: {agent_name}")
    print(
        f"packet: {stable_path(packet_path)}"
    )
    print(
        f"policy: {policy['decision']}"
    )
    print(
        "approval_used: "
        f"{str(bool(approved)).lower()}"
    )
    print(
        "auto_applied: "
        f"{str(auto_applied).lower()}"
    )

    for result in results:
        if "path" in result:
            print(
                f"wrote: {result['path']}"
            )

    return 0
