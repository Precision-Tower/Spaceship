from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import re

MISSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
RESOURCE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CONTEXT_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")

ALLOWED_MISSION_STATES = frozenset({
    "planned",
    "running",
    "waiting",
    "completed",
    "failed",
    "cancelled",
})
ALLOWED_TASK_STATES = frozenset({
    "pending",
    "active",
    "completed",
    "skipped",
    "blocked",
    "failed",
})
DEFAULT_INITIAL_STATE = "planned"


class MissionSpecValidationError(ValueError):
    def __init__(self, errors: list[str], *, phase: str = "validation") -> None:
        super().__init__("; ".join(errors))
        self.errors = errors
        self.phase = phase


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_mission_token(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(raw).strip()).strip("-")
    if not cleaned:
        raise ValueError("mission_id_empty")
    return cleaned


@dataclass(frozen=True)
class MissionIdentitySpec:
    mission_id: str
    title: str
    owner: str
    created_at: str


@dataclass(frozen=True)
class MissionTaskSpec:
    task_id: str
    title: str
    status: str = "pending"


@dataclass(frozen=True)
class MissionSpec:
    identity: MissionIdentitySpec
    objective: str
    inputs: tuple[str, ...] = ()
    context: dict[str, str] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    tasks: tuple[MissionTaskSpec, ...] = ()
    initial_state: str = DEFAULT_INITIAL_STATE
    parent_mission_id: str | None = None

    @property
    def mission_id(self) -> str:
        return self.identity.mission_id

    @property
    def title(self) -> str:
        return self.identity.title

    @property
    def owner(self) -> str:
        return self.identity.owner

    @property
    def created_at(self) -> str:
        return self.identity.created_at

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _coerce_string_tuple(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(_clean_text(value) for value in values)


def build_task_specs(tasks: list[str | dict[str, Any] | MissionTaskSpec] | tuple[str | dict[str, Any] | MissionTaskSpec, ...] | None) -> tuple[MissionTaskSpec, ...]:
    if not tasks:
        return ()
    result: list[MissionTaskSpec] = []
    for index, task in enumerate(tasks, start=1):
        if isinstance(task, MissionTaskSpec):
            result.append(task)
            continue
        if isinstance(task, dict):
            task_id = _clean_text(task.get("task_id") or f"task-{index}")
            title = _clean_text(task.get("title"))
            status = _clean_text(task.get("status") or "pending")
            result.append(MissionTaskSpec(task_id=task_id, title=title, status=status))
            continue
        text = _clean_text(task)
        if not text:
            result.append(MissionTaskSpec(task_id=f"task-{index}", title=""))
            continue
        parts = text.split(":", 2)
        if len(parts) == 1:
            result.append(MissionTaskSpec(task_id=f"task-{index}", title=parts[0].strip()))
        elif len(parts) == 2:
            result.append(MissionTaskSpec(task_id=_clean_text(parts[0]), title=_clean_text(parts[1])))
        else:
            result.append(MissionTaskSpec(task_id=_clean_text(parts[0]), title=_clean_text(parts[1]), status=parts[2].strip()))
    return tuple(result)


def build_mission_spec(
    *,
    mission_id: str,
    title: str,
    owner: str,
    objective: str,
    created_at: str | None = None,
    inputs: list[str] | tuple[str, ...] | None = None,
    context: dict[str, str] | None = None,
    constraints: list[str] | tuple[str, ...] | None = None,
    resources: list[str] | tuple[str, ...] | None = None,
    tasks: list[str | dict[str, Any] | MissionTaskSpec] | tuple[str | dict[str, Any] | MissionTaskSpec, ...] | None = None,
    initial_state: str = DEFAULT_INITIAL_STATE,
    parent_mission_id: str | None = None,
) -> MissionSpec:
    try:
        normalized_id = normalize_mission_token(mission_id)
    except ValueError as exc:
        raise MissionSpecValidationError([str(exc)], phase="normalization") from exc

    return MissionSpec(
        identity=MissionIdentitySpec(
            mission_id=normalized_id,
            title=_clean_text(title),
            owner=_clean_text(owner),
            created_at=created_at or utc_now(),
        ),
        objective=_clean_text(objective),
        inputs=_coerce_string_tuple(inputs),
        context={_clean_text(key): _clean_text(value) for key, value in (context or {}).items()},
        constraints=_coerce_string_tuple(constraints),
        resources=_coerce_string_tuple(resources),
        tasks=build_task_specs(tasks),
        initial_state=_clean_text(initial_state),
        parent_mission_id=_clean_text(parent_mission_id) if parent_mission_id else None,
    )


def validate_mission_spec(spec: MissionSpec) -> list[str]:
    errors: list[str] = []
    if not spec.identity.mission_id:
        errors.append("identity.mission_id is required")
    elif not MISSION_ID_RE.match(spec.identity.mission_id):
        errors.append(f"identity.mission_id is invalid: {spec.identity.mission_id}")
    if not spec.identity.title:
        errors.append("identity.title is required")
    if not spec.identity.owner:
        errors.append("identity.owner is required")
    if not spec.identity.created_at:
        errors.append("identity.created_at is required")
    if not spec.objective:
        errors.append("objective is required")
    if spec.initial_state not in ALLOWED_MISSION_STATES:
        errors.append(f"invalid lifecycle state: {spec.initial_state}")
    _validate_string_sequence("inputs", spec.inputs, errors)
    _validate_string_sequence("constraints", spec.constraints, errors)

    seen_resources: set[str] = set()
    for resource in spec.resources:
        if not resource:
            errors.append("empty resource is not allowed")
            continue
        if resource in seen_resources:
            errors.append(f"duplicate resource: {resource}")
        seen_resources.add(resource)
        if not RESOURCE_RE.match(resource):
            errors.append(f"resource must be an abstract capability token: {resource}")

    for key, value in spec.context.items():
        if not key:
            errors.append("context key is required")
        elif not CONTEXT_KEY_RE.match(key):
            errors.append(f"context key is invalid: {key}")
        if value == "":
            errors.append(f"context value is required for: {key}")

    seen_tasks: set[str] = set()
    for task in spec.tasks:
        if not task.task_id:
            errors.append("task.task_id is required")
        elif task.task_id in seen_tasks:
            errors.append(f"duplicate task.task_id: {task.task_id}")
        seen_tasks.add(task.task_id)
        if not task.title:
            errors.append(f"task.title is required for: {task.task_id or '<missing>'}")
        if task.status not in ALLOWED_TASK_STATES:
            errors.append(f"invalid task status for {task.task_id or '<missing>'}: {task.status}")

    if spec.parent_mission_id:
        if not MISSION_ID_RE.match(spec.parent_mission_id):
            errors.append(f"parent_mission_id is invalid: {spec.parent_mission_id}")
        if spec.parent_mission_id == spec.mission_id:
            errors.append("parent_mission_id cannot equal mission_id")
    return errors


def _validate_string_sequence(field: str, values: tuple[str, ...], errors: list[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if not value:
            errors.append(f"empty {field} entry is not allowed")
            continue
        if value in seen:
            errors.append(f"duplicate {field} entry: {value}")
        seen.add(value)


def require_valid_mission_spec(spec: MissionSpec) -> MissionSpec:
    errors = validate_mission_spec(spec)
    if errors:
        raise MissionSpecValidationError(errors)
    return spec
