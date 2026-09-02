from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.work.tasks.editor.contracts import ACTIVE_EDITOR_NAME, EditorTask, PatchAuthorization
from Agency.Core.work.tasks.editor.execution import execute_editor_task
from Agency.Core.work.tasks.editor import persistence as editor_persistence
from Agency.Core.foundation.paths import DASHBOARD_ROOT, stable_path
from Agency.Core.work.work_packets.contracts import (
    STEP_TERMINAL_STATUSES,
    WorkPacket,
    WorkPacketStep,
    dependency_status,
    effective_step_scope,
    now_utc,
    packet_from_mapping,
    replace_packet_status,
    replace_step,
    validate_work_packet,
)
from Agency.Core.work.work_packets import persistence


def _safe_id(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip())
    return text.strip(".-") or "work-packet"


def _packet_payload(packet: WorkPacket, *, ok: bool = True, errors: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": ok,
        "packet_id": packet.packet_id,
        "status": packet.status,
        "play_owner": packet.play_owner,
        "ball_holder": packet.ball_holder,
        "ball_owner": packet.play_owner,
        "next_decision_owner": packet.next_decision_owner,
        "persistence_path": persistence.stable_packet_path(packet.packet_id),
        "repository_mutation_performed": False,
        "acceptance_established": False,
        "errors": errors or [],
        "packet": packet.to_dict(),
    }


def _error_payload(packet_id: str, errors: list[str], *, status: str = "rejected") -> dict[str, Any]:
    return {
        "ok": False,
        "packet_id": packet_id,
        "status": status,
        "repository_mutation_performed": False,
        "acceptance_established": False,
        "errors": errors,
    }


def _load_packet_file(path: str | Path) -> WorkPacket:
    packet_path = Path(path)
    text = packet_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if packet_path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    return packet_from_mapping(data)


def create_packet(packet: WorkPacket) -> dict[str, Any]:
    directory = persistence.packet_dir(packet.packet_id)
    if (directory / "packet.json").exists():
        return _error_payload(packet.packet_id, ["duplicate_packet_id"])

    errors = validate_work_packet(packet, root=DASHBOARD_ROOT)
    if errors:
        return _error_payload(packet.packet_id, errors)

    persistence.save_packet(packet)
    persistence.append_event(
        directory,
        "packet_created",
        created_by=packet.created_by,
        play_owner=packet.play_owner,
        ball_holder=packet.ball_holder,
    )
    return _packet_payload(packet)


def create_packet_from_file(path: str | Path) -> dict[str, Any]:
    try:
        packet = _load_packet_file(path)
    except Exception as exc:
        digest = hashlib.sha256(
            str(path).encode("utf-8", errors="replace")
        ).hexdigest()[:12]
        return _error_payload(
            f"rejected-intake-{digest}",
            [f"malformed_work_packet:{type(exc).__name__}: {exc}"],
        )

    return create_packet(packet)


def _find_step(packet: WorkPacket, step_id: str) -> WorkPacketStep:
    for step in packet.steps:
        if step.step_id == step_id:
            return step
    raise ValueError(f"step_not_found:{step_id}")


def _active_or_activate(packet: WorkPacket, directory: Path) -> WorkPacket:
    if packet.status == "draft":
        packet = replace_packet_status(packet, "active", ball_holder=packet.play_owner)
        persistence.save_packet(packet)
        persistence.append_event(directory, "packet_activated", play_owner=packet.play_owner, ball_holder=packet.ball_holder)
    return packet


def _selected_or_dispatched_step(packet: WorkPacket) -> WorkPacketStep | None:
    for step in packet.steps:
        if step.status in {"selected", "dispatched"}:
            return step
    return None


def select_step(packet_id: str, step_id: str, owner: str) -> dict[str, Any]:
    packet = persistence.load_packet(packet_id)
    directory = persistence.packet_dir(packet_id)
    errors = validate_work_packet(packet, root=DASHBOARD_ROOT)
    if errors:
        return _error_payload(packet_id, errors)
    if owner != packet.play_owner or owner != packet.next_decision_owner:
        return _error_payload(packet_id, ["selection_owner_must_equal_play_owner"])
    if packet.ball_holder != packet.play_owner:
        return _error_payload(packet_id, ["cannot_select_while_ball_is_not_with_play_owner"])
    packet = _active_or_activate(packet, directory)
    if packet.status != "active":
        return _error_payload(packet_id, [f"packet_not_selectable:{packet.status}"])
    active_step = _selected_or_dispatched_step(packet)
    if active_step is not None:
        return _error_payload(packet_id, [f"step_already_selected_or_dispatched:{active_step.step_id}"])
    step = _find_step(packet, step_id)
    if step.status != "pending":
        return _error_payload(packet_id, [f"step_not_pending:{step.step_id}:{step.status}"])
    unmet = dependency_status(packet, step)
    if unmet:
        return _error_payload(packet_id, [f"unmet_dependencies:{step.step_id}:{','.join(unmet)}"])
    selected = WorkPacketStep(**{**step.to_dict(), "status": "selected"})
    packet = replace_step(packet, selected, status="active", ball_holder=packet.play_owner)
    persistence.save_packet(packet)
    persistence.append_event(directory, "step_selected", step_id=step_id, owner=owner, decision_owner=owner)
    return _packet_payload(packet)


def _derive_symbol_request(objective: str) -> dict[str, Any]:
    match = re.search(r"\bdefinition\s+of\s+([A-Za-z_][A-Za-z0-9_]*)\b", objective, re.IGNORECASE)
    if match:
        return {"operations": ["symbol_definition", "references"], "symbol": match.group(1)}
    return {"operations": ["path_discovery"]}


def _authorization_path(packet_id: str, authorization_id: str) -> str:
    return stable_path(
        persistence.packet_dir(packet_id) / "authorizations" / f"{authorization_id}.json"
    )


def _latest_authorization_for_step(packet_id: str, step: WorkPacketStep) -> dict[str, Any] | None:
    auth_dir = persistence.packet_dir(packet_id) / "authorizations"
    if not auth_dir.exists():
        return None
    for path in sorted(auth_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("step_id") in step.depends_on or data.get("step_id") == step.step_id:
            return data
    return None


def _editor_task_for_step(packet: WorkPacket, step: WorkPacketStep) -> EditorTask:
    scope = effective_step_scope(packet, step, root=DASHBOARD_ROOT)
    request = dict(step.request)
    if "repository_context" not in request and step.operation == "inspect":
        request["repository_context"] = _derive_symbol_request(step.objective)
    if "repository_context" not in request and step.operation == "propose_patch":
        request["repository_context"] = {"operations": ["text_search"], "text": str(request.get("change_intent") or step.objective)[:120]}
    if step.operation == "apply_patch":
        authorization = request.get("authorization")
        if not authorization:
            authorization = _latest_authorization_for_step(packet.packet_id, step)
        if authorization:
            request["authorization"] = authorization
            request["authorization_path"] = _authorization_path(packet.packet_id, authorization["authorization_id"])
            request["proposal_patch_path"] = authorization.get("proposal_path")
    if step.operation == "verify" and "verification" not in request:
        request["verification"] = {"commands": ["git diff --check", "git status --short"]}
    constraints = {**packet.constraints, **step.constraints}
    constraints["read_only"] = step.operation != "apply_patch"
    constraints["mutation_authorized"] = step.operation == "apply_patch"
    return EditorTask(
        task_id=_safe_id(f"{packet.packet_id}-{step.step_id}"),
        schema_version=1,
        issued_by=packet.play_owner,
        editor=ACTIVE_EDITOR_NAME,
        play_owner=packet.play_owner,
        ball_holder=ACTIVE_EDITOR_NAME,
        next_decision_owner=packet.play_owner,
        objective=step.objective,
        operation=step.operation,
        scope=scope,
        request=request,
        constraints=constraints,
        evidence_requirements=step.evidence_requirements,
        created_at=now_utc(),
        work_packet_id=packet.packet_id,
        parent_step_id=step.step_id,
    )


def _map_result_status(status: str) -> str:
    return {"completed": "completed", "partial": "partial", "blocked": "blocked", "rejected": "rejected", "failed": "failed"}.get(status, "failed")


def _packet_status_after_step(packet: WorkPacket, step_status: str) -> tuple[str, str | None]:
    if step_status in {"blocked", "rejected", "failed"}:
        return "blocked", "packet_blocked"
    if step_status == "partial":
        return "awaiting_direction", "packet_awaiting_direction"
    if all(step.status in STEP_TERMINAL_STATUSES for step in packet.steps):
        return "completed", "packet_completed"
    return "active", "packet_state_updated"


def dispatch_step(packet_id: str, step_id: str, owner: str) -> dict[str, Any]:
    packet = persistence.load_packet(packet_id)
    directory = persistence.packet_dir(packet_id)
    errors = validate_work_packet(packet, root=DASHBOARD_ROOT)
    if errors:
        return _error_payload(packet_id, errors)
    if owner != packet.play_owner or owner != packet.next_decision_owner:
        return _error_payload(packet_id, ["dispatch_owner_must_equal_play_owner"])
    if packet.ball_holder != packet.play_owner:
        return _error_payload(packet_id, ["cannot_dispatch_while_ball_is_not_with_play_owner"])
    step = _find_step(packet, step_id)
    if step.status != "selected":
        return _error_payload(packet_id, [f"step_must_be_selected_before_dispatch:{step_id}:{step.status}"])
    throw_id = _safe_id(f"throw-{packet_id}-{step_id}-{hashlib.sha256(now_utc().encode()).hexdigest()[:8]}")
    persistence.append_event(directory, "step_dispatch_started", step_id=step_id, owner=owner)
    persistence.append_event(directory, "ball_thrown", throw_id=throw_id, packet=packet_id, step=step_id, from_holder=packet.play_owner, to_holder=ACTIVE_EDITOR_NAME, route=step.operation)
    dispatched = WorkPacketStep(**{**step.to_dict(), "status": "dispatched"})
    packet = replace_step(packet, dispatched, status="active", ball_holder=ACTIVE_EDITOR_NAME)
    persistence.save_packet(packet)
    persistence.append_event(directory, "ball_received", throw_id=throw_id, by=ACTIVE_EDITOR_NAME)

    editor_task = _editor_task_for_step(packet, dispatched)
    persistence.append_event(directory, "editor_task_created", step_id=step_id, editor_task_id=editor_task.task_id)
    task_ref = persistence.save_task_reference(packet_id, editor_task.task_id, {
        "editor_task_id": editor_task.task_id,
        "editor_task_path": stable_path(editor_persistence.task_dir(editor_task.task_id) / "task.json"),
        "task": editor_task.to_dict(),
    })
    editor_result = execute_editor_task(editor_task)
    result_ref = persistence.save_result_reference(packet_id, editor_task.task_id, {
        "editor_task_id": editor_task.task_id,
        "editor_result_path": stable_path(editor_persistence.task_dir(editor_task.task_id) / "result.json"),
        "result": editor_result.to_dict(),
    })
    throw_record = {
        "throw_id": throw_id,
        "packet": packet_id,
        "step": step_id,
        "from": packet.play_owner,
        "to": ACTIVE_EDITOR_NAME,
        "route": step.operation,
        "dispatched_at": now_utc(),
        "received_at": now_utc(),
        "returned_at": editor_result.completed_at,
        "result": stable_path(result_ref),
    }
    persistence.save_throw(packet_id, throw_id, throw_record)
    persistence.append_event(directory, "editor_result_received", step_id=step_id, editor_task_id=editor_task.task_id, status=editor_result.status)
    persistence.append_event(directory, "ball_returned", throw_id=throw_id, from_holder=ACTIVE_EDITOR_NAME, to_holder=packet.play_owner)

    mapped = _map_result_status(editor_result.status)
    completed_step = WorkPacketStep(**{
        **dispatched.to_dict(),
        "status": mapped,
        "editor_task_id": editor_task.task_id,
        "editor_result_path": stable_path(result_ref),
        "result_summary": {
            "status": editor_result.status,
            "play_outcome": editor_result.play_outcome,
            "evidence_loaded": editor_result.evidence_bundle is not None,
            "proposal_created": bool(editor_result.patch_artifacts),
            "repository_mutation_performed": bool(editor_result.repository_mutations),
            "authorization_id": editor_result.authorization_id,
            "commit_performed": editor_result.commit_performed,
            "acceptance_claimed": editor_result.acceptance_claimed,
        },
        "unresolveds": editor_result.unresolveds,
    })
    packet = replace_step(packet, completed_step, ball_holder=packet.play_owner)
    packet_status, packet_event = _packet_status_after_step(packet, mapped)
    packet = replace_packet_status(packet, packet_status, ball_holder=packet.play_owner)
    persistence.save_packet(packet)
    persistence.append_event(directory, "ball_received_back", throw_id=throw_id, by=packet.play_owner)
    persistence.append_event(directory, "step_state_updated", step_id=step_id, status=mapped)
    if packet_event:
        persistence.append_event(directory, packet_event, status=packet_status, acceptance_established=False)
    return {
        **_packet_payload(packet),
        "step_id": step_id,
        "throw_id": throw_id,
        "editor_task_id": editor_task.task_id,
        "editor_result_status": editor_result.status,
        "editor_result_path": stable_path(result_ref),
        "task_reference_path": stable_path(task_ref),
        "result_reference_path": stable_path(result_ref),
        "no_next_step_selected": _selected_or_dispatched_step(packet) is None,
        "result": packet.to_dict(),
    }


def _resolve_stable(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return DASHBOARD_ROOT / path


def _parse_patch_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            rel = line[6:].strip()
            if rel != "/dev/null" and rel not in paths:
                paths.append(rel)
    return paths


def authorize_patch(packet_id: str, step_id: str, owner: str, *, expires_hours: int = 24) -> dict[str, Any]:
    packet = persistence.load_packet(packet_id)
    directory = persistence.packet_dir(packet_id)
    if owner != packet.play_owner or owner != packet.next_decision_owner:
        return _error_payload(packet_id, ["authorization_owner_must_equal_play_owner"])
    step = _find_step(packet, step_id)
    if step.operation != "propose_patch" or step.status != "completed" or not step.editor_task_id:
        return _error_payload(packet_id, [f"step_not_authorizable:{step_id}:{step.status}:{step.operation}"])
    result_ref = persistence.packet_dir(packet_id) / "results" / f"{step.editor_task_id}.json"
    result_data = json.loads(result_ref.read_text(encoding="utf-8"))["result"]
    patch_artifacts = result_data.get("patch_artifacts") or []
    if not patch_artifacts:
        return _error_payload(packet_id, ["proposal_patch_artifact_missing"])
    patch_path = _resolve_stable(patch_artifacts[0]["path"])
    patch_text = patch_path.read_text(encoding="utf-8")
    allowed_paths = _parse_patch_paths(patch_text)
    baseline_hashes = {
        rel: hashlib.sha256((DASHBOARD_ROOT / rel).read_bytes()).hexdigest()
        for rel in allowed_paths
    }
    authorization_id = _safe_id(f"auth-{packet_id}-{step_id}")
    created = datetime.now(timezone.utc)
    auth = PatchAuthorization(
        authorization_id=authorization_id,
        work_packet_id=packet_id,
        step_id=step_id,
        editor_task_id=step.editor_task_id,
        proposal_sha256=hashlib.sha256(patch_path.read_bytes()).hexdigest(),
        baseline_hashes=baseline_hashes,
        authorized_by=owner,
        play_owner=packet.play_owner,
        authorized_editor=ACTIVE_EDITOR_NAME,
        allowed_paths=allowed_paths,
        allowed_operations=["apply_patch"],
        created_at=created.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        expires_at=(created + timedelta(hours=expires_hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        proposal_path=stable_path(patch_path),
    )
    auth_path = persistence.save_authorization(packet_id, authorization_id, auth.to_dict())
    persistence.append_event(directory, "patch_authorized", authorization_id=authorization_id, step_id=step_id, authorized_by=owner)
    return {
        "ok": True,
        "packet_id": packet_id,
        "authorization_id": authorization_id,
        "authorization_path": stable_path(auth_path),
        "proposal_sha256": auth.proposal_sha256,
        "allowed_paths": allowed_paths,
        "ball_holder": packet.ball_holder,
        "play_owner": packet.play_owner,
        "next_decision_owner": packet.next_decision_owner,
        "authorization": auth.to_dict(),
    }


def packet_result(packet_id: str) -> dict[str, Any]:
    packet = persistence.load_packet(packet_id)
    return {
        **_packet_payload(packet),
        "operational_completion_is_not_acceptance": packet.status == "completed",
        "accepted": False,
        "validated": False,
        "committed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python run.py work-packet", description="Create, inspect, select, dispatch, authorize, and record WorkPackets.")
    sub = parser.add_subparsers(dest="command")
    create = sub.add_parser("create", help="Create a WorkPacket from a YAML file.")
    create.add_argument("--file", required=True, help="Path to the WorkPacket YAML file.")
    show = sub.add_parser("show", help="Show a WorkPacket by ID.")
    show.add_argument("packet_id", help="WorkPacket identifier.")
    select = sub.add_parser("select", help="Select a WorkPacket step for an owner.")
    select.add_argument("--packet", required=True, help="WorkPacket identifier.")
    select.add_argument("--step", required=True, help="WorkPacket step identifier.")
    select.add_argument("--owner", required=True, help="Owner receiving the step.")
    dispatch = sub.add_parser("dispatch", help="Dispatch a WorkPacket step to an owner.")
    dispatch.add_argument("--packet", required=True, help="WorkPacket identifier.")
    dispatch.add_argument("--step", required=True, help="WorkPacket step identifier.")
    dispatch.add_argument("--owner", required=True, help="Owner receiving the step.")
    authorize = sub.add_parser("authorize", help="Authorize a WorkPacket step.")
    authorize.add_argument("--packet", required=True, help="WorkPacket identifier.")
    authorize.add_argument("--step", required=True, help="WorkPacket step identifier.")
    authorize.add_argument("--owner", required=True, help="Owner receiving the authorization.")
    authorize.add_argument("--expires-hours", type=int, default=24, help="Authorization lifetime in hours (default: 24).")
    result = sub.add_parser("result", help="Show the result for a WorkPacket.")
    result.add_argument("packet_id", help="WorkPacket identifier.")
    args = parser.parse_args(argv or [])

    if args.command == "create":
        payload = create_packet_from_file(args.file)
    elif args.command == "show":
        payload = _packet_payload(persistence.load_packet(args.packet_id))
    elif args.command == "select":
        payload = select_step(args.packet, args.step, args.owner)
    elif args.command == "dispatch":
        payload = dispatch_step(args.packet, args.step, args.owner)
    elif args.command == "authorize":
        payload = authorize_patch(args.packet, args.step, args.owner, expires_hours=args.expires_hours)
    elif args.command == "result":
        payload = packet_result(args.packet_id)
    else:
        parser.print_help()
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1
