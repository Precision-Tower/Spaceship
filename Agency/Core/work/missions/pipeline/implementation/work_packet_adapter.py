from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from Agency.Core.work.tasks.editor.contracts import ACTIVE_EDITOR_NAME, PatchAuthorization, now_utc
from Agency.Core.work.work_packets.contracts import WorkPacket, WorkPacketStep
from Agency.Core.foundation.paths import stable_path


def _safe_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip())
    return text.strip(".-") or "packet"


def mission_unit_packet_id(mission_id: str, unit_id: str) -> str:
    raw = f"wp-{mission_id}-{unit_id}"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip(".-")
    return safe or "wp-unit"


def build_mission_unit_work_packet(
    *,
    mission_id: str,
    unit: dict[str, Any],
    proposal_path: Path,
    review_path: Path,
    patch_path: Path,
    baseline_hashes: dict[str, str],
    play_owner: str,
) -> WorkPacket:
    packet_id = mission_unit_packet_id(mission_id, str(unit.get("id") or "unit"))
    allowed_paths = list(dict.fromkeys(unit.get("allowed_paths") or []))
    apply_step_id = "apply-patch"
    verify_step_id = "verify"

    apply_step = WorkPacketStep(
        step_id=apply_step_id,
        sequence=1,
        title=f"Apply patch for unit {unit.get('id')}",
        objective=f"Apply implementation patch for unit {unit.get('id')}",
        operation="apply_patch",
        status="pending",
        depends_on=[],
        scope={"include": allowed_paths, "exclude": []},
        request={
            "patch_path": stable_path(patch_path),
            "proposal_path": stable_path(proposal_path),
            "review_path": stable_path(review_path),
            "unit_id": str(unit.get("id")),
            "mission_id": str(mission_id),
            "dependencies": unit.get("dependency_ids") or unit.get("dependencies") or [],
            "baseline_hashes": baseline_hashes,
        },
        constraints={"mutation_authorized": True, "read_only": False},
    )

    verify_step = WorkPacketStep(
        step_id=verify_step_id,
        sequence=2,
        title=f"Verify unit {unit.get('id')}",
        objective=f"Verify implementation patch application for unit {unit.get('id')}",
        operation="verify",
        status="pending",
        depends_on=[apply_step_id],
        scope={"include": allowed_paths, "exclude": []},
        request={
            "unit_id": str(unit.get("id")),
            "mission_id": str(mission_id),
            "verification_commands": unit.get("verification") or [],
            "verification": {"commands": ["git diff --check", "git status --short"]},
        },
        constraints={"mutation_authorized": False, "read_only": True},
    )

    now = now_utc()
    return WorkPacket(
        packet_id=packet_id,
        schema_version=1,
        title=f"Implement unit {unit.get('id')} for mission {mission_id}",
        objective=str(unit.get("objective") or f"Execute implementation for unit {unit.get('id')}"),
        created_by=play_owner,
        play_owner=play_owner,
        ball_holder=play_owner,
        next_decision_owner=play_owner,
        status="draft",
        scope={"include": allowed_paths, "exclude": []},
        constraints={"mutation_authorized": False, "read_only": False},
        acceptance_criteria=unit.get("verification") or ["Unit patch applied and verified."],
        steps=[apply_step, verify_step],
        unresolveds=[],
        contradictions=[],
        created_at=now,
        updated_at=now,
    )


def validate_review_authority(review: dict[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(review, dict):
        return False, "review_decision_absent_or_malformed"
    if review.get("authority") != "operator_review":
        return False, "review_authority_is_not_operator_review"
    if review.get("decision") != "approved":
        return False, "review_decision_is_not_approved"
    if review.get("implementation_authorized") is not True:
        return False, "review_implementation_not_authorized"
    return True, None


def build_patch_authorization_from_review(
    *,
    review: dict[str, Any],
    packet_id: str,
    apply_step_id: str,
    patch_path: Path,
    baseline_hashes: dict[str, str],
    allowed_paths: list[str],
    play_owner: str,
    expires_hours: int = 24,
) -> PatchAuthorization:
    valid, error_reason = validate_review_authority(review)
    if not valid:
        raise ValueError(f"cannot_build_patch_authorization:{error_reason}")

    if not patch_path.exists():
        raise ValueError("patch_path_missing")

    patch_bytes = patch_path.read_bytes()
    proposal_sha256 = hashlib.sha256(patch_bytes).hexdigest()
    editor_task_id = _safe_id(f"{packet_id}-{apply_step_id}")
    authorization_id = _safe_id(f"auth-{packet_id}-{apply_step_id}")

    authorized_by = str(review.get("reviewed_by") or play_owner).strip() or play_owner
    created_dt = datetime.now(timezone.utc)
    created_at = created_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    expires_at = (created_dt + timedelta(hours=expires_hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return PatchAuthorization(
        authorization_id=authorization_id,
        work_packet_id=packet_id,
        step_id=apply_step_id,
        editor_task_id=editor_task_id,
        proposal_sha256=proposal_sha256,
        baseline_hashes=baseline_hashes,
        authorized_by=authorized_by,
        play_owner=play_owner,
        authorized_editor=ACTIVE_EDITOR_NAME,
        allowed_paths=allowed_paths,
        allowed_operations=["apply_patch"],
        created_at=created_at,
        expires_at=expires_at,
        proposal_path=stable_path(patch_path),
    )