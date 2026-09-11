from __future__ import annotations

import hashlib
import json
from typing import Any

from Agency.GeminiGo.assignment import assignment_paths
from Agency.Core.work.work_packets.contracts import (
    WorkPacket,
    WorkPacketStep,
    now_utc,
)
from Agency.Core.work.work_packets.execution import (
    create_packet,
    dispatch_step,
    select_step,
)


PLAY_OWNER = "Gear"


def action_fingerprint(task: dict[str, Any]) -> str:
    material = {
        "identity": str(task.get("identity") or "").strip(),
        "state": str(task.get("state") or "").strip(),
        "summary": str(task.get("summary") or "").strip(),
        "next": str(task.get("next") or "").strip(),
        "operation": "inspect",
        "scope": assignment_paths(task),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def packet_id_for(task: dict[str, Any]) -> str:
    identity = str(task.get("identity") or "").strip()
    digest = action_fingerprint(task)[:12]
    token = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in identity)
    return f"geminigo-{token[:48]}-{digest}"


def build_inspection_packet(task: dict[str, Any]) -> WorkPacket:
    identity = str(task.get("identity") or "").strip()
    summary = str(task.get("summary") or identity).strip()
    next_action = str(task.get("next") or summary).strip()
    packet_id = packet_id_for(task)
    created = now_utc()
    paths = assignment_paths(task)
    lane = str(task.get("lane") or "agency")
    step = WorkPacketStep(
        step_id="inspect-authored-task",
        sequence=1,
        title=f"Inspect authored {lane} task",
        objective=(
            f"Collect bounded deterministic repository evidence for {identity}: "
            f"{next_action}"
        ),
        operation="inspect",
        status="pending",
        evidence_requirements=[
            "repository_relative_path",
            "bounded_repository_evidence",
            "no_repository_mutation",
        ],
        scope={"include": paths, "exclude": ["qps/cipher"] if lane == "kernel" else []},
        request={
            "repository_context": {
                "operations": ["text_search"],
                "text": identity,
                "paths": paths,
                "limits": {
                    "max_files": 4,
                    "max_matches": 12,
                    "max_evidence_items": 16,
                },
            }
        },
        constraints={
            "read_only": True,
            "mutation_authorized": False,
            "gemini_output_is_not_authority": True,
        },
    )
    return WorkPacket(
        packet_id=packet_id,
        schema_version=1,
        title=f"GeminiGo bounded evidence for {identity}",
        objective=summary,
        created_by="GeminiGo",
        play_owner=PLAY_OWNER,
        ball_holder=PLAY_OWNER,
        next_decision_owner=PLAY_OWNER,
        status="draft",
        scope={
            "include": ["qps/kernel", "qps/checklist.qps", "qps/_index.qps"]
            if lane == "kernel"
            else ["Agency"],
            "exclude": ["qps/cipher"]
            if lane == "kernel"
            else ["Agency/Archive"],
        },
        constraints={
            "mutation_authorized": False,
            "geminigo_dispatch": True,
            "provider_cannot_authorize_patch": True,
        },
        acceptance_criteria=[
            "Core Editor returns deterministic bounded evidence",
            "No repository mutation is performed",
            "Gemini output remains advisory evidence",
        ],
        steps=[step],
        unresolveds=[],
        contradictions=[],
        created_at=created,
        updated_at=created,
    )


def dispatch_read_only_assignment(task: dict[str, Any]) -> dict[str, Any]:
    packet = build_inspection_packet(task)
    created = create_packet(packet)
    if not created.get("ok"):
        errors = created.get("errors") or []
        if "duplicate_packet_id" not in errors:
            return {
                "ok": False,
                "stage": "create",
                "packet_id": packet.packet_id,
                "errors": errors,
            }
        return {
            "ok": False,
            "stage": "duplicate",
            "packet_id": packet.packet_id,
            "errors": errors,
        }

    selected = select_step(packet.packet_id, "inspect-authored-task", PLAY_OWNER)
    if not selected.get("ok"):
        return {
            "ok": False,
            "stage": "select",
            "packet_id": packet.packet_id,
            "errors": selected.get("errors") or [],
        }

    dispatched = dispatch_step(
        packet.packet_id,
        "inspect-authored-task",
        PLAY_OWNER,
    )
    return {
        "ok": bool(dispatched.get("ok")),
        "stage": "dispatch",
        "packet_id": packet.packet_id,
        "editor_task_id": dispatched.get("editor_task_id"),
        "editor_result_status": dispatched.get("editor_result_status"),
        "editor_result_path": dispatched.get("editor_result_path"),
        "repository_mutation_performed": bool(
            ((dispatched.get("result") or {}).get("steps") or [{}])[0]
            .get("result_summary", {})
            .get("repository_mutation_performed", False)
        ),
        "acceptance_established": False,
        "errors": dispatched.get("errors") or [],
    }
