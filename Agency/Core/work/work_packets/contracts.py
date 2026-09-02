from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from Agency.Core.work.tasks.editor.contracts import ACTIVE_EDITOR_NAME, coerce_string_list, now_utc, resolve_repo_path


PACKET_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
PACKET_STATUSES = {"draft", "active", "blocked", "awaiting_direction", "completed", "cancelled"}
STEP_OPERATIONS = {"inspect", "propose_patch", "apply_patch", "verify"}
STEP_STATUSES = {"pending", "selected", "dispatched", "completed", "partial", "blocked", "rejected", "failed", "skipped"}
STEP_TERMINAL_STATUSES = {"completed", "partial", "blocked", "rejected", "failed", "skipped"}
DEPENDENCY_SATISFIED_STATUSES = {"completed", "skipped"}


@dataclass(frozen=True)
class WorkPacketStep:
    step_id: str
    sequence: int
    title: str
    objective: str
    operation: str
    status: str
    depends_on: list[str] = field(default_factory=list)
    editor_task_id: str | None = None
    editor_result_path: str | None = None
    result_summary: dict[str, Any] | None = None
    evidence_requirements: list[str] = field(default_factory=list)
    unresolveds: list[dict[str, Any]] = field(default_factory=list)
    scope: dict[str, list[str]] = field(default_factory=dict)
    request: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkPacket:
    packet_id: str
    schema_version: int
    title: str
    objective: str
    created_by: str
    play_owner: str
    ball_holder: str
    next_decision_owner: str
    status: str
    scope: dict[str, list[str]]
    constraints: dict[str, Any]
    acceptance_criteria: list[str]
    steps: list[WorkPacketStep]
    unresolveds: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    created_at: str
    updated_at: str

    @property
    def ball_owner(self) -> str:
        return self.play_owner

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        data["ball_owner"] = self.play_owner
        return data


def _coerce_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _coerce_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def step_from_mapping(data: dict[str, Any]) -> WorkPacketStep:
    scope = _coerce_dict(data.get("scope"))
    return WorkPacketStep(
        step_id=str(data.get("step_id") or "").strip(),
        sequence=int(data.get("sequence") or 0),
        title=str(data.get("title") or "").strip(),
        objective=str(data.get("objective") or "").strip(),
        operation=str(data.get("operation") or "").strip(),
        status=str(data.get("status") or "pending").strip(),
        depends_on=coerce_string_list(data.get("depends_on")),
        editor_task_id=str(data.get("editor_task_id") or "").strip() or None,
        editor_result_path=str(data.get("editor_result_path") or "").strip() or None,
        result_summary=_coerce_dict(data.get("result_summary")) or None,
        evidence_requirements=coerce_string_list(data.get("evidence_requirements")),
        unresolveds=_coerce_records(data.get("unresolveds")),
        scope={"include": coerce_string_list(scope.get("include")), "exclude": coerce_string_list(scope.get("exclude"))},
        request=_coerce_dict(data.get("request")),
        constraints=_coerce_dict(data.get("constraints")),
    )


def packet_from_mapping(data: dict[str, Any]) -> WorkPacket:
    if not isinstance(data, dict):
        raise ValueError("work_packet_must_be_object")
    root = data.get("WorkPacket", data)
    if not isinstance(root, dict):
        raise ValueError("work_packet_must_be_object")
    scope = _coerce_dict(root.get("scope"))
    now = now_utc()
    play_owner = str(root.get("play_owner") or root.get("ball_owner") or "").strip()
    return WorkPacket(
        packet_id=str(root.get("packet_id") or "").strip(),
        schema_version=int(root.get("schema_version") or 1),
        title=str(root.get("title") or "").strip(),
        objective=str(root.get("objective") or "").strip(),
        created_by=str(root.get("created_by") or "").strip(),
        play_owner=play_owner,
        ball_holder=str(root.get("ball_holder") or play_owner).strip(),
        next_decision_owner=str(root.get("next_decision_owner") or play_owner).strip(),
        status=str(root.get("status") or "draft").strip(),
        scope={"include": coerce_string_list(scope.get("include")), "exclude": coerce_string_list(scope.get("exclude"))},
        constraints=_coerce_dict(root.get("constraints")),
        acceptance_criteria=coerce_string_list(root.get("acceptance_criteria")),
        steps=[step_from_mapping(item) for item in root.get("steps", []) if isinstance(item, dict)],
        unresolveds=_coerce_records(root.get("unresolveds")),
        contradictions=_coerce_records(root.get("contradictions")),
        created_at=str(root.get("created_at") or now),
        updated_at=str(root.get("updated_at") or now),
    )


def replace_step(packet: WorkPacket, replacement: WorkPacketStep, *, status: str | None = None, ball_holder: str | None = None) -> WorkPacket:
    return WorkPacket(
        packet_id=packet.packet_id,
        schema_version=packet.schema_version,
        title=packet.title,
        objective=packet.objective,
        created_by=packet.created_by,
        play_owner=packet.play_owner,
        ball_holder=ball_holder or packet.ball_holder,
        next_decision_owner=packet.next_decision_owner,
        status=status or packet.status,
        scope=packet.scope,
        constraints=packet.constraints,
        acceptance_criteria=packet.acceptance_criteria,
        steps=[replacement if step.step_id == replacement.step_id else step for step in packet.steps],
        unresolveds=packet.unresolveds,
        contradictions=packet.contradictions,
        created_at=packet.created_at,
        updated_at=now_utc(),
    )


def replace_packet_status(packet: WorkPacket, status: str, *, ball_holder: str | None = None) -> WorkPacket:
    return WorkPacket(
        packet_id=packet.packet_id,
        schema_version=packet.schema_version,
        title=packet.title,
        objective=packet.objective,
        created_by=packet.created_by,
        play_owner=packet.play_owner,
        ball_holder=ball_holder or packet.ball_holder,
        next_decision_owner=packet.next_decision_owner,
        status=status,
        scope=packet.scope,
        constraints=packet.constraints,
        acceptance_criteria=packet.acceptance_criteria,
        steps=packet.steps,
        unresolveds=packet.unresolveds,
        contradictions=packet.contradictions,
        created_at=packet.created_at,
        updated_at=now_utc(),
    )


def _scope_relatives(include: list[str], *, root: Path) -> list[str]:
    values: list[str] = []
    for path in include:
        resolved = resolve_repo_path(path, root=root)
        values.append(resolved.relative_to(root.resolve()).as_posix())
    return values


def _path_inside_any(path: str, scopes: list[str]) -> bool:
    if "." in scopes:
        return True
    normalized = path.strip("/")
    return any(normalized == scope.strip("/") or normalized.startswith(scope.strip("/") + "/") for scope in scopes)


def _has_cycle(steps: list[WorkPacketStep]) -> bool:
    deps = {step.step_id: set(step.depends_on) for step in steps}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> bool:
        if step_id in visiting:
            return True
        if step_id in visited:
            return False
        visiting.add(step_id)
        for dep in deps.get(step_id, set()):
            if visit(dep):
                return True
        visiting.remove(step_id)
        visited.add(step_id)
        return False

    return any(visit(step_id) for step_id in deps)


def validate_work_packet(packet: WorkPacket, *, root: Path) -> list[str]:
    errors: list[str] = []
    if not packet.packet_id:
        errors.append("packet_id_required")
    elif not PACKET_ID_RE.match(packet.packet_id):
        errors.append("packet_id_must_be_stable_path_safe")
    if packet.schema_version != 1:
        errors.append("unsupported_schema_version")
    if not packet.play_owner:
        errors.append("play_owner_required")
    if packet.next_decision_owner != packet.play_owner:
        errors.append("next_decision_owner_must_equal_play_owner")
    if packet.ball_holder not in {packet.play_owner, ACTIVE_EDITOR_NAME}:
        errors.append(f"ball_holder_must_be_play_owner_or_{ACTIVE_EDITOR_NAME}")
    if packet.status not in PACKET_STATUSES:
        errors.append(f"unsupported_packet_status:{packet.status}")
    if packet.constraints.get("mutation_authorized") is True:
        errors.append("packet_repository_mutation_requires_patch_authorization_not_packet_flag")
    if not packet.scope.get("include"):
        errors.append("packet_scope_required")
    if not packet.steps:
        errors.append("packet_steps_required")

    packet_scope_rels: list[str] = []
    for include in packet.scope.get("include", []):
        try:
            resolved = resolve_repo_path(include, root=root)
            if not resolved.exists():
                errors.append(f"packet_scope_path_not_found:{include}")
            packet_scope_rels.append(resolved.relative_to(root.resolve()).as_posix())
        except ValueError as exc:
            errors.append(str(exc))

    all_step_ids = {item.step_id for item in packet.steps}
    step_ids: set[str] = set()
    sequences: set[int] = set()
    for step in packet.steps:
        if not step.step_id:
            errors.append("step_id_required")
        elif step.step_id in step_ids:
            errors.append(f"duplicate_step_id:{step.step_id}")
        step_ids.add(step.step_id)
        if step.sequence in sequences:
            errors.append(f"duplicate_sequence:{step.sequence}")
        sequences.add(step.sequence)
        if step.operation not in STEP_OPERATIONS:
            errors.append(f"unsupported_step_operation:{step.step_id}:{step.operation}")
        if step.status not in STEP_STATUSES:
            errors.append(f"unsupported_step_status:{step.step_id}:{step.status}")
        for dep in step.depends_on:
            if dep not in all_step_ids:
                errors.append(f"unknown_dependency:{step.step_id}:{dep}")
        for include in step.scope.get("include") or []:
            try:
                rel = resolve_repo_path(include, root=root).relative_to(root.resolve()).as_posix()
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not _path_inside_any(rel, packet_scope_rels):
                errors.append(f"step_scope_expands_packet_scope:{step.step_id}:{include}")
    if _has_cycle(packet.steps):
        errors.append("circular_dependency_detected")
    return errors


def effective_step_scope(packet: WorkPacket, step: WorkPacketStep, *, root: Path) -> dict[str, list[str]]:
    include = step.scope.get("include") or packet.scope.get("include") or []
    packet_scope = _scope_relatives(packet.scope.get("include") or [], root=root)
    step_scope = _scope_relatives(include, root=root)
    for rel in step_scope:
        if not _path_inside_any(rel, packet_scope):
            raise ValueError(f"step_scope_expands_packet_scope:{step.step_id}:{rel}")
    return {
        "include": include,
        "exclude": list(dict.fromkeys([*(packet.scope.get("exclude") or []), *(step.scope.get("exclude") or [])])),
    }


def dependency_status(packet: WorkPacket, step: WorkPacketStep) -> list[str]:
    by_id = {item.step_id: item for item in packet.steps}
    unmet: list[str] = []
    for dep in step.depends_on:
        if by_id.get(dep) is None or by_id[dep].status not in DEPENDENCY_SATISFIED_STATUSES:
            unmet.append(dep)
    return unmet
