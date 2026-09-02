from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Callable
from Agency.Core.work.missions.pipeline.implementation.work_packet_adapter import (
    build_mission_unit_work_packet,
    build_patch_authorization_from_review,
    mission_unit_packet_id,
)
from Agency.Core.work.work_packets import contracts as work_packets_contracts
from Agency.Core.work.work_packets import execution as work_packets_execution
from Agency.Core.work.work_packets import persistence as work_packets_persistence
from Agency.Core.runtime.commands import mission_command



@dataclass(frozen=True)
class ImplementationExecutionDependencies:
    """Local infrastructure required by implementation execution."""
    DASHBOARD_ROOT: Path
    MISSIONS_ROOT: Path
    MISSION_SCHEMA_VERSION: int
    IMPLEMENTATION_MAX_NEW_TOKENS: int
    MAX_IMPLEMENTATION_FILE_BYTES: int
    MAX_IMPLEMENTATION_PROMPT_CHARS: int
    MAX_VERIFICATION_OUTPUT_CHARS: int
    PYTHON: Path
    _append_mission_event: Callable[..., Any]
    _as_string_list: Callable[..., Any]
    _atomic_json: Callable[..., Any]
    _atomic_text: Callable[..., Any]
    _call_model: Callable[..., Any]
    _dedupe_manifest_paths: Callable[..., Any]
    _git_status_lines: Callable[..., Any]
    _is_relative_to: Callable[..., Any]
    _load_json: Callable[..., Any]
    _load_operator_notes: Callable[..., Any]
    _load_plan: Callable[..., Any]
    _load_proposal: Callable[..., Any]
    _load_required_mission_json: Callable[..., Any]
    _mission_intent_path: Callable[..., Any]
    _mission_proposal_json_path: Callable[..., Any]
    _mission_review_decision_json_path: Callable[..., Any]
    _mission_state_path: Callable[..., Any]
    _now: Callable[..., Any]
    _parse_model_json_object: Callable[..., Any]
    _read_text_file: Callable[..., Any]
    _require_model_ready: Callable[..., Any]
    _resolve_mission_dir: Callable[..., Any]
    _run_command: Callable[..., Any]
    _stable: Callable[..., Any]
    refresh_pinboard: Callable[..., Any]


_BOUND_DEPENDENCIES: ImplementationExecutionDependencies | None = None


def bind_dependencies(deps: ImplementationExecutionDependencies) -> None:
    """Bind infrastructure used by helpers shared with verification code."""
    global _BOUND_DEPENDENCIES
    _BOUND_DEPENDENCIES = deps
    namespace = globals()
    for field in fields(deps):
        namespace[field.name] = getattr(deps, field.name)


def run_mission_implement(
    deps: ImplementationExecutionDependencies,
    mission: str,
    *,
    dry_run: bool = False,
) -> int:
    bind_dependencies(deps)
    return _run_bound_mission_implement(
        argparse.Namespace(mission=mission, dry_run=dry_run)
    )


def _mission_implementation_dir(mission_dir: Path) -> Path:
    return mission_dir / "implementation"


def _mission_implementation_manifest_path(mission_dir: Path) -> Path:
    return _mission_implementation_dir(mission_dir) / "manifest.json"


def _safe_unit_dir_name(unit_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(unit_id or "").strip())
    return safe.strip(".-") or "unit"


def _mission_unit_dir(mission_dir: Path, unit_id: str) -> Path:
    return _mission_implementation_dir(mission_dir) / "units" / _safe_unit_dir_name(unit_id)


def _load_review_decision(mission_dir: Path) -> dict[str, Any]:
    decision = _load_required_mission_json(_mission_review_decision_json_path(mission_dir))
    if decision.get("authority") != "operator_review":
        raise ValueError("review authority is not operator_review")
    return decision


def _load_implementation_inputs(mission_dir: Path) -> dict[str, Any]:
    return {
        "intent": _load_required_mission_json(_mission_intent_path(mission_dir)),
        "state": _load_required_mission_json(_mission_state_path(mission_dir)),
        "plan": _load_plan(mission_dir),
        "proposal": _load_proposal(mission_dir),
        "review": _load_review_decision(mission_dir),
        "operator_notes": _load_operator_notes(mission_dir),
    }


def _normalize_implementation_operation(value: Any) -> str:
    text = str(value or "modify").strip().lower()
    if text in {"add", "create", "new"}:
        return "create"
    if text in {"remove", "delete", "unlink"}:
        return "delete"
    return "modify"


def _normalize_implementation_units(proposal: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    raw_units = proposal.get("implementation_units", [])
    if not isinstance(raw_units, list) or not raw_units:
        return [], ["proposal contains no implementation_units"]

    units: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_units, start=1):
        if not isinstance(raw, dict):
            errors.append(f"implementation unit {index} is not an object")
            continue
        unit_id = str(raw.get("id") or f"unit-{index:03d}").strip()
        if not unit_id:
            unit_id = f"unit-{index:03d}"
        if unit_id in seen_ids:
            errors.append(f"duplicate implementation unit id {unit_id}")
            continue
        seen_ids.add(unit_id)
        expected_files = _dedupe_manifest_paths(raw.get("expected_files", []))
        changes: list[dict[str, Any]] = []
        for change in raw.get("changes", []) if isinstance(raw.get("changes"), list) else []:
            if not isinstance(change, dict):
                continue
            path = str(change.get("path") or "").strip()
            if not path:
                continue
            operation = _normalize_implementation_operation(change.get("operation") or change.get("kind"))
            changes.append({
                "path": path,
                "operation": operation,
                "reason": str(change.get("reason") or "").strip(),
                "original_sha256": str(
                    change.get("original_sha256")
                    or change.get("expected_sha256")
                    or ""
                ).strip(),
            })
        if not changes:
            for path in expected_files:
                changes.append({
                    "path": path,
                    "operation": "modify",
                    "reason": "Expected implementation surface from proposal.",
                    "original_sha256": "",
                })
        if not changes:
            errors.append(f"{unit_id} has no expected files or changes")
        allowed_paths = _dedupe_manifest_paths([
            *expected_files,
            *[change["path"] for change in changes],
        ])
        units.append({
            "id": unit_id,
            "objective": str(raw.get("objective") or raw.get("name") or "").strip(),
            "expected_files": expected_files or allowed_paths,
            "dependencies": _as_string_list(raw.get("dependencies"), limit=12),
            "changes": changes,
            "verification": _as_string_list(raw.get("verification"), limit=12),
            "rollback": _as_string_list(raw.get("rollback"), limit=12),
            "supported_by": _as_string_list(raw.get("supported_by"), limit=12),
            "allowed_paths": allowed_paths,
            "no_mutation": bool(raw.get("no_mutation") or raw.get("implementation_not_required")),
        })

    unit_ids = {unit["id"] for unit in units}
    for unit in units:
        unit["dependency_ids"] = [
            dep for dep in unit.get("dependencies", [])
            if dep in unit_ids
        ]
    return units, errors


def _implementation_execution_order(proposal: dict[str, Any], units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {unit["id"]: unit for unit in units}
    ordered: list[dict[str, Any]] = []
    for item in _as_string_list(proposal.get("execution_order"), limit=max(12, len(units))):
        unit = by_id.get(item)
        if unit and unit not in ordered:
            ordered.append(unit)
            continue
        try:
            index = int(item) - 1
        except ValueError:
            index = -1
        if 0 <= index < len(units) and units[index] not in ordered:
            ordered.append(units[index])
    for unit in units:
        if unit not in ordered:
            ordered.append(unit)
    return ordered


def _unit_status_path(mission_dir: Path, unit_id: str) -> Path:
    return _mission_unit_dir(mission_dir, unit_id) / "status.json"


def _load_unit_status(mission_dir: Path, unit_id: str) -> dict[str, Any]:
    path = _unit_status_path(mission_dir, unit_id)
    data = _load_json(path)
    if not isinstance(data, dict) or "load_error" in data:
        return {
            "unit_id": unit_id,
            "status": "pending",
            "attempt": 0,
        }
    return data


def _implementation_manifest_from_units(
    mission_dir: Path,
    mission_id: str,
    proposal_path: Path,
    review_path: Path,
    units: list[dict[str, Any]],
    *,
    pre_existing_status: list[str] | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    unit_records: list[dict[str, Any]] = []
    complete = True
    for unit in units:
        status_data = _load_unit_status(mission_dir, unit["id"])
        status = str(status_data.get("status") or "pending")
        if status != "complete":
            complete = False
        unit_records.append({
            "id": unit["id"],
            "status": status,
            "attempts": int(status_data.get("attempt") or 0),
            "artifact_path": _stable(_unit_status_path(mission_dir, unit["id"])),
        })
    return {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": mission_id,
        "authority": "approved_implementation_execution",
        "proposal_path": _stable(proposal_path),
        "review_path": _stable(review_path),
        "units": unit_records,
        "implementation_complete": complete and bool(unit_records),
        "pre_existing_modified_paths": pre_existing_status or [],
        "updated_at": updated_at or _now(),
    }


def _write_implementation_manifest(
    mission_dir: Path,
    mission_id: str,
    proposal_path: Path,
    review_path: Path,
    units: list[dict[str, Any]],
    *,
    pre_existing_status: list[str] | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    manifest = _implementation_manifest_from_units(
        mission_dir,
        mission_id,
        proposal_path,
        review_path,
        units,
        pre_existing_status=pre_existing_status,
        updated_at=updated_at,
    )
    path = _mission_implementation_manifest_path(mission_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(path, manifest)
    return manifest


def _select_next_implementation_unit(
    proposal: dict[str, Any],
    units: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    manifest_status = {
        item.get("id"): str(item.get("status") or "pending")
        for item in manifest.get("units", [])
        if isinstance(item, dict)
    }
    ordered_units = _implementation_execution_order(proposal, units)
    blocked: list[str] = []
    for unit in ordered_units:
        status = manifest_status.get(unit["id"], "pending")
        if status == "complete":
            continue
        incomplete_deps = [
            dep for dep in unit.get("dependency_ids", [])
            if manifest_status.get(dep, "pending") != "complete"
        ]
        if incomplete_deps:
            blocked.append(f"{unit['id']} waits for {', '.join(incomplete_deps)}")
            continue
        return unit, None, blocked
    if all(manifest_status.get(unit["id"], "pending") == "complete" for unit in units):
        return None, "implementation_already_complete", []
    return None, "implementation_blocked", blocked


def _validate_implementation_authority(
    inputs: dict[str, Any],
    mission_id: str,
) -> tuple[bool, str | None, str | None]:
    state = inputs.get("state", {})
    review = inputs.get("review", {})
    proposal = inputs.get("proposal", {})
    if proposal.get("authority") != "implementation_proposal":
        return False, "invalid_proposal", "proposal/proposal.json is not an implementation proposal."
    if not proposal.get("implementation_units"):
        return False, "invalid_proposal", "proposal contains no implementation units."
    if review.get("decision") != "approved" or review.get("implementation_authorized") is not True:
        return False, "implementation_not_authorized", (
            "review/decision.json does not approve implementation."
        )
    if state.get("implementation_authorized") is not True:
        return False, "implementation_not_authorized", (
            "state.json does not record operator implementation authorization."
        )
    return True, None, None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _capture_file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": _stable(path),
            "exists": False,
            "sha256": None,
            "size_bytes": 0,
        }
    data = path.read_bytes()
    return {
        "path": _stable(path),
        "exists": True,
        "sha256": _sha256_bytes(data),
        "size_bytes": len(data),
    }


def _resolve_repo_file_path(raw_path: str) -> tuple[Path | None, str | None]:
    text = str(raw_path or "").strip().replace("\\", "/")
    if not text:
        return None, "empty file path"
    rel_path = Path(text)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        return None, f"unsafe file path: {text}"
    candidate = (DASHBOARD_ROOT / rel_path).resolve()
    if not _is_relative_to(candidate, DASHBOARD_ROOT.resolve()):
        return None, f"file path escapes repository root: {text}"
    return candidate, None


def _proposal_operation_map(unit: dict[str, Any]) -> dict[str, set[str]]:
    operations: dict[str, set[str]] = {}
    for path in unit.get("allowed_paths", []):
        operations.setdefault(path, set())
    for change in unit.get("changes", []):
        if not isinstance(change, dict):
            continue
        path = str(change.get("path") or "").strip()
        if not path:
            continue
        operations.setdefault(path, set()).add(
            _normalize_implementation_operation(change.get("operation") or change.get("kind"))
        )
    return operations


def _change_expected_hashes(unit: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for change in unit.get("changes", []):
        if not isinstance(change, dict):
            continue
        path = str(change.get("path") or "").strip()
        value = str(change.get("original_sha256") or "").strip()
        if path and value:
            hashes[path] = value
    return hashes


def _git_status_for_path(path: str) -> list[str]:
    result = _run_command(["git", "status", "--porcelain", "--", path], timeout=20)
    return result.get("stdout", "").splitlines()


def _capture_unit_file_context(
    unit: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    errors: list[str] = []
    file_context: list[dict[str, Any]] = []
    contents: dict[str, str] = {}
    expected_hashes = _change_expected_hashes(unit)
    for path in unit.get("allowed_paths", []):
        target, error = _resolve_repo_file_path(path)
        if error or target is None:
            errors.append(error or f"invalid path {path}")
            continue
        operation_set = _proposal_operation_map(unit).get(path, {"modify"})
        state = _capture_file_state(target)
        status_lines = _git_status_for_path(path)
        state["git_status"] = status_lines
        if status_lines and any(op in operation_set for op in {"modify", "delete"}) and path not in expected_hashes:
            errors.append(f"{path} has pre-existing git status without proposal hash: {status_lines}")
            continue
        if path in expected_hashes and state.get("sha256") != expected_hashes[path]:
            errors.append(f"{path} hash does not match proposal expected state")
            continue
        if "create" in operation_set and "modify" not in operation_set and "delete" not in operation_set:
            if target.exists():
                errors.append(f"{path} already exists for create operation")
            file_context.append({
                **state,
                "operation": "create",
                "content": "",
            })
            continue
        if not target.exists():
            errors.append(f"{path} does not exist for {', '.join(sorted(operation_set))} operation")
            continue
        text, read_error = _read_text_file(target)
        if read_error:
            errors.append(f"{path} could not be read as text: {read_error}")
            continue
        if text is None:
            errors.append(f"{path} has no readable text content")
            continue
        encoded = text.encode("utf-8")
        if len(encoded) > MAX_IMPLEMENTATION_FILE_BYTES:
            errors.append(f"{path} exceeds implementation file byte budget")
            continue
        contents[path] = text
        file_context.append({
            **state,
            "operation": ",".join(sorted(operation_set)),
            "content": text,
        })
    return file_context, contents, errors


def _implementation_system_context() -> str:
    return """You implement exactly one approved implementation unit.
Do not change architectural decisions.
Do not expand scope.
Do not modify files not listed in the unit.
Return valid compact JSON only.
Do not output patches or shell commands that mutate files.
Describe concrete edits in file_changes with complete new_content for each created or modified text file."""


def _call_model_for_implementation(
    prompt: str,
    system_context: str,
    max_new_tokens: int,
) -> dict[str, Any]:
    mock = os.environ.get("AGENCY_MOCK_IMPLEMENTATION_RESPONSE")
    if os.environ.get("AGENCY_MOCK_EMPTY_MODEL") != "1" and mock is not None:
        return {
            "ok": True,
            "status": "draft_generated",
            "reason": "AGENCY_MOCK_IMPLEMENTATION_RESPONSE supplied draft",
            "draft": mock,
            "usage": {"mock": True},
        }
    return _call_model(prompt, system_context, max_new_tokens)


def _build_implementation_prompt(
    inputs: dict[str, Any],
    unit: dict[str, Any],
    file_context: list[dict[str, Any]],
) -> str:
    plan = inputs.get("plan", {})
    proposal = inputs.get("proposal", {})
    supported_by = set(unit.get("supported_by", []))
    findings = [
        {
            "id": item.get("id"),
            "claim": item.get("claim"),
            "confidence": item.get("confidence"),
        }
        for item in plan.get("causal_findings", [])
        if isinstance(item, dict) and item.get("id") in supported_by
    ][:6]
    compact_files = []
    for item in file_context:
        compact_files.append({
            "path": item.get("path"),
            "exists": item.get("exists"),
            "sha256": item.get("sha256"),
            "size_bytes": item.get("size_bytes"),
            "operation": item.get("operation"),
            "content": str(item.get("content") or "")[:MAX_IMPLEMENTATION_FILE_BYTES],
        })
    context = {
        "mission_id": proposal.get("mission_id"),
        "intent": inputs.get("intent", {}).get("intent"),
        "proposal_summary": proposal.get("summary"),
        "unit": {
            "id": unit.get("id"),
            "objective": unit.get("objective"),
            "changes": unit.get("changes"),
            "expected_files": unit.get("expected_files"),
            "verification": unit.get("verification"),
            "rollback": unit.get("rollback"),
            "supported_by": unit.get("supported_by"),
        },
        "findings": findings,
        "operator_notes": str(inputs.get("operator_notes") or "")[:1000],
        "files": compact_files,
    }
    shape = (
        "Return JSON: {unit_id, summary, file_changes:[{path, operation, "
        "original_sha256, new_content}], verification_commands:[], rollback_notes:[]}."
    )
    prompt = f"""You are implementing one approved implementation unit.
Do not inspect the repository. Use only the supplied unit, plan findings, and listed file contents.
Do not change architecture, expand scope, or modify files absent from the selected unit.
For modify/create operations, include full new_content. For delete, omit new_content.
{shape}
Context:{json.dumps(context, separators=(',', ':'))}
"""
    if len(prompt) > MAX_IMPLEMENTATION_PROMPT_CHARS:
        for item in compact_files:
            item["content"] = str(item.get("content") or "")[:3000]
        context["files"] = compact_files
        prompt = f"""Implement one approved unit. Return valid JSON only. No scope expansion.
{shape}
Context:{json.dumps(context, separators=(',', ':'))}
"""
    if len(prompt) > MAX_IMPLEMENTATION_PROMPT_CHARS:
        prompt = prompt[:MAX_IMPLEMENTATION_PROMPT_CHARS] + "\n"
    return prompt


def _normalize_implementation_response(
    model_payload: dict[str, Any],
    unit: dict[str, Any],
) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    for raw in model_payload.get("file_changes", []) if isinstance(model_payload.get("file_changes"), list) else []:
        if not isinstance(raw, dict):
            continue
        operation = _normalize_implementation_operation(raw.get("operation") or raw.get("kind"))
        path = str(raw.get("path") or "").strip()
        if not path:
            continue
        change = {
            "path": path,
            "operation": operation,
            "original_sha256": str(raw.get("original_sha256") or "").strip(),
        }
        if operation in {"modify", "create"}:
            change["new_content"] = str(raw.get("new_content") if raw.get("new_content") is not None else raw.get("content") or "")
        changes.append(change)
    return {
        "unit_id": str(model_payload.get("unit_id") or unit.get("id") or "").strip(),
        "summary": str(model_payload.get("summary") or "").strip(),
        "file_changes": changes,
        "verification_commands": _as_string_list(model_payload.get("verification_commands"), limit=12),
        "rollback_notes": _as_string_list(model_payload.get("rollback_notes"), limit=12),
    }


def _validate_implementation_response(
    response: dict[str, Any],
    unit: dict[str, Any],
    before_by_path: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if response.get("unit_id") != unit.get("id"):
        errors.append("implementation response unit_id does not match selected unit")
    allowed_paths = set(unit.get("allowed_paths", []))
    operation_map = _proposal_operation_map(unit)
    seen_paths: set[str] = set()
    normalized_changes: list[dict[str, Any]] = []
    for change in response.get("file_changes", []):
        path = str(change.get("path") or "").strip()
        operation = _normalize_implementation_operation(change.get("operation"))
        if path in seen_paths:
            errors.append(f"duplicate file operation for {path}")
            continue
        seen_paths.add(path)
        if path not in allowed_paths:
            errors.append(f"{path} is not authorized by selected implementation unit")
            continue
        target, path_error = _resolve_repo_file_path(path)
        if path_error or target is None:
            errors.append(path_error or f"invalid path {path}")
            continue
        allowed_ops = operation_map.get(path) or {"modify"}
        if operation not in allowed_ops:
            errors.append(f"{path} operation {operation} is not declared by proposal")
            continue
        before_state = before_by_path.get(path)
        if before_state is None:
            errors.append(f"{path} was not captured before implementation")
            continue
        if operation == "create" and before_state.get("exists"):
            errors.append(f"{path} already existed before create operation")
            continue
        if operation in {"modify", "delete"} and not before_state.get("exists"):
            errors.append(f"{path} did not exist before {operation} operation")
            continue
        original_sha = str(change.get("original_sha256") or "").strip()
        if original_sha and original_sha != before_state.get("sha256"):
            errors.append(f"{path} original_sha256 does not match captured before state")
            continue
        if operation in {"modify", "create"} and "new_content" not in change:
            errors.append(f"{path} {operation} operation has no new_content")
            continue
        normalized_changes.append({
            "path": path,
            "target": target,
            "operation": operation,
            "original_sha256": original_sha,
            "new_content": change.get("new_content", ""),
        })
    if not normalized_changes and not unit.get("no_mutation"):
        errors.append("implementation response contains no file changes")
    return normalized_changes, errors


def _write_unit_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(path, payload)


def _write_unit_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_text(path, text)


def _write_unit_status(
    mission_dir: Path,
    unit_id: str,
    status: str,
    *,
    started_at: str,
    attempt: int,
    completed_at: str | None = None,
    failed_at: str | None = None,
    error: dict[str, Any] | None = None,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "status": status,
        "started_at": started_at,
        "attempt": attempt,
    }
    if completed_at:
        payload["completed_at"] = completed_at
    if failed_at:
        payload["failed_at"] = failed_at
    if error:
        payload["error"] = error
    if artifact_dir is not None:
        payload["artifact_dir"] = _stable(artifact_dir)
    _write_unit_json(_unit_status_path(mission_dir, unit_id), payload)
    return payload


def _actual_current_matches_before(before_state: dict[str, Any], target: Path) -> bool:
    current = _capture_file_state(target)
    return current.get("exists") == before_state.get("exists") and current.get("sha256") == before_state.get("sha256")


def _apply_file_changes(
    changes: list[dict[str, Any]],
    before_by_path: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    applied: list[dict[str, Any]] = []
    errors: list[str] = []
    for change in changes:
        path = str(change["path"])
        target: Path = change["target"]
        operation = str(change["operation"])
        before_state = before_by_path[path]
        if not _actual_current_matches_before(before_state, target):
            errors.append(f"{path} changed after before-state capture")
            break
        try:
            if operation == "delete":
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                _atomic_text(target, str(change.get("new_content") or ""))
        except Exception as exc:
            errors.append(f"{path}: {type(exc).__name__}: {exc}")
            break
        after_state = _capture_file_state(target)
        applied.append({
            "path": path,
            "operation": operation,
            "before": before_state,
            "after": after_state,
            "changed": before_state.get("sha256") != after_state.get("sha256")
            or before_state.get("exists") != after_state.get("exists"),
        })
    return applied, errors


def _generate_unit_diff(
    before_contents: dict[str, str],
    changes: list[dict[str, Any]],
) -> str:
    pieces: list[str] = []
    for change in changes:
        path = str(change["path"])
        target: Path = change["target"]
        operation = str(change["operation"])
        before_text = before_contents.get(path, "") if operation != "create" else ""
        if operation == "delete":
            after_text = ""
        else:
            after_text = str(change.get("new_content") or "")
        before_lines = before_text.splitlines()
        after_lines = after_text.splitlines()
        for line in difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        ):
            pieces.append(f"{line}\n")
    return "".join(pieces)


def _verification_file_arg_safe(raw_path: str) -> tuple[bool, str | None]:
    text = str(raw_path or "").strip()
    if not text:
        return False, "empty verification file path"
    candidate_path = Path(text)
    if ".." in candidate_path.parts:
        return False, f"verification file path contains traversal: {text}"
    if candidate_path.is_absolute():
        resolved = candidate_path.resolve()
    else:
        resolved = (DASHBOARD_ROOT / candidate_path).resolve()
    if not _is_relative_to(resolved, DASHBOARD_ROOT.resolve()):
        return False, f"verification file path escapes repository root: {text}"
    return True, None


def _verification_command_allowed(command: str) -> tuple[list[str] | None, str | None]:
    text = str(command or "").strip()
    if not text:
        return None, "empty verification command"
    if any(token in text for token in ("&&", "||", ";", "|", ">", "<", "`", "$(")):
        return None, "shell operators are not allowed in verification commands"
    try:
        argv = shlex.split(text)
    except ValueError as exc:
        return None, f"invalid command quoting: {exc}"
    if not argv:
        return None, "empty verification command"
    executable = Path(argv[0]).name

    if executable == "git":
        normalized = ["git", *argv[1:]]
        if normalized in (
            ["git", "status", "--short"],
            ["git", "diff", "--check"],
        ):
            return normalized, None
        return None, f"git verification command is not allowed: {text}"
    if argv[0] == str(PYTHON) or executable in {"python", "python3"}:
        if len(argv) >= 3 and argv[1:3] == ["-m", "py_compile"]:
            if len(argv) == 3:
                return None, "py_compile verification requires at least one file"
            for file_arg in argv[3:]:
                if file_arg.startswith("-"):
                    return None, f"py_compile option is not allowed: {file_arg}"
                safe, reason = _verification_file_arg_safe(file_arg)
                if not safe:
                    return None, reason
            return argv, None
        return None, "only python -m py_compile is allowed for python verification"
    if executable in {"bash", "sh"}:
        if len(argv) >= 3 and argv[1] == "-n":
            for file_arg in argv[2:]:
                if file_arg.startswith("-"):
                    return None, f"shell syntax option is not allowed: {file_arg}"
                safe, reason = _verification_file_arg_safe(file_arg)
                if not safe:
                    return None, reason
            return argv, None
        return None, "only shell syntax checks are allowed"
    if executable.startswith("godot"):
        if "--check-only" in argv or "--quit" in argv:
            return argv, None
        return None, "godot verification must include --check-only or --quit"
    return None, f"verification executable is not allowlisted: {argv[0]}"


def _run_unit_verification(commands: list[str]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    all_passed = True
    for command in commands:
        started_at = _now()
        argv, error = _verification_command_allowed(command)
        if error or argv is None:
            all_passed = False
            results.append({
                "command": command,
                "exit_code": 126,
                "stdout": "",
                "stderr": error or "verification command rejected",
                "started_at": started_at,
                "completed_at": _now(),
            })
            continue
        try:
            proc = subprocess.run(
                argv,
                cwd=DASHBOARD_ROOT,
                text=True,
                capture_output=True,
                timeout=60,
            )
            exit_code = proc.returncode
            stdout = proc.stdout[-MAX_VERIFICATION_OUTPUT_CHARS:]
            stderr = proc.stderr[-MAX_VERIFICATION_OUTPUT_CHARS:]
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = str(exc.stdout or "")[-MAX_VERIFICATION_OUTPUT_CHARS:]
            stderr = str(exc.stderr or "verification command timed out")[-MAX_VERIFICATION_OUTPUT_CHARS:]
        completed_at = _now()
        if exit_code != 0:
            all_passed = False
        results.append({
            "command": command,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "started_at": started_at,
            "completed_at": completed_at,
        })
    return {
        "schema_version": MISSION_SCHEMA_VERSION,
        "all_passed": all_passed,
        "commands": results,
    }


def _render_unit_rollback(
    unit: dict[str, Any],
    applied: list[dict[str, Any]],
    before_by_path: dict[str, dict[str, Any]],
    rollback_notes: list[str],
) -> str:
    lines = [
        "# Unit Rollback",
        "",
        f"Unit: {unit.get('id')}",
        "",
        "Rollback was not executed automatically.",
        "",
        "## Files Changed",
    ]
    if not applied:
        lines.append("- none")
    for item in applied:
        path = item.get("path")
        before = before_by_path.get(path, {})
        lines.append(
            f"- {path}: operation={item.get('operation')}, "
            f"original_sha256={before.get('sha256')}, "
            f"after_sha256={item.get('after', {}).get('sha256')}"
        )
    lines.extend([
        "",
        "## Manual Reversal",
    ])
    if rollback_notes:
        lines.extend(f"- {note}" for note in rollback_notes)
    else:
        for item in applied:
            path = item.get("path")
            operation = item.get("operation")
            if operation == "create":
                lines.append(f"- Remove created file {path}.")
            elif operation == "delete":
                lines.append(f"- Restore deleted file {path} from version control or before-state artifacts.")
            else:
                lines.append(f"- Restore {path} to original hash {before_by_path.get(path, {}).get('sha256')}.")
    lines.append("")
    return "\n".join(lines)


def _implementation_state_payload(
    state_data: dict[str, Any],
    mission_id: str,
    manifest: dict[str, Any],
    *,
    status: str | None = None,
) -> dict[str, Any]:
    complete = bool(manifest.get("implementation_complete"))
    updated_at = str(manifest.get("updated_at") or _now())
    if complete:
        phase = "implemented"
        state_status = "implementation_complete"
        next_action = {
            "command": mission_command("verify", mission_id),
            "authority": "read_only_verification",
            "reason": "All approved implementation units are complete.",
        }
    else:
        phase = "implementing"
        state_status = status or "implementation_in_progress"
        next_action = {
            "command": mission_command("implement", mission_id),
            "authority": "approved_implementation_execution",
            "reason": "Additional approved implementation units remain.",
        }
    unresolved: list[str] = []
    for item in state_data.get("unresolved", []):
        text = str(item)
        if text in {"Implementation has not started.", "Implementation remains incomplete."}:
            continue
        if text not in unresolved:
            unresolved.append(text)
    if not complete and "Implementation remains incomplete." not in unresolved:
        unresolved.append("Implementation remains incomplete.")
    return {
        **state_data,
        "schema_version": state_data.get("schema_version", MISSION_SCHEMA_VERSION),
        "mission_id": mission_id,
        "updated_at": updated_at,
        "phase": phase,
        "status": state_status,
        "implementation_authorized": True,
        "implementation_enabled": True,
        "implementation_complete": complete,
        "next_action": next_action,
        "unresolved": unresolved,
        "implementation": {
            "path": _stable(_mission_implementation_manifest_path(MISSIONS_ROOT / mission_id)),
            "updated_at": updated_at,
            "schema_version": MISSION_SCHEMA_VERSION,
            "complete": complete,
        },
    }


def _implementation_failure(
    status: str,
    mission_id: str | None,
    reason: str,
    *,
    next_action: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    exit_code: int = 1,
) -> int:
    payload = {
        "ok": False,
        "status": status,
        "error": status,
        "mission_id": mission_id,
        "reason": reason,
        "authority": "approved_implementation_execution",
        "source_files_modified": False,
    }
    if next_action:
        payload["next_action"] = next_action
    if extra:
        payload.update(extra)
    print(json.dumps(payload, indent=2))
    return exit_code


def _record_implementation_unit_failure(
    mission_dir: Path,
    mission_id: str,
    inputs: dict[str, Any],
    units: list[dict[str, Any]],
    unit: dict[str, Any],
    *,
    started_at: str,
    attempt: int,
    failure_status: str,
    error_type: str,
    error_message: str,
    pre_existing_status: list[str],
    extra_artifacts: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    failed_at = _now()
    unit_dir = _mission_unit_dir(mission_dir, unit["id"])
    attempt_dir = unit_dir / f"attempt_{attempt:03d}"
    if extra_artifacts:
        for name, payload in extra_artifacts.items():
            if isinstance(payload, str):
                _write_unit_text(attempt_dir / name, payload)
                _write_unit_text(unit_dir / name, payload)
            elif isinstance(payload, dict):
                _write_unit_json(attempt_dir / name, payload)
                _write_unit_json(unit_dir / name, payload)
    status_payload = _write_unit_status(
        mission_dir,
        unit["id"],
        "failed",
        started_at=started_at,
        attempt=attempt,
        failed_at=failed_at,
        error={
            "type": error_type,
            "message": error_message,
        },
        artifact_dir=attempt_dir,
    )
    _write_unit_json(attempt_dir / "status.json", status_payload)
    manifest = _write_implementation_manifest(
        mission_dir,
        mission_id,
        _mission_proposal_json_path(mission_dir),
        _mission_review_decision_json_path(mission_dir),
        units,
        pre_existing_status=pre_existing_status,
        updated_at=failed_at,
    )
    state_payload = _implementation_state_payload(
        inputs["state"],
        mission_id,
        manifest,
        status=failure_status,
    )
    _atomic_json(_mission_state_path(mission_dir), state_payload)
    return manifest, state_payload


def _run_bound_mission_implement(args: argparse.Namespace) -> int:
    try:
        mission_dir = _resolve_mission_dir(args.mission)
    except ValueError as exc:
        return _implementation_failure(
            "mission_not_found",
            str(args.mission),
            str(exc),
            exit_code=2,
        )

    mission_id = mission_dir.name
    proposal_path = _mission_proposal_json_path(mission_dir)
    review_path = _mission_review_decision_json_path(mission_dir)
    if not proposal_path.exists():
        next_action = {
            "command": mission_command("propose", mission_id),
            "authority": "implementation_proposal",
        }
        return _implementation_failure(
            "proposal_required",
            mission_id,
            "proposal/proposal.json is required before implementation.",
            next_action=next_action,
            exit_code=1,
        )
    if not review_path.exists():
        next_action = {
            "command": mission_command("review", mission_id, "--approve"),
            "authority": "operator_review",
        }
        return _implementation_failure(
            "review_required",
            mission_id,
            "review/decision.json is required before implementation.",
            next_action=next_action,
            exit_code=1,
        )

    try:
        inputs = _load_implementation_inputs(mission_dir)
    except ValueError as exc:
        return _implementation_failure(
            "invalid_proposal",
            mission_id,
            str(exc),
            exit_code=2,
        )

    authorized, auth_error, auth_reason = _validate_implementation_authority(inputs, mission_id)
    if not authorized:
        next_action = {
            "command": mission_command("review", mission_id, "--approve"),
            "authority": "operator_review",
        }
        return _implementation_failure(
            auth_error or "implementation_not_authorized",
            mission_id,
            auth_reason or "Implementation is not authorized.",
            next_action=next_action,
            exit_code=1,
        )

    units, unit_errors = _normalize_implementation_units(inputs["proposal"])
    if unit_errors or not units:
        return _implementation_failure(
            "invalid_proposal",
            mission_id,
            "Proposal implementation units are invalid.",
            extra={"validation_errors": unit_errors},
            exit_code=1,
        )

    pre_existing_status = _git_status_lines()
    manifest = _write_implementation_manifest(
        mission_dir,
        mission_id,
        proposal_path,
        review_path,
        units,
        pre_existing_status=pre_existing_status,
        updated_at=_now(),
    )
    unit, blocked_status, blocked_reasons = _select_next_implementation_unit(
        inputs["proposal"],
        units,
        manifest,
    )
    if blocked_status == "implementation_already_complete":
        state_payload = _implementation_state_payload(inputs["state"], mission_id, manifest)
        _atomic_json(_mission_state_path(mission_dir), state_payload)
        payload = {
            "ok": False,
            "status": "implementation_already_complete",
            "mission_id": mission_id,
            "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
            "next_action": state_payload["next_action"],
            "authority": "approved_implementation_execution",
            "source_files_modified": False,
        }
        print(json.dumps(payload, indent=2))
        return 0
    if blocked_status == "implementation_blocked" or unit is None:
        return _implementation_failure(
            "implementation_blocked",
            mission_id,
            "No implementation unit has all dependencies complete.",
            extra={"blocked": blocked_reasons},
            exit_code=1,
        )

    if bool(getattr(args, "dry_run", False)):
        wp_preview = build_mission_unit_work_packet(
            mission_id=mission_id,
            unit=unit,
            proposal_path=proposal_path,
            review_path=review_path,
            patch_path=_mission_unit_dir(mission_dir, unit["id"]) / "changes.patch",
            baseline_hashes={},
            play_owner="operator",
        )
        payload = {
            "ok": True,
            "status": "implementation_dry_run",
            "mission_id": mission_id,
            "selected_unit": unit,
            "work_packet_id": wp_preview.packet_id,
            "work_packet_steps": [s.to_dict() for s in wp_preview.steps],
            "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
            "source_files_modified": False,
            "authority": "approved_implementation_execution",
        }
        print(json.dumps(payload, indent=2))
        return 0

    unit_status = _load_unit_status(mission_dir, unit["id"])
    attempt = int(unit_status.get("attempt") or 0) + 1
    started_at = _now()
    unit_dir = _mission_unit_dir(mission_dir, unit["id"])
    attempt_dir = unit_dir / f"attempt_{attempt:03d}"
    file_context, before_contents, context_errors = _capture_unit_file_context(unit)
    before_by_path = {
        str(item.get("path")): {
            key: value
            for key, value in item.items()
            if key != "content"
        }
        for item in file_context
    }
    before_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "unit_id": unit["id"],
        "captured_at": _now(),
        "files": list(before_by_path.values()),
    }
    if context_errors:
        context_status = "unsafe_file_path" if any(
            "unsafe file path" in error or "escapes repository root" in error or "empty file path" in error
            for error in context_errors
        ) else "unexpected_file_state"
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status=context_status,
            error_type=context_status,
            error_message="; ".join(context_errors),
            pre_existing_status=pre_existing_status,
            extra_artifacts={"before.json": before_payload},
        )
        return _implementation_failure(
            context_status,
            mission_id,
            "Selected implementation unit target files are not in the expected state.",
            extra={
                "unit_id": unit["id"],
                "errors": context_errors,
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
            },
            exit_code=1,
        )

    prompt = _build_implementation_prompt(inputs, unit, file_context)
    request_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": mission_id,
        "unit": unit,
        "started_at": started_at,
        "attempt": attempt,
        "prompt_chars": len(prompt),
        "system_context": _implementation_system_context(),
        "max_new_tokens": IMPLEMENTATION_MAX_NEW_TOKENS,
        "pre_existing_modified_paths": pre_existing_status,
    }
    _write_unit_json(attempt_dir / "request.json", request_payload)
    _write_unit_json(unit_dir / "request.json", request_payload)
    _write_unit_json(attempt_dir / "before.json", before_payload)
    _write_unit_json(unit_dir / "before.json", before_payload)
    in_progress = _write_unit_status(
        mission_dir,
        unit["id"],
        "in_progress",
        started_at=started_at,
        attempt=attempt,
        artifact_dir=attempt_dir,
    )
    _write_unit_json(attempt_dir / "status.json", in_progress)
    _write_implementation_manifest(
        mission_dir,
        mission_id,
        proposal_path,
        review_path,
        units,
        pre_existing_status=pre_existing_status,
        updated_at=started_at,
    )

    ready, model_server_status, _started_model_server = _require_model_ready(
        start_model_server=False,
    )
    if not ready and os.environ.get("AGENCY_MOCK_IMPLEMENTATION_RESPONSE") is None:
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status="model_inference_failed",
            error_type="model_inference_failed",
            error_message="Model server is not ready for implementation.",
            pre_existing_status=pre_existing_status,
            extra_artifacts={"before.json": before_payload, "request.json": request_payload},
        )
        return _implementation_failure(
            "model_inference_failed",
            mission_id,
            "Model server is not ready for implementation.",
            extra={
                "unit_id": unit["id"],
                "model_server_status": model_server_status,
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
            },
            exit_code=1,
        )

    model_response = _call_model_for_implementation(
        prompt,
        _implementation_system_context(),
        IMPLEMENTATION_MAX_NEW_TOKENS,
    )
    draft = str(model_response.get("draft") or "").strip()
    if not model_response.get("ok") or model_response.get("status") != "draft_generated" or not draft:
        result_payload = {
            "schema_version": MISSION_SCHEMA_VERSION,
            "unit_id": unit["id"],
            "summary": "",
            "model_response": model_response,
            "file_changes": [],
            "applied": [],
        }
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status="model_inference_failed",
            error_type="model_inference_failed",
            error_message="Implementation model did not return a usable draft.",
            pre_existing_status=pre_existing_status,
            extra_artifacts={
                "before.json": before_payload,
                "request.json": request_payload,
                "result.json": result_payload,
                "changes.diff": "",
                "rollback.md": _render_unit_rollback(unit, [], before_by_path, unit.get("rollback", [])),
            },
        )
        return _implementation_failure(
            "model_inference_failed",
            mission_id,
            "Implementation model did not return a usable draft.",
            extra={
                "unit_id": unit["id"],
                "model_response": model_response,
                "model_server_status": model_server_status,
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
            },
            exit_code=1,
        )

    parsed = _parse_model_json_object(draft)
    if parsed is None:
        result_payload = {
            "schema_version": MISSION_SCHEMA_VERSION,
            "unit_id": unit["id"],
            "summary": "",
            "model_response_status": model_response.get("status"),
            "model_draft_excerpt": draft[:1200],
            "file_changes": [],
            "applied": [],
        }
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status="invalid_implementation_response",
            error_type="invalid_implementation_response",
            error_message="Implementation model response was not valid JSON.",
            pre_existing_status=pre_existing_status,
            extra_artifacts={
                "before.json": before_payload,
                "request.json": request_payload,
                "result.json": result_payload,
                "changes.diff": "",
                "rollback.md": _render_unit_rollback(unit, [], before_by_path, unit.get("rollback", [])),
            },
        )
        return _implementation_failure(
            "invalid_implementation_response",
            mission_id,
            "Implementation model response was not valid JSON.",
            extra={
                "unit_id": unit["id"],
                "model_response_status": model_response.get("status"),
                "model_draft_excerpt": draft[:1200],
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
            },
            exit_code=1,
        )

    implementation_response = _normalize_implementation_response(parsed, unit)
    validated_changes, response_errors = _validate_implementation_response(
        implementation_response,
        unit,
        before_by_path,
    )
    if response_errors:
        response_status = "unsafe_file_path" if any(
            "unsafe file path" in error or "escapes repository root" in error
            for error in response_errors
        ) else "invalid_implementation_response"
        result_payload = {
            "schema_version": MISSION_SCHEMA_VERSION,
            "unit_id": unit["id"],
            "summary": implementation_response.get("summary", ""),
            "model_response": model_response,
            "file_changes": implementation_response.get("file_changes", []),
            "applied": [],
            "validation_errors": response_errors,
        }
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status=response_status,
            error_type=response_status,
            error_message="; ".join(response_errors),
            pre_existing_status=pre_existing_status,
            extra_artifacts={
                "before.json": before_payload,
                "request.json": request_payload,
                "result.json": result_payload,
                "changes.diff": "",
                "rollback.md": _render_unit_rollback(unit, [], before_by_path, implementation_response.get("rollback_notes", [])),
            },
        )
        return _implementation_failure(
            response_status,
            mission_id,
            "Implementation model response failed validation.",
            extra={
                "unit_id": unit["id"],
                "validation_errors": response_errors,
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
            },
            exit_code=1,
        )

    patch_text = _generate_unit_diff(before_contents, validated_changes)
    patch_path = attempt_dir / "changes.patch"
    _write_unit_text(patch_path, patch_text)
    _write_unit_text(unit_dir / "changes.patch", patch_text)
    _write_unit_text(attempt_dir / "changes.diff", patch_text)
    _write_unit_text(unit_dir / "changes.diff", patch_text)

    baseline_hashes = {
        path: before_by_path[path]["sha256"]
        for path in unit.get("allowed_paths", [])
        if before_by_path.get(path, {}).get("exists") and before_by_path.get(path, {}).get("sha256")
    }

    play_owner = str(inputs.get("review", {}).get("reviewed_by") or inputs.get("intent", {}).get("created_by") or "operator").strip() or "operator"

    packet = build_mission_unit_work_packet(
        mission_id=mission_id,
        unit=unit,
        proposal_path=proposal_path,
        review_path=review_path,
        patch_path=patch_path,
        baseline_hashes=baseline_hashes,
        play_owner=play_owner,
    )

    work_packets_persistence.save_packet(packet)

    try:
        auth = build_patch_authorization_from_review(
            review=inputs["review"],
            packet_id=packet.packet_id,
            apply_step_id="apply-patch",
            patch_path=patch_path,
            baseline_hashes=baseline_hashes,
            allowed_paths=unit.get("allowed_paths", []),
            play_owner=play_owner,
        )
        work_packets_persistence.save_authorization(packet.packet_id, auth.authorization_id, auth.to_dict())
    except ValueError as exc:
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status="authorization_construction_failed",
            error_type="authorization_construction_failed",
            error_message=str(exc),
            pre_existing_status=pre_existing_status,
            extra_artifacts={
                "before.json": before_payload,
                "request.json": request_payload,
                "rollback.md": _render_unit_rollback(unit, [], before_by_path, implementation_response.get("rollback_notes", [])),
            },
        )
        return _implementation_failure(
            "authorization_construction_failed",
            mission_id,
            f"Patch authorization construction failed: {exc}",
            extra={
                "unit_id": unit["id"],
                "work_packet_id": packet.packet_id,
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
            },
            exit_code=1,
        )

    select_res = work_packets_execution.select_step(packet.packet_id, "apply-patch", play_owner)
    if not select_res.get("ok"):
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status="work_packet_step_selection_failed",
            error_type="work_packet_step_selection_failed",
            error_message="; ".join(select_res.get("errors", [])),
            pre_existing_status=pre_existing_status,
        )
        return _implementation_failure(
            "work_packet_step_selection_failed",
            mission_id,
            "Failed to select WorkPacket apply-patch step.",
            extra={
                "unit_id": unit["id"],
                "work_packet_id": packet.packet_id,
                "errors": select_res.get("errors", []),
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
            },
            exit_code=1,
        )

    apply_res = work_packets_execution.dispatch_step(packet.packet_id, "apply-patch", play_owner)
    apply_task_id = apply_res.get("editor_task_id")
    apply_result_path = apply_res.get("editor_result_path")
    apply_status = apply_res.get("editor_result_status")

    apply_editor_result_data = _load_json(Path(apply_result_path)) if apply_result_path and Path(apply_result_path).exists() else {}
    apply_result_dict = apply_editor_result_data.get("result", {})
    repo_mutated = bool(apply_result_dict.get("repository_mutations")) or bool(apply_res.get("result_summary", {}).get("repository_mutation_performed"))

    applied: list[dict[str, Any]] = []
    for mut in apply_result_dict.get("repository_mutations", []):
        if isinstance(mut, dict):
            path = mut.get("path")
            before_st = before_by_path.get(path, {})
            target, _ = _resolve_repo_file_path(path)
            after_st = _capture_file_state(target) if target else {}
            applied.append({
                "path": path,
                "operation": mut.get("operation") or "apply_patch",
                "before": before_st,
                "after": after_st,
                "changed": True,
            })

    if apply_status != "completed" or not apply_res.get("ok"):
        apply_errors = [err.get("message") or err.get("code") for err in apply_result_dict.get("errors", [])] or apply_res.get("errors", []) or ["apply_patch_step_failed"]
        fail_status = "patch_application_rejected" if apply_status in {"rejected", "blocked"} else "implementation_write_failed"
        result_payload = {
            "schema_version": MISSION_SCHEMA_VERSION,
            "unit_id": unit["id"],
            "summary": implementation_response.get("summary", ""),
            "model_response_status": model_response.get("status"),
            "file_changes": implementation_response.get("file_changes", []),
            "applied": applied,
            "write_errors": apply_errors,
            "work_packet_id": packet.packet_id,
            "editor_task_ids": [apply_task_id] if apply_task_id else [],
            "work_packet_path": _stable(work_packets_persistence.packet_dir(packet.packet_id)),
            "editor_result_paths": [apply_result_path] if apply_result_path else [],
            "authorization_id": auth.authorization_id,
        }
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status=fail_status,
            error_type=fail_status,
            error_message="; ".join(str(e) for e in apply_errors),
            pre_existing_status=pre_existing_status,
            extra_artifacts={
                "before.json": before_payload,
                "request.json": request_payload,
                "result.json": result_payload,
                "changes.diff": patch_text,
                "rollback.md": _render_unit_rollback(unit, applied, before_by_path, implementation_response.get("rollback_notes", [])),
            },
        )
        return _implementation_failure(
            fail_status,
            mission_id,
            "Patch application failed.",
            extra={
                "unit_id": unit["id"],
                "write_errors": apply_errors,
                "applied": applied,
                "work_packet_id": packet.packet_id,
                "editor_task_ids": [apply_task_id] if apply_task_id else [],
                "work_packet_path": _stable(work_packets_persistence.packet_dir(packet.packet_id)),
                "editor_result_paths": [apply_result_path] if apply_result_path else [],
                "authorization_id": auth.authorization_id,
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
                "source_files_modified": repo_mutated,
            },
            exit_code=1,
        )

    select_v = work_packets_execution.select_step(packet.packet_id, "verify", play_owner)
    verify_res = work_packets_execution.dispatch_step(packet.packet_id, "verify", play_owner)
    verify_task_id = verify_res.get("editor_task_id")
    verify_result_path = verify_res.get("editor_result_path")
    verify_status = verify_res.get("editor_result_status")

    verification_commands = unit.get("verification", [])
    verification_payload = _run_unit_verification(verification_commands)
    _write_unit_json(attempt_dir / "verification.json", verification_payload)
    _write_unit_json(unit_dir / "verification.json", verification_payload)

    verify_passed = (verify_status == "completed") and verification_payload.get("all_passed", True)

    if not verify_passed:
        result_payload = {
            "schema_version": MISSION_SCHEMA_VERSION,
            "unit_id": unit["id"],
            "summary": implementation_response.get("summary", ""),
            "model_response_status": model_response.get("status"),
            "file_changes": implementation_response.get("file_changes", []),
            "applied": applied,
            "work_packet_id": packet.packet_id,
            "editor_task_ids": [apply_task_id, verify_task_id] if verify_task_id else [apply_task_id],
            "work_packet_path": _stable(work_packets_persistence.packet_dir(packet.packet_id)),
            "editor_result_paths": [apply_result_path, verify_result_path] if verify_result_path else [apply_result_path],
            "authorization_id": auth.authorization_id,
        }
        manifest, state_payload = _record_implementation_unit_failure(
            mission_dir,
            mission_id,
            inputs,
            units,
            unit,
            started_at=started_at,
            attempt=attempt,
            failure_status="verification_failed",
            error_type="verification_failed",
            error_message="Unit verification failed.",
            pre_existing_status=pre_existing_status,
            extra_artifacts={
                "before.json": before_payload,
                "request.json": request_payload,
                "result.json": result_payload,
                "changes.diff": patch_text,
                "rollback.md": _render_unit_rollback(unit, applied, before_by_path, implementation_response.get("rollback_notes", [])),
                "verification.json": verification_payload,
            },
        )
        return _implementation_failure(
            "verification_failed",
            mission_id,
            "Unit verification failed.",
            extra={
                "unit_id": unit["id"],
                "verification": verification_payload,
                "work_packet_id": packet.packet_id,
                "editor_task_ids": [apply_task_id, verify_task_id] if verify_task_id else [apply_task_id],
                "work_packet_path": _stable(work_packets_persistence.packet_dir(packet.packet_id)),
                "editor_result_paths": [apply_result_path, verify_result_path] if verify_result_path else [apply_result_path],
                "authorization_id": auth.authorization_id,
                "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
                "next_action": state_payload["next_action"],
                "source_files_modified": True,
            },
            exit_code=1,
        )

    after_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "unit_id": unit["id"],
        "captured_at": _now(),
        "files": [
            _capture_file_state(change["target"])
            for change in validated_changes
        ],
    }
    result_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "unit_id": unit["id"],
        "summary": implementation_response.get("summary", ""),
        "model_response_status": model_response.get("status"),
        "file_changes": [
            {
                "path": change["path"],
                "operation": change["operation"],
                "original_sha256": change.get("original_sha256"),
            }
            for change in validated_changes
        ],
        "applied": applied,
        "write_errors": [],
        "work_packet_id": packet.packet_id,
        "editor_task_ids": [apply_task_id, verify_task_id],
        "work_packet_path": _stable(work_packets_persistence.packet_dir(packet.packet_id)),
        "editor_result_paths": [apply_result_path, verify_result_path],
        "authorization_id": auth.authorization_id,
    }
    rollback_text = _render_unit_rollback(
        unit,
        applied,
        before_by_path,
        implementation_response.get("rollback_notes", []) or unit.get("rollback", []),
    )
    _write_unit_json(attempt_dir / "result.json", result_payload)
    _write_unit_json(unit_dir / "result.json", result_payload)
    _write_unit_json(attempt_dir / "after.json", after_payload)
    _write_unit_json(unit_dir / "after.json", after_payload)
    _write_unit_text(attempt_dir / "changes.diff", patch_text)
    _write_unit_text(unit_dir / "changes.diff", patch_text)
    _write_unit_text(attempt_dir / "rollback.md", rollback_text)
    _write_unit_text(unit_dir / "rollback.md", rollback_text)

    completed_at = _now()
    complete_status = _write_unit_status(
        mission_dir,
        unit["id"],
        "complete",
        started_at=started_at,
        attempt=attempt,
        completed_at=completed_at,
        artifact_dir=attempt_dir,
    )
    _write_unit_json(attempt_dir / "status.json", complete_status)
    manifest = _write_implementation_manifest(
        mission_dir,
        mission_id,
        proposal_path,
        review_path,
        units,
        pre_existing_status=pre_existing_status,
        updated_at=completed_at,
    )
    state_payload = _implementation_state_payload(
        inputs["state"],
        mission_id,
        manifest,
    )
    _atomic_json(_mission_state_path(mission_dir), state_payload)

    changed_files = [item for item in applied if item.get("changed")]
    observation = {
        "command": "mission implement",
        "status": "implementation_unit_complete",
        "mission_id": mission_id,
        "unit_id": unit["id"],
        "changed_files": [item.get("path") for item in changed_files],
        "implementation_complete": manifest.get("implementation_complete"),
        "source_files_modified": bool(changed_files),
        "authority": "approved_implementation_execution",
        "work_packet_id": packet.packet_id,
        "editor_task_ids": [apply_task_id, verify_task_id],
        "authorization_id": auth.authorization_id,
    }
    _append_mission_event(mission_dir, unit["id"].replace("-", ""), observation)
    refresh_pinboard(
        mission=str(inputs["intent"].get("intent") or mission_id),
        last_observation=observation,
        next_action=state_payload["next_action"],
    )
    payload = {
        "ok": True,
        "status": "implementation_unit_complete",
        "mission_id": mission_id,
        "unit_id": unit["id"],
        "attempt": attempt,
        "changed_files": [item.get("path") for item in changed_files],
        "implementation_complete": manifest.get("implementation_complete"),
        "manifest_path": _stable(_mission_implementation_manifest_path(mission_dir)),
        "unit_artifacts": _stable(unit_dir),
        "next_action": state_payload["next_action"],
        "source_files_modified": bool(changed_files),
        "authority": "approved_implementation_execution",
        "work_packet_id": packet.packet_id,
        "editor_task_ids": [apply_task_id, verify_task_id],
        "work_packet_path": _stable(work_packets_persistence.packet_dir(packet.packet_id)),
        "editor_result_paths": [apply_result_path, verify_result_path],
        "authorization_id": auth.authorization_id,
    }
    print(json.dumps(payload, indent=2))
    return 0