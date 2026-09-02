from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Agency.Core.foundation.paths import DASHBOARD_ROOT


SUPPORTED_OPERATIONS = {"inspect", "propose_patch", "apply_patch", "verify"}
ACTIVE_EDITOR_NAME = "Editor"
TASK_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


@dataclass(frozen=True)
class PatchAuthorization:
    authorization_id: str
    work_packet_id: str
    step_id: str
    editor_task_id: str
    proposal_sha256: str
    baseline_hashes: dict[str, str]
    authorized_by: str
    play_owner: str
    authorized_editor: str
    allowed_paths: list[str]
    allowed_operations: list[str]
    created_at: str
    expires_at: str
    proposal_path: str | None = None
    used_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EditorTask:
    task_id: str
    schema_version: int
    issued_by: str
    editor: str
    play_owner: str
    ball_holder: str
    next_decision_owner: str
    objective: str
    operation: str
    scope: dict[str, list[str]]
    request: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    evidence_requirements: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_utc)
    work_packet_id: str | None = None
    parent_step_id: str | None = None

    @property
    def ball_owner(self) -> str:
        return self.play_owner

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ball_owner"] = self.play_owner
        return data


@dataclass(frozen=True)
class EditorResult:
    task_id: str
    schema_version: int
    status: str
    operation: str
    editor: str
    issued_by: str
    play_owner: str
    ball_holder: str
    next_decision_owner: str
    throw_completed: bool
    play_outcome: str
    objective: str
    evidence_bundle: dict[str, Any] | None
    observations: list[dict[str, Any]]
    proposed_changes: list[dict[str, Any]]
    patch_artifacts: list[dict[str, Any]]
    repository_mutations: list[dict[str, Any]]
    before_hashes: dict[str, str]
    after_hashes: dict[str, str]
    verification: list[dict[str, Any]]
    verification_results: list[dict[str, Any]]
    authorization_id: str | None
    proposal_sha256: str | None
    commit_performed: bool
    acceptance_claimed: bool
    unresolveds: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    limits_reached: list[str]
    errors: list[dict[str, Any]]
    started_at: str
    completed_at: str
    persistence_path: str

    @property
    def ball_owner(self) -> str:
        return self.play_owner

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["ball_owner"] = self.play_owner
        return data


def patch_authorization_from_mapping(data: dict[str, Any]) -> PatchAuthorization:
    if not isinstance(data, dict):
        raise ValueError("patch_authorization_must_be_object")
    return PatchAuthorization(
        authorization_id=str(data.get("authorization_id") or "").strip(),
        work_packet_id=str(data.get("work_packet_id") or "").strip(),
        step_id=str(data.get("step_id") or "").strip(),
        editor_task_id=str(data.get("editor_task_id") or "").strip(),
        proposal_sha256=str(data.get("proposal_sha256") or "").strip(),
        baseline_hashes=dict(data.get("baseline_hashes") or {}),
        authorized_by=str(data.get("authorized_by") or "").strip(),
        play_owner=str(data.get("play_owner") or data.get("ball_owner") or "").strip(),
        authorized_editor=str(data.get("authorized_editor") or "").strip(),
        allowed_paths=coerce_string_list(data.get("allowed_paths")),
        allowed_operations=coerce_string_list(data.get("allowed_operations")),
        created_at=str(data.get("created_at") or now_utc()),
        expires_at=str(data.get("expires_at") or "").strip(),
        proposal_path=str(data.get("proposal_path") or "").strip() or None,
        used_at=str(data.get("used_at") or "").strip() or None,
    )


def editor_task_from_mapping(data: dict[str, Any]) -> EditorTask:
    if not isinstance(data, dict):
        raise ValueError("editor_task_must_be_object")
    scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
    constraints = data.get("constraints") if isinstance(data.get("constraints"), dict) else {}
    request = data.get("request") if isinstance(data.get("request"), dict) else {}
    play_owner = str(data.get("play_owner") or data.get("ball_owner") or "").strip()
    return EditorTask(
        task_id=str(data.get("task_id") or "").strip(),
        schema_version=int(data.get("schema_version") or 1),
        issued_by=str(data.get("issued_by") or "").strip(),
        editor=str(data.get("editor") or "").strip(),
        play_owner=play_owner,
        ball_holder=str(data.get("ball_holder") or data.get("editor") or "").strip(),
        next_decision_owner=str(data.get("next_decision_owner") or play_owner).strip(),
        objective=str(data.get("objective") or "").strip(),
        operation=str(data.get("operation") or "").strip(),
        scope={
            "include": coerce_string_list(scope.get("include")),
            "exclude": coerce_string_list(scope.get("exclude")),
        },
        request=request,
        constraints=dict(constraints),
        evidence_requirements=coerce_string_list(data.get("evidence_requirements")),
        created_at=str(data.get("created_at") or now_utc()),
        work_packet_id=str(data.get("work_packet_id") or "").strip() or None,
        parent_step_id=str(data.get("parent_step_id") or "").strip() or None,
    )


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_repo_path(value: str, *, root: Path | None = None) -> Path:
    repo_root = (root or DASHBOARD_ROOT).resolve()
    raw = Path(str(value).strip())
    if not str(value).strip():
        raise ValueError("empty_path_rejected")
    if ".." in raw.parts:
        raise ValueError(f"path_traversal_rejected: {value}")
    candidate = raw if raw.is_absolute() else repo_root / raw
    resolved = candidate.resolve()
    if not _is_relative_to(resolved, repo_root):
        raise ValueError(f"path_escapes_repository_root: {value}")
    return resolved


def repo_relative(path: Path, *, root: Path | None = None) -> str:
    return path.resolve().relative_to((root or DASHBOARD_ROOT).resolve()).as_posix()


def _repository_wide_scope(include: list[str]) -> bool:
    return any(str(item).strip() in {"", ".", "./"} for item in include)


def validate_editor_task(task: EditorTask, *, root: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not task.task_id:
        errors.append("task_id_required")
    elif not TASK_ID_RE.match(task.task_id):
        errors.append("task_id_must_be_stable_path_safe")
    if task.schema_version != 1:
        errors.append("unsupported_schema_version")
    if not task.issued_by:
        errors.append("issued_by_required")
    if task.editor != ACTIVE_EDITOR_NAME:
        errors.append(f"editor_must_be_{ACTIVE_EDITOR_NAME}_for_current_adapter")
    if not task.play_owner:
        errors.append("play_owner_required")
    if task.next_decision_owner != task.play_owner:
        errors.append("next_decision_owner_must_equal_play_owner")
    if task.ball_holder != task.editor:
        errors.append("active_editor_task_ball_holder_must_be_editor")
    if task.operation not in SUPPORTED_OPERATIONS:
        errors.append(f"unknown_operation:{task.operation or 'missing'}")
    include = task.scope.get("include") or []
    if not include:
        errors.append("explicit_scope_required")
    constraints = task.constraints or {}
    if task.operation == "inspect" and constraints.get("read_only") is not True:
        errors.append("inspect_requires_read_only_true")
    if task.operation in {"inspect", "propose_patch"} and constraints.get("mutation_authorized") is True:
        errors.append("current_editor_boundary_rejects_mutation_authorized_true_without_patch_authorization")
    if task.operation == "propose_patch" and constraints.get("mutation_authorized") is not False:
        errors.append("propose_patch_requires_mutation_authorized_false")
    if task.operation == "apply_patch" and not (task.request.get("authorization") or task.request.get("authorization_path")):
        errors.append("apply_patch_requires_patch_authorization")
    if task.operation == "verify" and constraints.get("read_only") is not True:
        errors.append("verify_requires_read_only_true")
    if _repository_wide_scope(include):
        bounded = all(
            constraints.get(key) not in {None, ""}
            for key in ("max_files", "max_matches", "max_total_context_bytes")
        )
        if not bounded:
            errors.append("repository_wide_scope_requires_explicit_limits")
    for path in include:
        try:
            resolved = resolve_repo_path(path, root=root)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not resolved.exists():
            errors.append(f"scope_path_not_found:{path}")
    return errors
