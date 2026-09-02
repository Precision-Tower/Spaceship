from __future__ import annotations

from Agency.Core.runtime.commands import mission_command
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ReviewExecutionDependencies:
    """Infrastructure required by Mission Review execution."""

    schema_version: Any
    resolve_mission_dir: Callable[[str], Path]
    validate_review_request: Callable[..., tuple[Any, Any, Any]]
    review_failure: Callable[..., int]
    mission_review_decision_json_path: Callable[[Path], Path]
    mission_review_decision_md_path: Callable[[Path], Path]
    mission_proposal_json_path: Callable[[Path], Path]
    load_review_inputs: Callable[[Path], dict[str, Any]]
    now: Callable[[], str]
    review_next_action: Callable[[str, str], dict[str, Any]]
    stable: Callable[[Path], str]
    mission_review_dir: Callable[[Path], Path]
    atomic_json: Callable[[Path, dict[str, Any]], Any]
    atomic_text: Callable[[Path, str], Any]
    render_review_markdown: Callable[[dict[str, Any]], str]
    update_state_after_review: Callable[
        [dict[str, Any], str, dict[str, Any], Path],
        dict[str, Any],
    ]
    mission_state_path: Callable[[Path], Path]
    append_mission_event: Callable[..., Any]
    refresh_pinboard: Callable[..., Any]
    emit_payload: Callable[[dict[str, Any]], Any]


def run_mission_review(
    dependencies: ReviewExecutionDependencies,
    args: argparse.Namespace,
) -> int:
    """Execute one operator-controlled Mission Review decision."""

    try:
        mission_dir = dependencies.resolve_mission_dir(args.mission)
    except ValueError as exc:
        return dependencies.review_failure(
            "mission_not_found",
            str(args.mission),
            str(exc),
            exit_code=2,
        )

    mission_id = mission_dir.name

    decision, _request_note, request_error = (
        dependencies.validate_review_request(args)
    )

    if request_error:
        return dependencies.review_failure(
            "invalid_review_request",
            mission_id,
            request_error,
            exit_code=2,
        )

    decision_json_path = (
        dependencies.mission_review_decision_json_path(mission_dir)
    )
    decision_md_path = (
        dependencies.mission_review_decision_md_path(mission_dir)
    )

    if decision_json_path.exists() or decision_md_path.exists():
        payload = {
            "ok": False,
            "status": "review_already_completed",
            "mission_id": mission_id,
            "decision_path": dependencies.stable(decision_json_path),
            "markdown_path": dependencies.stable(decision_md_path),
            "authority": "operator_review",
            "source_files_modified": False,
        }
        dependencies.emit_payload(payload)
        return 0

    proposal_path = dependencies.mission_proposal_json_path(
        mission_dir
    )

    if not proposal_path.exists():
        next_action = {
            "command": mission_command("propose", mission_id),
            "authority": "implementation_proposal",
        }
        return dependencies.review_failure(
            "proposal_required",
            mission_id,
            "proposal/proposal.json is required before operator review.",
            next_action=next_action,
            exit_code=1,
        )

    try:
        inputs = dependencies.load_review_inputs(mission_dir)
    except ValueError as exc:
        return dependencies.review_failure(
            "invalid_review_request",
            mission_id,
            str(exc),
            exit_code=2,
        )

    decision, notes, request_error = (
        dependencies.validate_review_request(
            args,
            str(inputs.get("operator_notes") or ""),
        )
    )

    if request_error or decision is None:
        return dependencies.review_failure(
            "invalid_review_request",
            mission_id,
            request_error or "Review decision is required.",
            exit_code=2,
        )

    reviewed_at = dependencies.now()
    next_action = dependencies.review_next_action(
        mission_id,
        decision,
    )

    decision_payload = {
        "schema_version": dependencies.schema_version,
        "mission_id": mission_id,
        "decision": decision,
        "reviewed_at": reviewed_at,
        "reviewed_by": "operator",
        "notes": notes,
        "authority": "operator_review",
        "implementation_authorized": decision == "approved",
        "next_action": next_action,
        "proposal_reference": {
            "path": dependencies.stable(proposal_path),
            "created_at": inputs["proposal"].get("created_at"),
            "schema_version": inputs["proposal"].get(
                "schema_version"
            ),
            "authority": inputs["proposal"].get("authority"),
        },
        "plan_reference": {
            "path": "plan/plan.json",
            "created_at": inputs["plan"].get("created_at"),
            "schema_version": inputs["plan"].get(
                "schema_version"
            ),
        },
    }

    try:
        dependencies.mission_review_dir(mission_dir).mkdir(
            parents=True,
            exist_ok=True,
        )
        dependencies.atomic_json(
            decision_json_path,
            decision_payload,
        )
        dependencies.atomic_text(
            decision_md_path,
            dependencies.render_review_markdown(
                decision_payload
            ),
        )

        state_payload = dependencies.update_state_after_review(
            inputs["state"],
            mission_id,
            decision_payload,
            decision_json_path,
        )

        dependencies.atomic_json(
            dependencies.mission_state_path(mission_dir),
            state_payload,
        )
    except Exception as exc:
        return dependencies.review_failure(
            "review_write_failed",
            mission_id,
            f"{type(exc).__name__}: {exc}",
            exit_code=1,
        )

    review_status = str(
        state_payload.get("status") or "review_recorded"
    )

    observation = {
        "command": "mission review",
        "status": review_status,
        "mission_id": mission_id,
        "decision": decision,
        "decision_path": dependencies.stable(
            decision_json_path
        ),
        "markdown_path": dependencies.stable(
            decision_md_path
        ),
        "implementation_authorized": decision_payload[
            "implementation_authorized"
        ],
        "source_files_modified": False,
        "authority": "operator_review",
    }

    dependencies.append_mission_event(
        mission_dir,
        decision,
        observation,
    )

    dependencies.refresh_pinboard(
        mission=str(
            inputs["intent"].get("intent") or mission_id
        ),
        last_observation=observation,
        next_action=state_payload["next_action"],
    )

    payload = {
        "ok": True,
        "status": review_status,
        "mission_id": mission_id,
        "decision": decision,
        "decision_path": dependencies.stable(
            decision_json_path
        ),
        "markdown_path": dependencies.stable(
            decision_md_path
        ),
        "implementation_authorized": decision_payload[
            "implementation_authorized"
        ],
        "next_action": state_payload["next_action"],
        "source_files_modified": False,
        "authority": "operator_review",
    }

    dependencies.emit_payload(payload)
    return 0