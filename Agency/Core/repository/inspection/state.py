from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class InspectionStateDependencies:
    load_required_mission_json: Callable[[Path], dict[str, Any]]
    load_optional_mission_json: Callable[[Path], dict[str, Any]]
    mission_intent_path: Callable[[Path], Path]
    mission_state_path: Callable[[Path], Path]
    mission_plan_json_path: Callable[[Path], Path]
    mission_proposal_json_path: Callable[[Path], Path]
    mission_review_decision_json_path: Callable[[Path], Path]
    mission_implementation_manifest_path: Callable[[Path], Path]
    mission_verification_report_json_path: Callable[[Path], Path]
    mission_inspect_dir: Callable[[Path], Path]
    mission_unit_progress: Callable[[Path, dict[str, Any]], dict[str, Any]]
    mission_next_command_from_artifacts: Callable[..., dict[str, Any]]
    assess_plan_proposal_readiness: Callable[[dict[str, Any]], dict[str, Any]]
    mission_artifact_path_map: Callable[[Path], dict[str, Any]]
    mission_timestamps: Callable[[Path], dict[str, Any]]
    mission_event_files: Callable[[Path], list[Path]]
    stable_path: Callable[[Path], str]


def mission_status_payload(
    mission_dir: Path,
    *,
    dependencies: InspectionStateDependencies,
) -> dict[str, Any]:
    intent_data = dependencies.load_required_mission_json(
        dependencies.mission_intent_path(mission_dir)
    )
    state_data = dependencies.load_required_mission_json(
        dependencies.mission_state_path(mission_dir)
    )
    inspect_dir = mission_dir / "inspect"
    pass_files = sorted(inspect_dir.glob("pass_*.json"))

    return {
        "ok": True,
        "status": "mission_status",
        "mission_id": mission_dir.name,
        "mission_path": dependencies.stable_path(mission_dir),
        "intent": intent_data.get("intent"),
        "scopes": intent_data.get("scopes", []),
        "phase": state_data.get("phase"),
        "inspection_complete": bool(state_data.get("inspection_complete", False)),
        "inspection_passes": int(state_data.get("inspection_passes", len(pass_files))),
        "planning_complete": bool(state_data.get("planning_complete", False)),
        "proposals_complete": bool(state_data.get("proposals_complete", False)),
        "current_status": state_data.get("status"),
        "next_action": state_data.get("next_action"),
        "blocked_reason": state_data.get("blocked_reason"),
        "unresolved": state_data.get("unresolved", []),
        "budgets": state_data.get("budgets", {}),
        "artifacts": {
            "intent": dependencies.stable_path(dependencies.mission_intent_path(mission_dir)),
            "state": dependencies.stable_path(dependencies.mission_state_path(mission_dir)),
            "manifest": dependencies.stable_path(inspect_dir / "manifest.json"),
            "coverage": dependencies.stable_path(inspect_dir / "coverage.json"),
            "operator_notes": dependencies.stable_path(
                mission_dir / "review" / "operator_notes.md"
            ),
            "inspection_passes": [
                dependencies.stable_path(pass_path)
                for pass_path in pass_files
            ],
        },
        "authority": "read_only_mission_status",
    }


def mission_reconstruction(
    mission_dir: Path,
    *,
    dependencies: InspectionStateDependencies,
) -> dict[str, Any]:
    intent = dependencies.load_optional_mission_json(
        dependencies.mission_intent_path(mission_dir)
    )
    state = dependencies.load_optional_mission_json(
        dependencies.mission_state_path(mission_dir)
    )
    plan = dependencies.load_optional_mission_json(
        dependencies.mission_plan_json_path(mission_dir)
    )
    proposal = dependencies.load_optional_mission_json(
        dependencies.mission_proposal_json_path(mission_dir)
    )
    review = dependencies.load_optional_mission_json(
        dependencies.mission_review_decision_json_path(mission_dir)
    )
    dependencies.load_optional_mission_json(
        dependencies.mission_implementation_manifest_path(mission_dir)
    )
    verification = dependencies.load_optional_mission_json(
        dependencies.mission_verification_report_json_path(mission_dir)
    )
    inspect_dir = dependencies.mission_inspect_dir(mission_dir)
    inspection_passes = sorted(inspect_dir.glob("pass_*.json"))
    unit_progress = dependencies.mission_unit_progress(mission_dir, proposal)

    created = bool(intent and state)
    inspected = bool(inspection_passes)
    planned = bool(plan and plan.get("authority") == "planning_synthesis_only")
    proposed = bool(proposal and proposal.get("authority") == "implementation_proposal")
    approved = bool(
        review
        and review.get("decision") == "approved"
        and review.get("implementation_authorized") is True
    )
    review_decision = str(review.get("decision") or "")
    verified = bool(verification)

    next_action = dependencies.mission_next_command_from_artifacts(
        mission_dir,
        state=state,
        plan=plan,
        proposed=proposed,
        planned=planned,
        approved=approved,
        review_decision=review_decision,
        unit_progress=unit_progress,
        verification_report=verification,
        inspection_passes=inspection_passes,
    )

    if verified and verification.get("result") == "passed":
        phase = "complete"
        status = "verified"
    elif verified:
        result = verification.get("result", "unknown")
        phase = str(state.get("phase") or f"verification_{result}")
        status = str(state.get("status") or f"verification_{result}")
    elif unit_progress.get("implementation_complete"):
        phase = "implemented"
        status = "verification_pending"
    elif approved and unit_progress.get("total", 0) > 0:
        phase = "implementing" if unit_progress.get("complete", 0) else "approved"
        status = f"{unit_progress.get('complete', 0)}/{unit_progress.get('total', 0)} units"
    elif approved:
        phase = "approved"
        status = "awaiting_implementation"
    elif review_decision == "rejected":
        phase = "rejected"
        status = "proposal_rejected"
    elif review_decision == "changes_requested":
        phase = "review_changes_requested"
        status = "proposal_revision_requested"
    elif proposed:
        phase = "proposed"
        status = "waiting_review"
    elif planned:
        phase = "planned"
        readiness = dependencies.assess_plan_proposal_readiness(plan)
        status = "waiting_proposal" if readiness.get("ready") else "proposal_not_ready"
    elif inspected:
        phase = "inspection"
        status = "waiting_plan"
    else:
        phase = str(state.get("phase") or "created")
        status = str(state.get("status") or "ready_for_inspection")

    event_files = dependencies.mission_event_files(mission_dir)

    return {
        "mission_id": mission_dir.name,
        "mission_path": dependencies.stable_path(mission_dir),
        "intent": intent.get("intent"),
        "phase": phase,
        "status": status,
        "checkpoints": {
            "created": created,
            "inspected": inspected,
            "planned": planned,
            "proposed": proposed,
            "approved": approved,
            "implementing": approved and not unit_progress.get("implementation_complete"),
            "implemented": bool(unit_progress.get("implementation_complete")),
            "verified": verified,
            "complete": bool(
                verification and verification.get("mission_complete") is True
            ),
        },
        "inspection": {
            "passes": len(inspection_passes),
            "latest_pass": (
                dependencies.stable_path(inspection_passes[-1])
                if inspection_passes else None
            ),
        },
        "unit_progress": unit_progress,
        "verification": {
            "exists": verified,
            "result": verification.get("result"),
            "mission_complete": verification.get("mission_complete"),
            "report": dependencies.stable_path(
                dependencies.mission_verification_report_json_path(mission_dir)
            ),
        },
        "next_action": next_action,
        "artifacts": dependencies.mission_artifact_path_map(mission_dir),
        "timestamps": dependencies.mission_timestamps(mission_dir),
        "events": {
            "count": len(event_files),
            "latest": (
                dependencies.stable_path(event_files[-1])
                if event_files else None
            ),
        },
        "state_phase": state.get("phase"),
        "state_status": state.get("status"),
    }
