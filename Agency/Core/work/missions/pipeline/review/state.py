from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ReviewStateDependencies:
    """Infrastructure required by the Mission Review state boundary."""

    load_required_mission_json: Callable[[Path], dict[str, Any]]
    mission_intent_path: Callable[[Path], Path]
    mission_state_path: Callable[[Path], Path]
    mission_proposal_json_path: Callable[[Path], Path]
    mission_review_dir: Callable[[Path], Path]
    load_plan: Callable[[Path], dict[str, Any]]
    now: Callable[[], str]
    stable: Callable[[Path], str]
    schema_version: Any
    emit_payload: Callable[[dict[str, Any]], None]


def _load_operator_notes(mission_dir: Path) -> str:
    path = mission_dir / "review" / "operator_notes.md"

    if not path.exists():
        return ""

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )[:2000]
    except Exception:
        return ""


def _mission_review_decision_md_path(
    mission_dir: Path,
    dependencies: ReviewStateDependencies,
) -> Path:
    return dependencies.mission_review_dir(mission_dir) / "decision.md"


def _load_proposal(
    mission_dir: Path,
    dependencies: ReviewStateDependencies,
) -> dict[str, Any]:
    proposal = dependencies.load_required_mission_json(
        dependencies.mission_proposal_json_path(mission_dir)
    )

    if proposal.get("authority") != "implementation_proposal":
        raise ValueError(
            "proposal authority is not implementation_proposal"
        )

    return proposal


def _load_review_inputs(
    mission_dir: Path,
    dependencies: ReviewStateDependencies,
) -> dict[str, Any]:
    return {
        "intent": dependencies.load_required_mission_json(
            dependencies.mission_intent_path(mission_dir)
        ),
        "state": dependencies.load_required_mission_json(
            dependencies.mission_state_path(mission_dir)
        ),
        "plan": dependencies.load_plan(mission_dir),
        "proposal": _load_proposal(mission_dir, dependencies),
        "operator_notes": _load_operator_notes(mission_dir),
    }


def _update_state_after_review(
    state_data: dict[str, Any],
    mission_id: str,
    decision_payload: dict[str, Any],
    decision_path: Path,
    dependencies: ReviewStateDependencies,
) -> dict[str, Any]:
    decision = str(decision_payload.get("decision") or "")
    approved = decision == "approved"

    if decision == "approved":
        phase = "approved"
        status = "awaiting_implementation"
        unresolved_note = "Implementation has not started."
    elif decision == "rejected":
        phase = "rejected"
        status = "proposal_rejected"
        unresolved_note = "Proposal rejected by operator."
    else:
        phase = "review_changes_requested"
        status = "proposal_revision_requested"
        unresolved_note = "Operator requested proposal revision."

    unresolved: list[str] = []

    for item in state_data.get("unresolved", []):
        text = str(item)

        if text == "No implementation proposal exists.":
            continue

        if text not in unresolved:
            unresolved.append(text)

    if unresolved_note not in unresolved:
        unresolved.append(unresolved_note)

    return {
        **state_data,
        "schema_version": state_data.get(
            "schema_version",
            dependencies.schema_version,
        ),
        "mission_id": mission_id,
        "updated_at": str(
            decision_payload.get("reviewed_at")
            or dependencies.now()
        ),
        "phase": phase,
        "status": status,
        "implementation_authorized": approved,
        "implementation_enabled": approved,
        "unresolved": unresolved,
        "next_action": decision_payload["next_action"],
        "review": {
            "path": dependencies.stable(decision_path),
            "created_at": decision_payload.get("reviewed_at"),
            "schema_version": dependencies.schema_version,
            "decision": decision,
            "implementation_authorized": approved,
        },
    }


def _review_failure(
    status: str,
    mission_id: str | None,
    reason: str,
    *,
    next_action: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    exit_code: int = 1,
    dependencies: ReviewStateDependencies,
) -> int:
    payload: dict[str, Any] = {
        "ok": False,
        "status": status,
        "error": status,
        "mission_id": mission_id,
        "reason": reason,
        "authority": "operator_review",
        "source_files_modified": False,
    }

    if next_action:
        payload["next_action"] = next_action

    if extra:
        payload.update(extra)

    dependencies.emit_payload(payload)
    return exit_code
