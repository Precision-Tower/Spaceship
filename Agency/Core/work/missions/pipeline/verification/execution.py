from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import time
import zlib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Callable
from Agency.Core.runtime.commands import mission_command


@dataclass(frozen=True)
class VerificationExecutionDependencies:
    """Local infrastructure required by post-implementation verification."""
    DASHBOARD_ROOT: Path
    MISSIONS_ROOT: Path
    MISSION_SCHEMA_VERSION: int
    MAX_VERIFICATION_OUTPUT_CHARS: int
    _append_mission_event: Callable[..., Any]
    _atomic_json: Callable[..., Any]
    _atomic_text: Callable[..., Any]
    _capture_file_state: Callable[..., Any]
    _git_status_lines: Callable[..., Any]
    _implementation_execution_order: Callable[..., Any]
    _is_relative_to: Callable[..., Any]
    _load_json: Callable[..., Any]
    _load_operator_notes: Callable[..., Any]
    _load_plan: Callable[..., Any]
    _load_proposal: Callable[..., Any]
    _load_required_mission_json: Callable[..., Any]
    _load_review_decision: Callable[..., Any]
    _mission_implementation_manifest_path: Callable[..., Any]
    _mission_intent_path: Callable[..., Any]
    _mission_proposal_json_path: Callable[..., Any]
    _mission_review_decision_json_path: Callable[..., Any]
    _mission_state_path: Callable[..., Any]
    _mission_unit_dir: Callable[..., Any]
    _normalize_implementation_operation: Callable[..., Any]
    _normalize_implementation_units: Callable[..., Any]
    _now: Callable[..., Any]
    _proposal_operation_map: Callable[..., Any]
    _resolve_mission_dir: Callable[..., Any]
    _resolve_repo_file_path: Callable[..., Any]
    _sha256_bytes: Callable[..., Any]
    _stable: Callable[..., Any]
    _status_path: Callable[..., Any]
    _verification_command_allowed: Callable[..., Any]
    refresh_pinboard: Callable[..., Any]


_BOUND_DEPENDENCIES: VerificationExecutionDependencies | None = None


def bind_dependencies(deps: VerificationExecutionDependencies) -> None:
    """Bind infrastructure used by verification helpers."""
    global _BOUND_DEPENDENCIES
    _BOUND_DEPENDENCIES = deps
    namespace = globals()
    for field in fields(deps):
        namespace[field.name] = getattr(deps, field.name)


def run_mission_verify(
    deps: VerificationExecutionDependencies,
    mission: str,
) -> int:
    bind_dependencies(deps)
    return _run_bound_mission_verify(argparse.Namespace(mission=mission))


def _mission_verification_dir(mission_dir: Path) -> Path:
    return mission_dir / "verification"


def _mission_verification_report_json_path(mission_dir: Path) -> Path:
    return _mission_verification_dir(mission_dir) / "report.json"


def _mission_verification_report_md_path(mission_dir: Path) -> Path:
    return _mission_verification_dir(mission_dir) / "report.md"


def _load_implementation_manifest(mission_dir: Path) -> dict[str, Any]:
    manifest = _load_required_mission_json(_mission_implementation_manifest_path(mission_dir))
    if manifest.get("authority") != "approved_implementation_execution":
        raise ValueError("implementation manifest authority is not approved_implementation_execution")
    return manifest


def _load_verification_inputs(mission_dir: Path) -> dict[str, Any]:
    return {
        "intent": _load_required_mission_json(_mission_intent_path(mission_dir)),
        "state": _load_required_mission_json(_mission_state_path(mission_dir)),
        "plan": _load_plan(mission_dir),
        "proposal": _load_proposal(mission_dir),
        "review": _load_review_decision(mission_dir),
        "implementation": _load_implementation_manifest(mission_dir),
        "operator_notes": _load_operator_notes(mission_dir),
    }


def _load_unit_artifact(
    mission_dir: Path,
    unit_id: str,
    name: str,
) -> tuple[dict[str, Any] | None, str | None]:
    path = _mission_unit_dir(mission_dir, unit_id) / name
    data = _load_json(path)
    if data is None:
        return None, f"missing {name}"
    if "load_error" in data:
        return None, f"unreadable {name}: {data.get('load_error')}"
    return data, None


def _unit_artifact_exists(mission_dir: Path, unit_id: str, name: str) -> bool:
    return (_mission_unit_dir(mission_dir, unit_id) / name).exists()


def _manifest_unit_status(manifest: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for item in manifest.get("units", []):
        if isinstance(item, dict) and item.get("id"):
            statuses[str(item["id"])] = str(item.get("status") or "pending")
    return statuses


def _validate_verification_readiness(
    inputs: dict[str, Any],
    units: list[dict[str, Any]],
) -> tuple[bool, str | None, str | None]:
    review = inputs.get("review", {})
    state = inputs.get("state", {})
    manifest = inputs.get("implementation", {})
    if review.get("decision") != "approved" or review.get("implementation_authorized") is not True:
        return False, "review_required", "review/decision.json does not approve implementation."
    if state.get("implementation_complete") is not True:
        return False, "implementation_incomplete", "state.json does not record implementation completion."
    if manifest.get("implementation_complete") is not True:
        return False, "implementation_incomplete", "implementation/manifest.json is not complete."
    manifest_status = _manifest_unit_status(manifest)
    incomplete = [
        unit["id"] for unit in units
        if manifest_status.get(unit["id"]) != "complete"
    ]
    if incomplete:
        return False, "implementation_incomplete", f"incomplete implementation units: {', '.join(incomplete)}"
    return True, None, None


def _assess_implementation_unit_artifacts(
    mission_dir: Path,
    units: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    manifest_status = _manifest_unit_status(manifest)
    completed: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    artifact_index: dict[str, dict[str, Any]] = {}
    required = [
        "status.json",
        "request.json",
        "before.json",
        "result.json",
        "verification.json",
        "after.json",
        "changes.diff",
        "rollback.md",
    ]
    for unit in units:
        unit_id = unit["id"]
        unit_dir = _mission_unit_dir(mission_dir, unit_id)
        status_data, status_error = _load_unit_artifact(mission_dir, unit_id, "status.json")
        after_data, after_error = _load_unit_artifact(mission_dir, unit_id, "after.json")
        result_data, result_error = _load_unit_artifact(mission_dir, unit_id, "result.json")
        verification_data, verification_error = _load_unit_artifact(mission_dir, unit_id, "verification.json")
        missing = [
            name for name in required
            if not _unit_artifact_exists(mission_dir, unit_id, name)
        ]
        artifact_errors = [
            error for error in (status_error, after_error, result_error, verification_error)
            if error
        ]
        status = str(
            (status_data or {}).get("status")
            or manifest_status.get(unit_id)
            or "pending"
        )
        record = {
            "id": unit_id,
            "manifest_status": manifest_status.get(unit_id, "missing"),
            "status": status,
            "artifact_path": _stable(unit_dir / "status.json"),
            "missing_artifacts": missing,
            "artifact_errors": artifact_errors,
        }
        artifact_index[unit_id] = {
            "status": status_data,
            "after": after_data,
            "result": result_data,
            "verification": verification_data,
        }
        if status == "failed":
            failed.append(record)
            continue
        if status != "complete":
            incomplete.append(record)
            continue
        if missing or artifact_errors:
            incomplete.append(record)
            continue
        if not isinstance(verification_data, dict) or verification_data.get("all_passed") is not True:
            failed.append({
                **record,
                "reason": "unit-local verification artifact did not pass",
            })
            continue
        completed.append(record)
    return {
        "all_units_complete": len(completed) == len(units) and not incomplete and not failed,
        "completed_units": completed,
        "incomplete_units": incomplete,
        "failed_units": failed,
        "artifact_index": artifact_index,
    }


def _result_operation_by_path(result_data: dict[str, Any] | None, unit: dict[str, Any]) -> dict[str, str]:
    operations: dict[str, str] = {}
    if isinstance(result_data, dict):
        for item in result_data.get("applied", []):
            if isinstance(item, dict) and item.get("path"):
                operations[str(item["path"])] = _normalize_implementation_operation(item.get("operation"))
        for item in result_data.get("file_changes", []):
            if isinstance(item, dict) and item.get("path"):
                operations.setdefault(
                    str(item["path"]),
                    _normalize_implementation_operation(item.get("operation")),
                )
    proposal_ops = _proposal_operation_map(unit)
    for path, values in proposal_ops.items():
        if values:
            operations.setdefault(path, sorted(values)[0])
    return operations


def _compare_file_integrity(
    mission_dir: Path,
    units: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    matched: list[dict[str, Any]] = []
    mismatched: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    unexpected_existing: list[dict[str, Any]] = []
    invalid_records: list[dict[str, Any]] = []
    for unit in units:
        unit_id = unit["id"]
        unit_artifacts = artifacts.get("artifact_index", {}).get(unit_id, {})
        after_data = unit_artifacts.get("after")
        result_data = unit_artifacts.get("result")
        if not isinstance(after_data, dict):
            invalid_records.append({
                "unit_id": unit_id,
                "reason": "missing_or_invalid_after_json",
            })
            continue
        operation_by_path = _result_operation_by_path(result_data, unit)
        files = after_data.get("files", [])
        if not isinstance(files, list):
            invalid_records.append({
                "unit_id": unit_id,
                "reason": "after_json_files_not_list",
            })
            continue
        for record in files:
            if not isinstance(record, dict):
                invalid_records.append({
                    "unit_id": unit_id,
                    "reason": "invalid_after_record",
                    "record": str(record)[:200],
                })
                continue
            path = str(record.get("path") or "").strip()
            target, path_error = _resolve_repo_file_path(path)
            if path_error or target is None:
                invalid_records.append({
                    "unit_id": unit_id,
                    "path": path,
                    "reason": path_error or "invalid_after_path",
                })
                continue
            expected_exists = bool(record.get("exists"))
            expected_sha = record.get("sha256")
            expected_size = record.get("size_bytes")
            actual = _capture_file_state(target)
            operation = operation_by_path.get(path, "modify")
            base = {
                "unit_id": unit_id,
                "path": path,
                "operation": operation,
                "expected": {
                    "exists": expected_exists,
                    "sha256": expected_sha,
                    "size_bytes": expected_size,
                },
                "actual": {
                    "exists": actual.get("exists"),
                    "sha256": actual.get("sha256"),
                    "size_bytes": actual.get("size_bytes"),
                },
            }
            if not expected_exists:
                if actual.get("exists"):
                    unexpected_existing.append({
                        **base,
                        "reason": "deleted_file_reappeared" if operation == "delete" else "unexpected_existing_file",
                    })
                else:
                    matched.append({
                        **base,
                        "reason": "expected_absent",
                    })
                continue
            if not actual.get("exists"):
                missing.append({
                    **base,
                    "reason": "missing_expected_file",
                })
                continue
            reasons: list[str] = []
            if expected_sha and actual.get("sha256") != expected_sha:
                reasons.append("hash_mismatch")
            if expected_size is not None and actual.get("size_bytes") != expected_size:
                reasons.append("size_mismatch")
            if reasons:
                mismatched.append({
                    **base,
                    "reason": ",".join(reasons),
                })
            else:
                matched.append({
                    **base,
                    "reason": "matches_recorded_after_state",
                })
    return {
        "all_match_recorded_after_state": not mismatched and not missing and not unexpected_existing and not invalid_records,
        "matched": matched,
        "mismatched": mismatched,
        "missing": missing,
        "unexpected_existing": unexpected_existing,
        "invalid_records": invalid_records,
    }


class VerificationEvidenceError(Exception):
    def __init__(self, status: str, reason: str, errors: list[str] | None = None) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.errors = errors or []


def _mission_verification_evidence_dir(mission_dir: Path) -> Path:
    return _mission_verification_dir(mission_dir) / "evidence"


def _mission_evidence_manifest_path(mission_dir: Path) -> Path:
    return _mission_verification_dir(mission_dir) / "evidence_manifest.json"


def _mission_relative_file_path(mission_dir: Path, path: Path) -> str:
    return path.relative_to(mission_dir).as_posix()


def _normalize_evidence_path(
    mission_dir: Path,
    raw_path: str,
) -> tuple[Path | None, str | None]:
    text = str(raw_path or "").strip().replace("\\", "/")
    if not text:
        return None, "invalid_evidence_path: empty evidence path"
    candidate_path = Path(text)
    if candidate_path.is_absolute() or ".." in candidate_path.parts:
        return None, f"invalid_evidence_path: unsafe evidence path {text}"
    candidate = (mission_dir / candidate_path).resolve()
    mission_root = mission_dir.resolve()
    if not _is_relative_to(candidate, mission_root):
        return None, f"invalid_evidence_path: evidence path escapes mission root {text}"
    if not candidate.exists():
        return None, f"evidence_artifact_missing: {text}"
    if not candidate.is_file():
        return None, f"invalid_evidence_path: evidence path is not a regular file {text}"
    return candidate, None


def _detect_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix == ".md":
        return "text/markdown"
    if suffix in {".diff", ".patch"}:
        return "text/x-diff"
    if suffix in {".txt", ".log"}:
        return "text/plain"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def _hash_evidence_artifact(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "sha256": _sha256_bytes(data),
        "size_bytes": len(data),
    }


def _build_evidence_record(
    mission_dir: Path,
    *,
    kind: str,
    path: str,
    created_at: str,
    producer: str,
    purpose: str,
    required: bool = True,
    media_type: str | None = None,
    derived_from: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_path = str(path or "").strip().replace("\\", "/")
    target, error = _normalize_evidence_path(mission_dir, normalized_path)
    if error or target is None:
        status = str(error or "invalid_evidence_path").split(":", 1)[0]
        raise VerificationEvidenceError(status, error or "invalid evidence path", [error or "invalid evidence path"])
    artifact = _hash_evidence_artifact(target)
    return {
        "kind": str(kind or "artifact").strip() or "artifact",
        "required": bool(required),
        "path": normalized_path,
        "sha256": artifact["sha256"],
        "size_bytes": artifact["size_bytes"],
        "created_at": created_at,
        "producer": str(producer or "mission.verify"),
        "purpose": str(purpose or "Verification evidence artifact."),
        "media_type": media_type or _detect_media_type(target),
        "derived_from": list(derived_from or []),
        "metadata": dict(metadata or {}),
    }


MAX_VISUAL_ARTIFACT_BYTES = 5_000_000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_GODOT_TIMEOUT_MS = 60000
DEFAULT_GODOT_TIMEOUT_MS = 15000
MAX_GODOT_DELAY_MS = 5000
MAX_GODOT_FRAMES = 120
DEFAULT_GODOT_FRAMES = 3
MAX_GODOT_OUTPUT_CHARS = 65536
MAX_SCENE_TREE_BYTES = 1_000_000
MAX_SCENE_TREE_DEPTH = 12
MAX_SCENE_TREE_NODES = 500


def _normalize_capture_id(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    return text.strip(".-")


def _normalize_visual_output_name(raw: Any) -> tuple[str | None, str | None]:
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return None, "invalid_visual_output_path: output_name is required"
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
        return None, f"invalid_visual_output_path: unsafe visual output {text}"
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", path.name).strip(".-")
    if not name:
        return None, "invalid_visual_output_path: output_name normalized to empty"
    if Path(name).suffix.lower() != ".png":
        return None, f"invalid_visual_output_path: visual output must end with .png: {text}"
    return name, None


def _bounded_int(value: Any, default: int, *, minimum: int = 0, maximum: int = 60000) -> int:
    try:
        number = int(value)
    except Exception:
        number = default
    return max(minimum, min(maximum, number))


def _criterion_ids(criteria: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("id") or "")
        for item in criteria
        if isinstance(item, dict) and item.get("id")
    }


def _normalize_visual_capture_request(
    raw: dict[str, Any],
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    capture_id = _normalize_capture_id(raw.get("capture_id") or raw.get("id"))
    if not capture_id:
        raise VerificationEvidenceError(
            "invalid_visual_capture_request",
            "visual capture request missing capture_id",
        )
    output_name, output_error = _normalize_visual_output_name(
        raw.get("output_name") or raw.get("path") or f"{capture_id}.png"
    )
    if output_error or output_name is None:
        raise VerificationEvidenceError(
            "invalid_visual_output_path",
            output_error or "invalid visual output path",
            [output_error or "invalid visual output path"],
        )
    criterion_id = str(raw.get("criterion_id") or "").strip()
    if criterion_id not in _criterion_ids(criteria):
        raise VerificationEvidenceError(
            "unresolved_visual_criterion",
            f"visual capture {capture_id} references unknown criterion {criterion_id}",
            [f"unresolved_visual_criterion: {criterion_id}"],
        )
    target = raw.get("target") if isinstance(raw.get("target"), dict) else {}
    timing = raw.get("timing") if isinstance(raw.get("timing"), dict) else {}
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return {
        "capture_id": capture_id,
        "required": bool(raw.get("required", True)),
        "purpose": str(raw.get("purpose") or f"Capture visual evidence for {criterion_id}.").strip(),
        "criterion_id": criterion_id,
        "backend": str(raw.get("backend") or "mock").strip().lower(),
        "output_name": output_name,
        "target": target,
        "timing": {
            "delay_ms": _bounded_int(timing.get("delay_ms"), 0, maximum=MAX_GODOT_DELAY_MS),
            "timeout_ms": _bounded_int(
                timing.get("timeout_ms"),
                5000,
                minimum=100,
                maximum=MAX_GODOT_TIMEOUT_MS,
            ),
            "frames": _bounded_int(timing.get("frames"), DEFAULT_GODOT_FRAMES, minimum=1, maximum=MAX_GODOT_FRAMES),
        },
        "metadata": metadata,
    }


def _collect_visual_capture_requests(
    proposal: dict[str, Any],
    criteria: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_checks = proposal.get("visual_checks", [])
    if not raw_checks:
        return []
    if not isinstance(raw_checks, list):
        raise VerificationEvidenceError(
            "invalid_visual_capture_request",
            "proposal visual_checks must be a list",
        )
    requests: list[dict[str, Any]] = []
    capture_ids: set[str] = set()
    output_names: set[str] = set()
    for raw in raw_checks:
        if not isinstance(raw, dict):
            raise VerificationEvidenceError(
                "invalid_visual_capture_request",
                "visual capture request must be an object",
            )
        request = _normalize_visual_capture_request(raw, criteria)
        if request["capture_id"] in capture_ids:
            raise VerificationEvidenceError(
                "duplicate_capture_id",
                f"duplicate visual capture_id {request['capture_id']}",
                [f"duplicate_capture_id: {request['capture_id']}"],
            )
        if request["output_name"] in output_names:
            raise VerificationEvidenceError(
                "duplicate_visual_output",
                f"duplicate visual output {request['output_name']}",
                [f"duplicate_visual_output: {request['output_name']}"],
            )
        capture_ids.add(request["capture_id"])
        output_names.add(request["output_name"])
        requests.append(request)
    return requests


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def _deterministic_png_bytes(width: int = 16, height: int = 9) -> bytes:
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend([
                (x * 17) % 256,
                (y * 29) % 256,
                ((x + y) * 11) % 256,
            ])
        rows.append(bytes(row))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"".join([
        PNG_SIGNATURE,
        _png_chunk(b"IHDR", ihdr),
        _png_chunk(b"IDAT", zlib.compress(b"".join(rows), level=9)),
        _png_chunk(b"IEND", b""),
    ])


def _parse_png_dimensions(data: bytes) -> tuple[int | None, int | None, str | None]:
    if len(data) < 33 or not data.startswith(PNG_SIGNATURE):
        return None, None, "invalid_png_artifact: invalid PNG signature"
    ihdr_length = struct.unpack(">I", data[8:12])[0]
    chunk_type = data[12:16]
    if ihdr_length != 13 or chunk_type != b"IHDR":
        return None, None, "invalid_png_artifact: first PNG chunk is not IHDR"
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        return None, None, "invalid_png_artifact: PNG dimensions must be positive"
    return width, height, None


def _validate_png_artifact(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if path.suffix.lower() != ".png":
        return None, "invalid_png_artifact: visual artifact must end with .png"
    if not path.exists() or not path.is_file():
        return None, "invalid_png_artifact: visual artifact does not exist"
    size = path.stat().st_size
    if size <= 0:
        return None, "invalid_png_artifact: visual artifact is empty"
    if size > MAX_VISUAL_ARTIFACT_BYTES:
        return None, "visual_artifact_too_large: visual artifact exceeds byte limit"
    data = path.read_bytes()
    width, height, error = _parse_png_dimensions(data)
    if error:
        return None, error
    return {
        "width": width,
        "height": height,
        "size_bytes": size,
        "sha256": _sha256_bytes(data),
    }, None


def _visual_capture_result_base(request: dict[str, Any], status: str, *, error: str | None = None) -> dict[str, Any]:
    now = _now()
    return {
        "capture_id": request.get("capture_id"),
        "criterion_id": request.get("criterion_id"),
        "required": bool(request.get("required", True)),
        "backend": request.get("backend"),
        "status": status,
        "artifact_path": None,
        "evidence_id": None,
        "media_type": "image/png",
        "width": None,
        "height": None,
        "started_at": now,
        "completed_at": _now(),
        "stdout": "",
        "stderr": error or "",
        "error": error,
        "purpose": request.get("purpose"),
        "metadata": dict(request.get("metadata") or {}),
    }


def _capture_with_mock_backend(
    request: dict[str, Any],
    mission_dir: Path,
    evidence_dir: Path,
) -> dict[str, Any]:
    mode = str(
        request.get("metadata", {}).get("mock_mode")
        or os.environ.get("AGENCY_MOCK_SCREENSHOT_MODE")
        or "success"
    ).strip().lower()
    if mode == "unavailable":
        return _visual_capture_result_base(
            request,
            "unavailable",
            error="visual_backend_unavailable: mock backend requested unavailable mode",
        )
    if mode == "timeout":
        return _visual_capture_result_base(
            request,
            "timed_out",
            error="visual_capture_timed_out: mock backend requested timeout mode",
        )
    output_path = evidence_dir / str(request["output_name"])
    if output_path.exists():
        return _visual_capture_result_base(
            request,
            "failed",
            error=f"duplicate_visual_output: {request['output_name']}",
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "invalid":
        _atomic_text(output_path, "not a png\n")
    else:
        tmp = output_path.with_suffix(output_path.suffix + ".tmp")
        tmp.write_bytes(_deterministic_png_bytes())
        tmp.replace(output_path)
    result = _visual_capture_result_base(request, "succeeded")
    result["artifact_path"] = _mission_relative_file_path(mission_dir, output_path)
    result["width"] = request.get("metadata", {}).get("claimed_width")
    result["height"] = request.get("metadata", {}).get("claimed_height")
    return result


def _visual_regular_file(path: Path) -> bool:
    try:
        return path.exists() and path.is_file()
    except OSError:
        return False


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        pass


def _truncate_visual_output(text: Any, limit: int = MAX_GODOT_OUTPUT_CHARS) -> tuple[str, bool]:
    value = "" if text is None else str(text)
    if len(value) <= limit:
        return value, False
    return value[-limit:], True


def _redact_visual_output(text: Any, replacements: dict[Path, str]) -> str:
    value = "" if text is None else str(text)
    pairs: list[tuple[str, str]] = []
    for path, token in replacements.items():
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        for candidate in {str(path), path.as_posix(), str(resolved), resolved.as_posix()}:
            if candidate:
                pairs.append((candidate, token))
    for needle, token in sorted(set(pairs), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(needle, token)
    return value


def _safe_godot_request_metadata(request: dict[str, Any]) -> dict[str, Any]:
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in {"executable", "project_path", "scene_path"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
    return safe


def _godot_error_result(
    request: dict[str, Any],
    status: str,
    error: str,
    *,
    stdout: str = "",
    stderr: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = _visual_capture_result_base(request, status, error=error)
    result["stdout"] = stdout
    result["stderr"] = stderr or error
    result["metadata"] = _safe_godot_request_metadata(request)
    result["metadata"].update(metadata or {})
    return result


def _validate_godot_project_path(request: dict[str, Any]) -> tuple[Path | None, str | None]:
    target = request.get("target") if isinstance(request.get("target"), dict) else {}
    raw = target.get("project_path") or request.get("metadata", {}).get("project_path")
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return None, "invalid_godot_project_path: project_path is required"
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        return None, f"invalid_godot_project_path: unsafe project_path {text}"
    candidate = (DASHBOARD_ROOT / path).resolve()
    if not _is_relative_to(candidate, DASHBOARD_ROOT.resolve()):
        return None, f"invalid_godot_project_path: project_path escapes repository root {text}"
    if not candidate.exists():
        return None, f"godot_project_not_found: {text}"
    if not candidate.is_dir():
        return None, f"invalid_godot_project_path: project_path is not a directory {text}"
    marker = (candidate / "project.godot").resolve()
    if not _is_relative_to(marker, candidate) or not marker.is_file():
        return None, f"godot_project_marker_missing: {text}/project.godot"
    return candidate, None


def _validate_godot_scene_path(request: dict[str, Any], project_path: Path) -> tuple[str | None, str | None]:
    target = request.get("target") if isinstance(request.get("target"), dict) else {}
    raw = target.get("scene_path") or request.get("metadata", {}).get("scene_path")
    if raw in (None, ""):
        return None, None
    text = str(raw or "").strip().replace("\\", "/")
    if not text.startswith("res://"):
        return None, f"invalid_godot_scene_path: scene_path must start with res://: {text}"
    if any(token in text for token in ("\0", "\n", "\r", ";", "&", "|", "`", "$", "<", ">")):
        return None, f"invalid_godot_scene_path: scene_path contains unsafe syntax {text}"
    resource = text.removeprefix("res://")
    parts = resource.split("/")
    if not resource or any(part in {"", ".", ".."} for part in parts):
        return None, f"invalid_godot_scene_path: unsafe scene_path {text}"
    if Path(parts[-1]).suffix.lower() not in {".tscn", ".scn"}:
        return None, f"invalid_godot_scene_path: scene_path must end with .tscn or .scn: {text}"
    scene_file = (project_path / Path(*parts)).resolve()
    if not _is_relative_to(scene_file, project_path.resolve()):
        return None, f"invalid_godot_scene_path: scene_path escapes project {text}"
    if not scene_file.is_file():
        return None, f"invalid_godot_scene_path: scene file does not exist {text}"
    return text, None


def _resolve_executable_candidate(raw: Any) -> tuple[str | None, str | None]:
    text = str(raw or "").strip()
    if not text:
        return None, "godot_executable_not_found: empty executable"
    if any(token in text for token in ("\0", "\n", "\r", ";", "&", "|", "`", "$", "<", ">")):
        return None, f"godot_executable_invalid: unsafe executable value {text}"
    path_like = Path(text)
    if path_like.is_absolute() or "/" in text or "\\" in text:
        candidate = path_like.expanduser()
        if not candidate.exists() or not candidate.is_file():
            return None, f"godot_executable_invalid: executable is not a file {Path(text).name or text}"
        if os.name != "nt" and not os.access(candidate, os.X_OK):
            return None, f"godot_executable_invalid: executable is not executable {candidate.name}"
        return str(candidate), None
    resolved = shutil.which(text)
    if not resolved:
        return None, f"godot_executable_not_found: {text}"
    return resolved, None


def _find_godot_executable(request: dict[str, Any]) -> tuple[str | None, str | None]:
    target = request.get("target") if isinstance(request.get("target"), dict) else {}
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    for raw in (
        metadata.get("executable"),
        target.get("executable"),
        os.environ.get("AGENCY_GODOT_EXECUTABLE"),
    ):
        if raw:
            return _resolve_executable_candidate(raw)
    for name in ("godot", "godot4"):
        resolved = shutil.which(name)
        if resolved:
            return resolved, None
    return None, "godot_executable_not_found: no godot executable found on PATH"


def _godot_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _godot_capture_script() -> str:
    return r'''
extends SceneTree

var request = {}

func _initialize():
    call_deferred("_run_capture")

func _arg_after(args, flag):
    var idx = args.find(flag)
    if idx < 0 or idx + 1 >= args.size():
        return ""
    return args[idx + 1]

func _node_snapshot(node, depth, max_depth, counter):
    counter["count"] += 1
    var children = []
    if depth < max_depth:
        for child in node.get_children():
            if counter["count"] >= int(request.get("max_scene_tree_nodes", 500)):
                break
            children.append(_node_snapshot(child, depth + 1, max_depth, counter))
    return {
        "name": str(node.name),
        "type": node.get_class(),
        "path": str(node.get_path()),
        "visible": node is CanvasItem and node.visible,
        "process_mode": int(node.process_mode),
        "child_count": node.get_child_count(),
        "children": children,
    }

func _write_json(path, payload):
    var file = FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(payload))
    file.close()
    return true

func _fail(message):
    printerr(message)
    quit(1)

func _run_capture():
    var args = OS.get_cmdline_args()
    var request_path = _arg_after(args, "--lo-capture-request")
    if request_path == "":
        _fail("missing --lo-capture-request")
        return
    var text = FileAccess.get_file_as_string(request_path)
    request = JSON.parse_string(text)
    if typeof(request) != TYPE_DICTIONARY:
        _fail("invalid capture request JSON")
        return
    var scene_path = str(request.get("scene_path", ""))
    if scene_path != "":
        var packed = load(scene_path)
        if packed == null:
            _fail("godot_scene_load_failed: " + scene_path)
            return
        var instance = packed.instantiate()
        root.add_child(instance)
    var frames = int(request.get("frames", 3))
    for i in range(max(frames, 1)):
        await process_frame
    var delay_ms = int(request.get("delay_ms", 0))
    if delay_ms > 0:
        await create_timer(float(delay_ms) / 1000.0).timeout
    var image = root.get_texture().get_image()
    var output_path = str(request.get("output_path", ""))
    if output_path == "":
        _fail("missing output path")
        return
    var save_error = image.save_png(output_path)
    if save_error != OK:
        _fail("godot_capture_failed: save_png returned " + str(save_error))
        return
    if bool(request.get("capture_scene_tree", false)):
        var tree_path = str(request.get("scene_tree_path", ""))
        if tree_path != "":
            var counter = {"count": 0}
            var payload = {
                "schema_version": 1,
                "captured_at": Time.get_datetime_string_from_system(true),
                "root": _node_snapshot(root, 0, int(request.get("max_scene_tree_depth", 12)), counter),
                "node_count": counter["count"],
                "max_depth": int(request.get("max_scene_tree_depth", 12)),
            }
            if not _write_json(tree_path, payload):
                _fail("godot_scene_tree_capture_failed: could not write scene tree")
                return
    print("AGENCY_GODOT_CAPTURE_COMPLETE")
    quit(0)
'''


def _write_godot_capture_harness(
    mission_dir: Path,
    request: dict[str, Any],
    project_path: Path,
    output_path: Path,
    scene_tree_path: Path | None,
    scene_path: str | None,
) -> tuple[Path, Path, Path]:
    harness_dir = mission_dir / "runtime" / "godot_capture" / str(request["capture_id"])
    if harness_dir.exists():
        shutil.rmtree(harness_dir)
    harness_dir.mkdir(parents=True, exist_ok=True)
    script_path = harness_dir / "capture.gd"
    request_path = harness_dir / "request.json"
    script_path.write_text(_godot_capture_script(), encoding="utf-8")
    timing = request.get("timing", {}) if isinstance(request.get("timing"), dict) else {}
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    request_payload = {
        "capture_id": request.get("capture_id"),
        "project_path": str(project_path),
        "scene_path": scene_path or "",
        "output_path": str(output_path),
        "scene_tree_path": str(scene_tree_path) if scene_tree_path else "",
        "capture_scene_tree": _godot_bool(metadata.get("capture_scene_tree"), False),
        "frames": _bounded_int(timing.get("frames"), DEFAULT_GODOT_FRAMES, minimum=1, maximum=MAX_GODOT_FRAMES),
        "delay_ms": _bounded_int(timing.get("delay_ms"), 0, maximum=MAX_GODOT_DELAY_MS),
        "max_scene_tree_depth": MAX_SCENE_TREE_DEPTH,
        "max_scene_tree_nodes": MAX_SCENE_TREE_NODES,
        "metadata": metadata,
    }
    _atomic_json(request_path, request_payload)
    return harness_dir, script_path, request_path


def _build_godot_command(
    executable: str,
    request: dict[str, Any],
    project_path: Path,
    script_path: Path,
    request_path: Path,
) -> list[str]:
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    argv = [executable]
    if _godot_bool(metadata.get("headless"), False):
        argv.append("--headless")
    width = _bounded_int(metadata.get("window_width"), 0, minimum=0, maximum=7680)
    height = _bounded_int(metadata.get("window_height"), 0, minimum=0, maximum=4320)
    if width > 0 and height > 0:
        argv.extend(["--resolution", f"{width}x{height}"])
    argv.extend([
        "--path",
        str(project_path),
        "--script",
        str(script_path),
        "--lo-capture-request",
        str(request_path),
    ])
    return argv


def _godot_process_environment() -> dict[str, str]:
    allowed = {
        "PATH",
        "HOME",
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "XDG_RUNTIME_DIR",
        "LANG",
        "LC_ALL",
        "TERM",
    }
    return {
        key: value
        for key, value in os.environ.items()
        if key in allowed and value is not None
    }


def _terminate_process_tree(proc: subprocess.Popen[str]) -> str | None:
    if proc.poll() is not None:
        return None
    try:
        if os.name != "nt":
            os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=2)
            return None
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait(timeout=2)
            return None
    except Exception as exc:
        try:
            proc.kill()
        except Exception:
            pass
        return f"godot_process_cleanup_failed: {type(exc).__name__}: {exc}"


def _validate_scene_tree_node(node: Any, *, depth: int = 0) -> tuple[int, int, str | None]:
    if not isinstance(node, dict):
        return 0, depth, "godot_scene_tree_capture_failed: scene tree node is not an object"
    if depth > MAX_SCENE_TREE_DEPTH:
        return 0, depth, "godot_scene_tree_capture_failed: scene tree exceeds maximum depth"
    children = node.get("children", [])
    if not isinstance(children, list):
        return 0, depth, "godot_scene_tree_capture_failed: scene tree children must be a list"
    count = 1
    max_depth = depth
    for child in children:
        child_count, child_depth, error = _validate_scene_tree_node(child, depth=depth + 1)
        if error:
            return count, max(max_depth, child_depth), error
        count += child_count
        max_depth = max(max_depth, child_depth)
        if count > MAX_SCENE_TREE_NODES:
            return count, max_depth, "godot_scene_tree_capture_failed: scene tree exceeds maximum node count"
    return count, max_depth, None


def _validate_scene_tree_artifact(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if path.suffix.lower() != ".json":
        return None, "godot_scene_tree_capture_failed: scene tree artifact must be JSON"
    if not path.exists() or not path.is_file():
        return None, "godot_scene_tree_capture_failed: scene tree artifact missing"
    size = path.stat().st_size
    if size <= 0:
        return None, "godot_scene_tree_capture_failed: scene tree artifact is empty"
    if size > MAX_SCENE_TREE_BYTES:
        return None, "godot_scene_tree_capture_failed: scene tree artifact exceeds byte limit"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"godot_scene_tree_capture_failed: invalid scene tree JSON: {exc}"
    if not isinstance(payload, dict) or not isinstance(payload.get("root"), dict):
        return None, "godot_scene_tree_capture_failed: scene tree JSON missing root object"
    node_count, max_depth, error = _validate_scene_tree_node(payload["root"])
    if error:
        return None, error
    return {
        "node_count": int(payload.get("node_count") or node_count),
        "max_depth": int(payload.get("max_depth") or max_depth),
        "size_bytes": size,
        "sha256": _sha256_bytes(path.read_bytes()),
    }, None


def _parse_godot_version(stdout: str, stderr: str) -> str | None:
    match = re.search(r"Godot(?: Engine)?\s+v?([0-9][^\s]*)", f"{stdout}\n{stderr}")
    return match.group(1) if match else None


def _capture_with_godot_backend(
    request: dict[str, Any],
    mission_dir: Path,
    evidence_dir: Path,
) -> dict[str, Any]:
    started_at = _now()
    project_path, project_error = _validate_godot_project_path(request)
    if project_error or project_path is None:
        return _godot_error_result(request, "failed", project_error or "invalid_godot_project_path")
    scene_path, scene_error = _validate_godot_scene_path(request, project_path)
    if scene_error:
        return _godot_error_result(request, "failed", scene_error)
    executable, executable_error = _find_godot_executable(request)
    if executable_error or executable is None:
        return _godot_error_result(
            request,
            "unavailable",
            executable_error or "godot_executable_not_found: no executable",
        )

    output_path = evidence_dir / str(request["output_name"])
    if output_path.exists():
        return _godot_error_result(
            request,
            "failed",
            f"duplicate_visual_output: {request['output_name']}",
        )
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    capture_scene_tree = _godot_bool(metadata.get("capture_scene_tree"), False)
    scene_tree_required = _godot_bool(metadata.get("scene_tree_required"), False)
    scene_tree_path = (
        evidence_dir / f"{Path(str(request['output_name'])).stem}.scene-tree.json"
        if capture_scene_tree
        else None
    )
    if scene_tree_path and scene_tree_path.exists():
        return _godot_error_result(
            request,
            "failed",
            f"duplicate_visual_output: {scene_tree_path.name}",
        )

    harness_dir: Path | None = None
    stdout = ""
    stderr = ""
    stdout_truncated = False
    stderr_truncated = False
    cleanup_error = None
    exit_code: int | None = None
    timed_out = False
    try:
        harness_dir, script_path, request_path = _write_godot_capture_harness(
            mission_dir,
            request,
            project_path,
            output_path,
            scene_tree_path,
            scene_path,
        )
        argv = _build_godot_command(executable, request, project_path, script_path, request_path)
        try:
            proc = subprocess.Popen(
                argv,
                cwd=project_path,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=_godot_process_environment(),
                start_new_session=os.name != "nt",
            )
        except FileNotFoundError:
            return _godot_error_result(
                request,
                "unavailable",
                "godot_executable_not_found: executable could not be launched",
            )
        except Exception as exc:
            return _godot_error_result(
                request,
                "failed",
                f"godot_launch_failed: {type(exc).__name__}: {exc}",
            )
        timeout_ms = _bounded_int(
            request.get("timing", {}).get("timeout_ms"),
            DEFAULT_GODOT_TIMEOUT_MS,
            minimum=100,
            maximum=MAX_GODOT_TIMEOUT_MS,
        )
        try:
            raw_stdout, raw_stderr = proc.communicate(timeout=timeout_ms / 1000.0)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            cleanup_error = _terminate_process_tree(proc)
            raw_stdout = exc.stdout or ""
            raw_stderr = exc.stderr or ""
            exit_code = proc.poll()
        replacements = {
            DASHBOARD_ROOT: "<repo>",
            mission_dir: "<mission>",
            project_path: "<godot-project>",
            output_path: "<visual-output>",
            Path(executable): f"<{Path(executable).name}>",
        }
        if harness_dir is not None:
            replacements[harness_dir] = "<godot-capture-harness>"
        if scene_tree_path is not None:
            replacements[scene_tree_path] = "<scene-tree-output>"
        stdout, stdout_truncated = _truncate_visual_output(_redact_visual_output(raw_stdout, replacements))
        stderr, stderr_truncated = _truncate_visual_output(_redact_visual_output(raw_stderr, replacements))
        base_metadata = {
            "godot_version": _parse_godot_version(stdout, stderr),
            "project_path": str(request.get("target", {}).get("project_path") or ""),
            "scene_path": scene_path,
            "execution_mode": "headless" if _godot_bool(metadata.get("headless"), False) else "windowed",
            "exit_code": exit_code,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "display_available": bool(os.environ.get("DISPLAY")),
            "wayland_available": bool(os.environ.get("WAYLAND_DISPLAY")),
            "executable_name": Path(executable).name,
            "capture_scene_tree": capture_scene_tree,
            "scene_tree_required": scene_tree_required,
        }
        if cleanup_error:
            base_metadata["process_cleanup_error"] = cleanup_error
        if timed_out:
            _safe_unlink(output_path)
            if scene_tree_path:
                _safe_unlink(scene_tree_path)
            return _godot_error_result(
                request,
                "timed_out",
                "godot_capture_timed_out: Godot capture exceeded timeout",
                stdout=stdout,
                stderr=stderr or "godot_capture_timed_out: Godot capture exceeded timeout",
                metadata=base_metadata,
            )
        if exit_code != 0:
            _safe_unlink(output_path)
            if scene_tree_path:
                _safe_unlink(scene_tree_path)
            return _godot_error_result(
                request,
                "failed",
                "godot_capture_failed: Godot exited with nonzero status",
                stdout=stdout,
                stderr=stderr or "godot_capture_failed: Godot exited with nonzero status",
                metadata=base_metadata,
            )
        png, png_error = _validate_png_artifact(output_path)
        if png_error or png is None:
            _safe_unlink(output_path)
            if scene_tree_path:
                _safe_unlink(scene_tree_path)
            return _godot_error_result(
                request,
                "invalid_output",
                f"godot_capture_invalid_output: {png_error or 'missing PNG'}",
                stdout=stdout,
                stderr=stderr or png_error or "missing PNG",
                metadata=base_metadata,
            )
        scene_tree_metadata: dict[str, Any] = {}
        if capture_scene_tree and scene_tree_path is not None:
            tree, tree_error = _validate_scene_tree_artifact(scene_tree_path)
            if tree_error or tree is None:
                _safe_unlink(scene_tree_path)
                if scene_tree_required:
                    _safe_unlink(output_path)
                    return _godot_error_result(
                        request,
                        "invalid_output",
                        tree_error or "godot_scene_tree_capture_failed",
                        stdout=stdout,
                        stderr=stderr or tree_error or "godot_scene_tree_capture_failed",
                        metadata=base_metadata,
                    )
                scene_tree_metadata["scene_tree_error"] = tree_error or "godot_scene_tree_capture_failed"
            else:
                scene_tree_metadata.update({
                    "scene_tree_path": _mission_relative_file_path(mission_dir, scene_tree_path),
                    "scene_tree_node_count": tree["node_count"],
                    "scene_tree_max_depth": tree["max_depth"],
                })
        result = _visual_capture_result_base(request, "succeeded")
        result.update({
            "artifact_path": _mission_relative_file_path(mission_dir, output_path),
            "width": png["width"],
            "height": png["height"],
            "stdout": stdout,
            "stderr": stderr,
            "started_at": started_at,
            "completed_at": _now(),
            "metadata": {
                **_safe_godot_request_metadata(request),
                **base_metadata,
                **scene_tree_metadata,
            },
        })
        return result
    finally:
        if harness_dir is not None:
            try:
                shutil.rmtree(harness_dir)
            except OSError:
                pass


def _execute_visual_capture(
    request: dict[str, Any],
    mission_dir: Path,
    evidence_dir: Path,
) -> dict[str, Any]:
    backend = str(request.get("backend") or "").strip().lower()
    if backend in {"mock", "deterministic_png"}:
        try:
            result = _capture_with_mock_backend(request, mission_dir, evidence_dir)
        except Exception as exc:
            result = _visual_capture_result_base(
                request,
                "failed",
                error=f"visual_capture_write_failed: {type(exc).__name__}: {exc}",
            )
    elif backend == "godot":
        try:
            result = _capture_with_godot_backend(request, mission_dir, evidence_dir)
        except Exception as exc:
            result = _visual_capture_result_base(
                request,
                "failed",
                error=f"godot_capture_failed: {type(exc).__name__}: {exc}",
            )
    elif backend in {"desktop", "playwright"}:
        result = _visual_capture_result_base(
            request,
            "unavailable",
            error=f"visual_backend_unavailable: backend {backend} is not implemented",
        )
    else:
        result = _visual_capture_result_base(
            request,
            "unavailable",
            error=f"visual_backend_unavailable: backend {backend} is not allowlisted",
        )
    return _validate_visual_capture_result(result, mission_dir)


def _validate_visual_capture_result(
    result: dict[str, Any],
    mission_dir: Path,
) -> dict[str, Any]:
    status = str(result.get("status") or "")
    if status != "succeeded":
        return result
    artifact_path = str(result.get("artifact_path") or "")
    target, path_error = _normalize_evidence_path(mission_dir, artifact_path)
    if path_error or target is None:
        result["status"] = "invalid_output"
        result["error"] = path_error or "invalid_visual_output_path"
        result["stderr"] = result["error"]
        result["artifact_path"] = artifact_path or None
        return result
    png, png_error = _validate_png_artifact(target)
    if png_error or png is None:
        result["status"] = "invalid_output"
        result["error"] = png_error or "invalid_png_artifact"
        result["stderr"] = result["error"]
        return result
    result["width"] = png["width"]
    result["height"] = png["height"]
    result["media_type"] = "image/png"
    result["error"] = None
    return result


def _execute_visual_captures(
    requests: list[dict[str, Any]],
    mission_dir: Path,
) -> dict[str, Any]:
    evidence_dir = _mission_verification_evidence_dir(mission_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    captures = [
        _execute_visual_capture(request, mission_dir, evidence_dir)
        for request in requests
    ]
    return {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": mission_dir.name,
        "created_at": _now(),
        "captures": captures,
    }


def _assign_evidence_ids(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assigned: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        assigned.append({
            "id": f"evidence-{index:04d}",
            **record,
        })
    return assigned


def _collect_verification_evidence(
    mission_dir: Path,
    proposal: dict[str, Any],
    units: list[dict[str, Any]],
    implementation_assessment: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    created_at = str(report.get("created_at") or _now())
    records: list[dict[str, Any]] = []

    def add(
        kind: str,
        relative_path: str,
        purpose: str,
        *,
        required: bool = True,
        derived_from: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        target, _error = _normalize_evidence_path(mission_dir, relative_path)
        if target is None:
            return
        records.append(_build_evidence_record(
            mission_dir,
            kind=kind,
            path=relative_path,
            created_at=created_at,
            producer="mission.verify",
            purpose=purpose,
            required=required,
            derived_from=derived_from,
            metadata=metadata,
        ))

    add(
        "command_output",
        "verification/commands.json",
        "Prove targeted verification commands were executed or explicitly recorded.",
    )
    add(
        "file_integrity",
        "verification/file_checks.json",
        "Prove actual files were compared against recorded post-change state.",
    )
    add(
        "change_inventory",
        "verification/unexpected_changes.json",
        "Prove repository status was checked for unexpected changes.",
    )

    ordered_units = _implementation_execution_order(proposal, units)
    for unit in ordered_units:
        unit_id = unit["id"]
        diff_path = _mission_unit_dir(mission_dir, unit_id) / "changes.diff"
        if diff_path.exists() and diff_path.is_file():
            add(
                "source_diff",
                _mission_relative_file_path(mission_dir, diff_path),
                f"Record the actual unified diff generated for implementation unit {unit_id}.",
                metadata={"unit_id": unit_id},
            )
    for unit in ordered_units:
        unit_id = unit["id"]
        verification_path = _mission_unit_dir(mission_dir, unit_id) / "verification.json"
        if verification_path.exists() and verification_path.is_file():
            add(
                "unit_verification",
                _mission_relative_file_path(mission_dir, verification_path),
                f"Record unit-local verification results for implementation unit {unit_id}.",
                metadata={"unit_id": unit_id},
            )

    visual_captures = report.get("visual_captures", {})
    captures = visual_captures.get("captures", []) if isinstance(visual_captures, dict) else []
    if isinstance(captures, list):
        for capture in captures:
            if not isinstance(capture, dict):
                continue
            if capture.get("status") != "succeeded" or not capture.get("artifact_path"):
                continue
            artifact_path = str(capture.get("artifact_path"))
            target, _error = _normalize_evidence_path(mission_dir, artifact_path)
            if target is None:
                continue
            image_evidence_id = f"evidence-{len(records) + 1:04d}"
            metadata = capture.get("metadata", {}) if isinstance(capture.get("metadata"), dict) else {}
            records.append(_build_evidence_record(
                mission_dir,
                kind="image",
                path=artifact_path,
                created_at=created_at,
                producer=f"visual.capture.{capture.get('backend') or 'unknown'}",
                purpose=str(capture.get("purpose") or "Visual verification evidence."),
                required=bool(capture.get("required", True)),
                media_type="image/png",
                metadata={
                    "capture_id": capture.get("capture_id"),
                    "criterion_id": capture.get("criterion_id"),
                    "backend": capture.get("backend"),
                    "width": capture.get("width"),
                    "height": capture.get("height"),
                    "capture_status": capture.get("status"),
                    "godot_version": metadata.get("godot_version"),
                    "execution_mode": metadata.get("execution_mode"),
                },
            ))
            scene_tree_path = str(metadata.get("scene_tree_path") or "")
            if scene_tree_path:
                scene_target, _scene_error = _normalize_evidence_path(mission_dir, scene_tree_path)
                if scene_target is None:
                    continue
                records.append(_build_evidence_record(
                    mission_dir,
                    kind="ui_tree",
                    path=scene_tree_path,
                    created_at=created_at,
                    producer=f"visual.capture.{capture.get('backend') or 'unknown'}",
                    purpose="Record the rendered Godot scene structure.",
                    required=bool(metadata.get("scene_tree_required", False)),
                    media_type="application/json",
                    derived_from=[image_evidence_id],
                    metadata={
                        "capture_id": capture.get("capture_id"),
                        "criterion_id": capture.get("criterion_id"),
                        "backend": capture.get("backend"),
                        "node_count": metadata.get("scene_tree_node_count"),
                        "max_depth": metadata.get("scene_tree_max_depth"),
                    },
                ))

    evidence = _assign_evidence_ids(records)
    return {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": mission_dir.name,
        "created_at": created_at,
        "updated_at": _now(),
        "producer": "mission.verify",
        "evidence": evidence,
        "metadata": {
            "result": report.get("result"),
            "completed_units": [
                item.get("id")
                for item in implementation_assessment.get("completed_units", [])
                if isinstance(item, dict)
            ],
        },
    }


def _evidence_ids_by_kind(manifest: dict[str, Any]) -> dict[str, list[str]]:
    by_kind: dict[str, list[str]] = {}
    for record in manifest.get("evidence", []):
        if not isinstance(record, dict):
            continue
        kind = str(record.get("kind") or "")
        evidence_id = str(record.get("id") or "")
        if kind and evidence_id:
            by_kind.setdefault(kind, []).append(evidence_id)
    return by_kind


def _report_evidence_ids(report: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in report.get("evidence_ids", []):
        evidence_id = str(item or "").strip()
        if evidence_id and evidence_id not in ids:
            ids.append(evidence_id)
    for criterion in report.get("acceptance_criteria", []):
        if not isinstance(criterion, dict):
            continue
        for item in criterion.get("evidence", []):
            evidence_id = str(item or "").strip()
            if evidence_id and evidence_id not in ids:
                ids.append(evidence_id)
    return ids


def _validate_evidence_graph(evidence_ids: set[str], derived_by_id: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    for evidence_id, parents in derived_by_id.items():
        for parent in parents:
            if parent not in evidence_ids:
                errors.append(f"unresolved_evidence_reference: {evidence_id} derives from unknown {parent}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(evidence_id: str, lineage: list[str]) -> None:
        if evidence_id in visiting:
            errors.append(
                "circular_evidence_derivation: "
                + " -> ".join([*lineage, evidence_id])
            )
            return
        if evidence_id in visited:
            return
        visiting.add(evidence_id)
        for parent in derived_by_id.get(evidence_id, []):
            if parent in evidence_ids:
                visit(parent, [*lineage, evidence_id])
        visiting.remove(evidence_id)
        visited.add(evidence_id)

    for evidence_id in sorted(evidence_ids):
        visit(evidence_id, [])
    return errors


def _validate_evidence_manifest(
    mission_dir: Path,
    manifest: dict[str, Any],
    report: dict[str, Any] | None = None,
    *,
    required_kinds: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    evidence = manifest.get("evidence", [])
    if not isinstance(evidence, list):
        return ["invalid_evidence_manifest: evidence must be a list"]
    ids: list[str] = []
    kinds: set[str] = set()
    derived_by_id: dict[str, list[str]] = {}
    required_fields = {
        "id",
        "kind",
        "required",
        "path",
        "sha256",
        "size_bytes",
        "created_at",
        "producer",
        "purpose",
        "media_type",
        "derived_from",
        "metadata",
    }
    for index, record in enumerate(evidence, start=1):
        if not isinstance(record, dict):
            errors.append(f"invalid_evidence_manifest: evidence record {index} is not an object")
            continue
        missing = sorted(required_fields - set(record))
        for key in missing:
            errors.append(f"invalid_evidence_manifest: {record.get('id', index)} missing {key}")
        evidence_id = str(record.get("id") or "").strip()
        if not evidence_id:
            errors.append(f"invalid_evidence_manifest: evidence record {index} missing id")
            continue
        ids.append(evidence_id)
        kind = str(record.get("kind") or "").strip()
        if kind:
            kinds.add(kind)
        target, path_error = _normalize_evidence_path(mission_dir, str(record.get("path") or ""))
        if path_error or target is None:
            errors.append(path_error or f"invalid_evidence_path: {record.get('path')}")
        else:
            actual = _hash_evidence_artifact(target)
            if record.get("sha256") != actual["sha256"]:
                errors.append(f"evidence_hash_mismatch: {evidence_id}")
            if record.get("size_bytes") != actual["size_bytes"]:
                errors.append(f"evidence_size_mismatch: {evidence_id}")
        derived_from = record.get("derived_from", [])
        if not isinstance(derived_from, list):
            errors.append(f"invalid_evidence_manifest: {evidence_id} derived_from must be a list")
            derived_from = []
        derived_by_id[evidence_id] = [str(item) for item in derived_from if str(item)]
        if not isinstance(record.get("metadata", {}), dict):
            errors.append(f"invalid_evidence_manifest: {evidence_id} metadata must be an object")
    seen: set[str] = set()
    for evidence_id in ids:
        if evidence_id in seen:
            errors.append(f"duplicate_evidence_id: {evidence_id}")
        seen.add(evidence_id)
    id_set = set(ids)
    errors.extend(_validate_evidence_graph(id_set, derived_by_id))
    if report is not None:
        for evidence_id in _report_evidence_ids(report):
            if evidence_id not in id_set:
                errors.append(f"unresolved_evidence_reference: report references unknown {evidence_id}")
    for kind in required_kinds or []:
        if kind not in kinds:
            errors.append(f"missing_required_evidence_kind: {kind}")
    return errors


def _required_evidence_kinds(report: dict[str, Any], units: list[dict[str, Any]]) -> list[str]:
    kinds = ["command_output", "file_integrity", "change_inventory"]
    if units and report.get("result") == "passed":
        kinds.extend(["source_diff", "unit_verification"])
    return kinds


def _evidence_error_status(errors: list[str]) -> str:
    for status in (
        "invalid_evidence_path",
        "evidence_artifact_missing",
        "evidence_hash_mismatch",
        "duplicate_evidence_id",
        "unresolved_evidence_reference",
        "circular_evidence_derivation",
        "missing_required_evidence_kind",
        "invalid_visual_capture_request",
        "visual_backend_unavailable",
        "visual_capture_failed",
        "visual_capture_timed_out",
        "invalid_visual_output_path",
        "invalid_png_artifact",
        "visual_artifact_too_large",
        "visual_capture_write_failed",
        "unresolved_visual_criterion",
        "duplicate_capture_id",
        "duplicate_visual_output",
        "invalid_godot_capture_request",
        "invalid_godot_project_path",
        "godot_project_not_found",
        "godot_project_marker_missing",
        "invalid_godot_scene_path",
        "godot_executable_not_found",
        "godot_executable_invalid",
        "godot_launch_failed",
        "godot_capture_failed",
        "godot_capture_timed_out",
        "godot_capture_invalid_output",
        "godot_scene_load_failed",
        "godot_scene_tree_capture_failed",
        "godot_process_cleanup_failed",
    ):
        if any(str(error).startswith(status) for error in errors):
            return status
    return "invalid_evidence_manifest"


def _attach_evidence_to_verification_report(
    report: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    by_kind = _evidence_ids_by_kind(manifest)
    evidence_ids = [
        str(record.get("id"))
        for record in manifest.get("evidence", [])
        if isinstance(record, dict) and record.get("id")
    ]
    support_ids = []
    for kind in ("file_integrity", "command_output", "change_inventory"):
        support_ids.extend(by_kind.get(kind, []))
    visual_ids_by_criterion: dict[str, list[str]] = {}
    visual_ids_by_path: dict[str, str] = {}
    scene_tree_ids_by_path: dict[str, str] = {}
    for record in manifest.get("evidence", []):
        if not isinstance(record, dict) or record.get("kind") not in {"image", "ui_tree"}:
            continue
        evidence_id = str(record.get("id") or "")
        metadata = record.get("metadata", {}) if isinstance(record.get("metadata"), dict) else {}
        criterion_id = str(metadata.get("criterion_id") or "")
        if criterion_id and evidence_id:
            visual_ids_by_criterion.setdefault(criterion_id, []).append(evidence_id)
        path = str(record.get("path") or "")
        if path and evidence_id:
            if record.get("kind") == "ui_tree":
                scene_tree_ids_by_path[path] = evidence_id
            else:
                visual_ids_by_path[path] = evidence_id
    final_report = json.loads(json.dumps(report))
    final_report["evidence_manifest"] = "verification/evidence_manifest.json"
    final_report["evidence_ids"] = evidence_ids
    for criterion in final_report.get("acceptance_criteria", []):
        if not isinstance(criterion, dict):
            continue
        existing = criterion.get("evidence", [])
        criterion["evidence_notes"] = existing if isinstance(existing, list) else [str(existing)]
        criterion_id = str(criterion.get("id") or "")
        criterion["evidence"] = list(dict.fromkeys([
            *support_ids,
            *visual_ids_by_criterion.get(criterion_id, []),
        ]))
        for capture in criterion.get("visual_captures", []):
            if isinstance(capture, dict) and capture.get("artifact_path"):
                capture["evidence_id"] = visual_ids_by_path.get(str(capture.get("artifact_path")))
                metadata = capture.get("metadata", {}) if isinstance(capture.get("metadata"), dict) else {}
                scene_tree_path = str(metadata.get("scene_tree_path") or "")
                if scene_tree_path:
                    capture["scene_tree_evidence_id"] = scene_tree_ids_by_path.get(scene_tree_path)
    visual_captures = final_report.get("visual_captures", {})
    captures = visual_captures.get("captures", []) if isinstance(visual_captures, dict) else []
    if isinstance(captures, list):
        for capture in captures:
            if isinstance(capture, dict) and capture.get("artifact_path"):
                capture["evidence_id"] = visual_ids_by_path.get(str(capture.get("artifact_path")))
                metadata = capture.get("metadata", {}) if isinstance(capture.get("metadata"), dict) else {}
                scene_tree_path = str(metadata.get("scene_tree_path") or "")
                if scene_tree_path:
                    capture["scene_tree_evidence_id"] = scene_tree_ids_by_path.get(scene_tree_path)
    return final_report


def _render_evidence_markdown(manifest: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for record in manifest.get("evidence", []):
        if not isinstance(record, dict):
            continue
        title = str(record.get("kind") or "artifact").replace("_", " ").title()
        lines.extend([
            f"- {record.get('id')} - {title}",
            f"  - Path: {record.get('path')}",
            f"  - SHA-256: {record.get('sha256')}",
            f"  - Required: {str(bool(record.get('required'))).lower()}",
            f"  - Purpose: {record.get('purpose')}",
        ])
    return lines or ["- none"]


def _collect_verification_commands(
    units: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for unit in units:
        unit_id = unit["id"]
        for command in unit.get("verification", []):
            key = (unit_id, command)
            if command and key not in seen:
                seen.add(key)
                commands.append({
                    "command": command,
                    "source": "implementation_unit",
                    "unit_id": unit_id,
                    "required": True,
                })
        verification = artifacts.get("artifact_index", {}).get(unit_id, {}).get("verification", {})
        if isinstance(verification, dict):
            for item in verification.get("commands", []):
                if not isinstance(item, dict):
                    continue
                command = str(item.get("command") or "").strip()
                key = (unit_id, command)
                if command and key not in seen:
                    seen.add(key)
                    commands.append({
                        "command": command,
                        "source": "derived_safe_check",
                        "unit_id": unit_id,
                        "required": True,
                    })
    return commands


def _run_final_verification_commands(command_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in command_specs:
        command = str(spec.get("command") or "").strip()
        started_at = _now()
        argv, error = _verification_command_allowed(command)
        if error or argv is None:
            results.append({
                "command": command,
                "source": spec.get("source") or "unknown",
                "unit_id": spec.get("unit_id"),
                "required": bool(spec.get("required", True)),
                "exit_code": 126,
                "stdout": "",
                "stderr": error or "verification command rejected",
                "started_at": started_at,
                "completed_at": _now(),
                "passed": False,
                "skipped": True,
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
        results.append({
            "command": command,
            "source": spec.get("source") or "unknown",
            "unit_id": spec.get("unit_id"),
            "required": bool(spec.get("required", True)),
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "started_at": started_at,
            "completed_at": _now(),
            "passed": exit_code == 0,
            "skipped": False,
        })
    return results


def _authorized_implementation_paths(units: list[dict[str, Any]], artifacts: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for unit in units:
        paths.update(str(path) for path in unit.get("allowed_paths", []))
        unit_artifacts = artifacts.get("artifact_index", {}).get(unit["id"], {})
        for name in ("after", "before"):
            data = unit_artifacts.get(name)
            if isinstance(data, dict):
                for item in data.get("files", []):
                    if isinstance(item, dict) and item.get("path"):
                        paths.add(str(item["path"]))
        result = unit_artifacts.get("result")
        if isinstance(result, dict):
            for item in result.get("applied", []):
                if isinstance(item, dict) and item.get("path"):
                    paths.add(str(item["path"]))
            for item in result.get("file_changes", []):
                if isinstance(item, dict) and item.get("path"):
                    paths.add(str(item["path"]))
    return paths


def _detect_unexpected_changes(
    manifest: dict[str, Any],
    units: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> list[dict[str, Any]]:
    current_status = _git_status_lines()
    pre_existing_lines = {
        str(line) for line in manifest.get("pre_existing_modified_paths", [])
        if isinstance(line, str)
    }
    pre_existing_paths = {_status_path(line) for line in pre_existing_lines}
    authorized_paths = _authorized_implementation_paths(units, artifacts)
    changes: list[dict[str, Any]] = []
    for line in current_status:
        path = _status_path(line)
        if not path or "__pycache__/" in path or path.endswith(".pyc"):
            continue
        if path in authorized_paths:
            reason = "mission_authorized"
            pre_existing = False
        elif line in pre_existing_lines or path in pre_existing_paths:
            reason = "pre_existing_unrelated"
            pre_existing = True
        elif any(
            pre_path.endswith("/") and path.startswith(pre_path)
            for pre_path in pre_existing_paths
        ):
            reason = "pre_existing_unrelated"
            pre_existing = True
        else:
            reason = "unexpected_new_change"
            pre_existing = False
        changes.append({
            "path": path,
            "status": line[:2],
            "reason": reason,
            "pre_existing": pre_existing,
        })
    return changes


def _assess_acceptance_criteria(
    proposal: dict[str, Any],
    *,
    blocking_failures: list[str],
    evidence_gaps: list[str],
    file_integrity: dict[str, Any],
    verification_commands: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_criteria = proposal.get("acceptance_criteria", [])
    criteria = raw_criteria if isinstance(raw_criteria, list) else []
    assessments: list[dict[str, Any]] = []
    if not criteria:
        return assessments
    command_evidence = [
        item.get("command") for item in verification_commands
        if item.get("passed")
    ]
    for index, raw_criterion in enumerate(criteria, start=1):
        evaluation: dict[str, Any] = {}
        if isinstance(raw_criterion, dict):
            criterion = str(
                raw_criterion.get("criterion")
                or raw_criterion.get("description")
                or raw_criterion.get("text")
                or ""
            ).strip()
            criterion_id = str(
                raw_criterion.get("id")
                or raw_criterion.get("criterion_id")
                or f"criterion-{index:03d}"
            ).strip()
            if isinstance(raw_criterion.get("evaluation"), dict):
                evaluation = dict(raw_criterion.get("evaluation") or {})
        else:
            criterion = str(raw_criterion).strip()
            criterion_id = f"criterion-{index:03d}"
        if not criterion:
            continue
        if blocking_failures:
            status = "failed"
            evidence = blocking_failures[:5]
        elif evidence_gaps:
            status = "inconclusive"
            evidence = evidence_gaps[:5]
        elif evaluation.get("mode") == "operator_review_required":
            status = "inconclusive"
            evidence = [
                str(evaluation.get("reason") or "operator review is required for this criterion")
            ]
        elif file_integrity.get("all_match_recorded_after_state") and all(
            item.get("passed") for item in verification_commands
            if item.get("required")
        ):
            status = "passed"
            evidence = [
                "all completed unit after-state hashes match current repository state",
                *[str(command) for command in command_evidence[:4]],
            ]
        else:
            status = "inconclusive"
            evidence = ["acceptance criterion could not be evaluated from available evidence"]
        assessments.append({
            "id": criterion_id,
            "criterion": criterion,
            "status": status,
            "evidence": evidence,
            "evaluation": evaluation,
        })
    return assessments


def _visual_result_blocks_success(capture: dict[str, Any]) -> tuple[str, str]:
    status = str(capture.get("status") or "")
    if status == "succeeded":
        return "inconclusive", "A screenshot was captured, but no deterministic visual evaluator is configured."
    if status == "invalid_output":
        return "failed", str(capture.get("error") or "invalid visual capture output")
    if status == "failed":
        return "failed", str(capture.get("error") or "visual capture failed")
    if status == "timed_out":
        return "inconclusive", str(capture.get("error") or "visual capture timed out")
    return "inconclusive", str(capture.get("error") or "visual backend unavailable")


def _apply_visual_capture_results_to_report(
    report: dict[str, Any],
    visual_captures: dict[str, Any],
) -> dict[str, Any]:
    if not visual_captures.get("captures"):
        return report
    updated = json.loads(json.dumps(report))
    criteria = updated.get("acceptance_criteria", [])
    by_id = {
        str(item.get("id")): item
        for item in criteria
        if isinstance(item, dict) and item.get("id")
    }
    visual_failures: list[str] = []
    visual_gaps: list[str] = []
    for capture in visual_captures.get("captures", []):
        if not isinstance(capture, dict):
            continue
        criterion = by_id.get(str(capture.get("criterion_id") or ""))
        if criterion is None:
            visual_gaps.append(
                f"visual capture {capture.get('capture_id')} references missing criterion"
            )
            continue
        visual_records = criterion.setdefault("visual_captures", [])
        visual_records.append({
            "capture_id": capture.get("capture_id"),
            "status": capture.get("status"),
            "backend": capture.get("backend"),
            "artifact_path": capture.get("artifact_path"),
            "evidence_id": capture.get("evidence_id"),
            "required": capture.get("required"),
            "metadata": capture.get("metadata") if isinstance(capture.get("metadata"), dict) else {},
        })
        if capture.get("required"):
            visual_status, reason = _visual_result_blocks_success(capture)
            if visual_status == "failed":
                criterion["status"] = "failed"
                visual_failures.append(reason)
            elif criterion.get("status") != "failed":
                criterion["status"] = "inconclusive"
                visual_gaps.append(reason)
            criterion["evaluation"] = {
                "mode": "operator_review_required",
                "status": "pending" if visual_status == "inconclusive" else visual_status,
                "reason": reason,
            }
        else:
            evaluation = criterion.get("evaluation")
            if not isinstance(evaluation, dict):
                evaluation = {}
            evaluation.setdefault("mode", "nonvisual_or_optional_visual")
            if capture.get("status") == "succeeded":
                evaluation["visual_capture_status"] = "succeeded"
            elif capture.get("status") != "succeeded":
                evaluation["visual_capture_status"] = capture.get("status")
                evaluation["visual_capture_reason"] = capture.get("error")
            criterion["evaluation"] = evaluation
    result, mission_complete, failures, gaps, risks = _verification_result(
        updated.get("implementation_assessment", {}),
        updated.get("file_integrity", {}),
        updated.get("verification_commands", []),
        updated.get("unexpected_changes", []),
        criteria,
    )
    failures = list(dict.fromkeys([*failures, *visual_failures]))
    gaps = list(dict.fromkeys([*gaps, *visual_gaps]))
    if failures:
        result = "failed"
        mission_complete = False
    elif gaps:
        result = "inconclusive"
        mission_complete = False
    updated["result"] = result
    updated["mission_complete"] = mission_complete
    updated["failures"] = failures
    updated["evidence_gaps"] = gaps
    updated["risks_remaining"] = risks
    if result == "passed":
        updated["next_action"] = {
            "command": None,
            "reason": "Mission completed successfully.",
        }
        updated["summary"] = "Verification passed. Completed implementation artifacts match current repository state."
    elif result == "failed":
        updated["next_action"] = {
            "command": "Review verification/report.json",
            "reason": "Verification found blocking failures.",
        }
        updated["summary"] = "Verification failed. Blocking mismatches or command failures were found."
    else:
        updated["next_action"] = {
            "command": "Review verification/report.json",
            "reason": "Verification could not establish success or failure conclusively.",
        }
        updated["summary"] = "Verification is inconclusive. Evidence gaps prevent a trustworthy pass/fail result."
    updated["visual_captures"] = visual_captures
    return updated


def _verification_result(
    implementation_assessment: dict[str, Any],
    file_integrity: dict[str, Any],
    verification_commands: list[dict[str, Any]],
    unexpected_changes: list[dict[str, Any]],
    acceptance_criteria: list[dict[str, Any]],
) -> tuple[str, bool, list[str], list[str], list[str]]:
    failures: list[str] = []
    gaps: list[str] = []
    risks: list[str] = []
    if implementation_assessment.get("failed_units"):
        failures.append("one or more implementation units are recorded as failed")
    if implementation_assessment.get("incomplete_units"):
        gaps.append("one or more implementation unit artifacts are missing or incomplete")
    if file_integrity.get("mismatched"):
        failures.append("current file hash does not match recorded after.json state")
    if file_integrity.get("missing"):
        failures.append("expected implemented file is missing")
    if file_integrity.get("unexpected_existing"):
        failures.append("file expected absent is currently present")
    if file_integrity.get("invalid_records"):
        gaps.append("one or more after.json file records are invalid")
    for item in verification_commands:
        if item.get("required") and item.get("skipped"):
            gaps.append(f"required verification command skipped: {item.get('command')}")
        elif item.get("required") and not item.get("passed"):
            failures.append(f"required verification command failed: {item.get('command')}")
    for item in unexpected_changes:
        if item.get("reason") == "unexpected_new_change":
            failures.append(f"unexpected repository change: {item.get('path')}")
        elif item.get("reason") == "pre_existing_unrelated":
            risks.append(f"pre-existing unrelated dirty path remains: {item.get('path')}")
    for item in acceptance_criteria:
        if item.get("status") == "failed":
            failures.append(f"acceptance criterion failed: {item.get('criterion')}")
        elif item.get("status") == "inconclusive":
            gaps.append(f"acceptance criterion inconclusive: {item.get('criterion')}")
    failures = list(dict.fromkeys(failures))
    gaps = list(dict.fromkeys(gaps))
    risks = list(dict.fromkeys(risks))
    if failures:
        return "failed", False, failures, gaps, risks
    if gaps:
        return "inconclusive", False, failures, gaps, risks
    return "passed", True, failures, gaps, risks


def _build_verification_report(
    mission_id: str,
    inputs: dict[str, Any],
    implementation_assessment: dict[str, Any],
    file_integrity: dict[str, Any],
    verification_commands: list[dict[str, Any]],
    unexpected_changes: list[dict[str, Any]],
    acceptance_criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    result, mission_complete, failures, gaps, risks = _verification_result(
        implementation_assessment,
        file_integrity,
        verification_commands,
        unexpected_changes,
        acceptance_criteria,
    )
    if result == "passed":
        next_action = {
            "command": None,
            "reason": "Mission completed successfully.",
        }
        summary = "Verification passed. Completed implementation artifacts match current repository state."
    elif result == "failed":
        next_action = {
            "command": "Review verification/report.json",
            "reason": "Verification found blocking failures.",
        }
        summary = "Verification failed. Blocking mismatches or command failures were found."
    else:
        next_action = {
            "command": "Review verification/report.json",
            "reason": "Verification could not establish success or failure conclusively.",
        }
        summary = "Verification is inconclusive. Evidence gaps prevent a trustworthy pass/fail result."
    public_assessment = {
        key: value for key, value in implementation_assessment.items()
        if key != "artifact_index"
    }
    return {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": mission_id,
        "created_at": _now(),
        "authority": "independent_post_implementation_verification",
        "result": result,
        "mission_complete": mission_complete,
        "summary": summary,
        "implementation_assessment": public_assessment,
        "file_integrity": file_integrity,
        "verification_commands": verification_commands,
        "acceptance_criteria": acceptance_criteria,
        "unexpected_changes": unexpected_changes,
        "risks_remaining": risks,
        "failures": failures,
        "evidence_gaps": gaps,
        "next_action": next_action,
        "source_files_modified": False,
        "proposal_path": _stable(_mission_proposal_json_path(MISSIONS_ROOT / mission_id)),
        "review_path": _stable(_mission_review_decision_json_path(MISSIONS_ROOT / mission_id)),
        "implementation_path": _stable(_mission_implementation_manifest_path(MISSIONS_ROOT / mission_id)),
    }


def _validate_verification_report(
    report: dict[str, Any],
    evidence_manifest: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    for key in (
        "schema_version",
        "mission_id",
        "created_at",
        "authority",
        "result",
        "mission_complete",
        "implementation_assessment",
        "file_integrity",
        "verification_commands",
        "acceptance_criteria",
        "unexpected_changes",
        "failures",
        "next_action",
    ):
        if key not in report:
            errors.append(f"missing {key}")
    if report.get("authority") != "independent_post_implementation_verification":
        errors.append("authority must be independent_post_implementation_verification")
    if report.get("result") not in {"passed", "failed", "inconclusive"}:
        errors.append("result must be passed, failed, or inconclusive")
    if report.get("result") == "passed" and report.get("mission_complete") is not True:
        errors.append("passed report must mark mission_complete true")
    if report.get("result") != "passed" and report.get("mission_complete") is True:
        errors.append("non-passed report cannot mark mission_complete true")
    if "evidence_manifest" in report or "evidence_ids" in report:
        if report.get("evidence_manifest") != "verification/evidence_manifest.json":
            errors.append("evidence_manifest must be verification/evidence_manifest.json")
        if not isinstance(report.get("evidence_ids"), list):
            errors.append("evidence_ids must be a list")
    if evidence_manifest is not None:
        known_ids = {
            str(record.get("id"))
            for record in evidence_manifest.get("evidence", [])
            if isinstance(record, dict) and record.get("id")
        }
        for evidence_id in _report_evidence_ids(report):
            if evidence_id not in known_ids:
                errors.append(f"unresolved_evidence_reference: report references unknown {evidence_id}")
    return errors


def _render_verification_markdown(
    report: dict[str, Any],
    evidence_manifest: dict[str, Any] | None = None,
) -> str:
    def bullet(items: list[Any]) -> list[str]:
        return [f"- {item}" for item in items] or ["- none"]

    assessment = report.get("implementation_assessment", {})
    file_integrity = report.get("file_integrity", {})
    lines = [
        "# Mission Verification",
        "",
        "## Result",
        "",
        str(report.get("result") or ""),
        "",
        "## Summary",
        "",
        str(report.get("summary") or ""),
        "",
        "## Implementation Unit Status",
        "",
        f"All units complete: {bool(assessment.get('all_units_complete'))}",
        "",
        "Completed:",
        *bullet([item.get("id") for item in assessment.get("completed_units", []) if isinstance(item, dict)]),
        "",
        "Incomplete:",
        *bullet([item.get("id") for item in assessment.get("incomplete_units", []) if isinstance(item, dict)]),
        "",
        "Failed:",
        *bullet([item.get("id") for item in assessment.get("failed_units", []) if isinstance(item, dict)]),
        "",
        "## File Integrity",
        "",
        f"All match recorded after state: {bool(file_integrity.get('all_match_recorded_after_state'))}",
        "",
        "Mismatched:",
        *bullet([item.get("path") for item in file_integrity.get("mismatched", []) if isinstance(item, dict)]),
        "",
        "Missing:",
        *bullet([item.get("path") for item in file_integrity.get("missing", []) if isinstance(item, dict)]),
        "",
        "Unexpected existing:",
        *bullet([item.get("path") for item in file_integrity.get("unexpected_existing", []) if isinstance(item, dict)]),
        "",
        "## Verification Commands",
    ]
    for item in report.get("verification_commands", []):
        lines.append(
            f"- {item.get('command')} :: passed={item.get('passed')} "
            f"exit={item.get('exit_code')} source={item.get('source')}"
        )
    if not report.get("verification_commands"):
        lines.append("- none")
    lines.extend([
        "",
        "## Acceptance Criteria",
    ])
    for item in report.get("acceptance_criteria", []):
        evidence_ids = ", ".join(str(evidence_id) for evidence_id in item.get("evidence", [])) or "none"
        lines.append(
            f"- {item.get('status')}: {item.get('criterion')} "
            f"(evidence: {evidence_ids})"
        )
    if not report.get("acceptance_criteria"):
        lines.append("- none")
    lines.extend([
        "",
        "## Unexpected Changes",
    ])
    for item in report.get("unexpected_changes", []):
        lines.append(
            f"- {item.get('path')}: {item.get('reason')} "
            f"pre_existing={item.get('pre_existing')}"
        )
    if not report.get("unexpected_changes"):
        lines.append("- none")
    lines.extend([
        "",
        "## Visual Evidence",
    ])
    visual_captures = report.get("visual_captures", {})
    captures = visual_captures.get("captures", []) if isinstance(visual_captures, dict) else []
    if captures:
        for capture in captures:
            metadata = capture.get("metadata", {}) if isinstance(capture.get("metadata"), dict) else {}
            lines.extend([
                "",
                f"### {capture.get('capture_id')}",
                "",
                f"- Backend: {capture.get('backend')}",
                f"- Status: {capture.get('status')}",
                f"- Criterion: {capture.get('criterion_id')}",
                f"- Evidence: {capture.get('evidence_id') or 'none'}",
                f"- Path: {capture.get('artifact_path') or 'none'}",
                f"- Dimensions: {capture.get('width') or 'unknown'}x{capture.get('height') or 'unknown'}",
                f"- Scene tree: {capture.get('scene_tree_evidence_id') or 'none'}",
                f"- Godot version: {metadata.get('godot_version') or 'unknown'}",
                f"- Execution mode: {metadata.get('execution_mode') or 'unknown'}",
                f"- Purpose: {capture.get('purpose') or ''}",
                f"- Evaluation: {capture.get('error') or 'operator review required when not otherwise proven'}",
            ])
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Remaining Risks",
        *bullet(report.get("risks_remaining", [])),
        "",
        "## Failures",
        *bullet(report.get("failures", [])),
        "",
        "## Evidence",
        "",
        f"Manifest: {report.get('evidence_manifest') or 'none'}",
        "",
        *_render_evidence_markdown(evidence_manifest or {}),
        "",
        "## Next Action",
        "",
        str(report.get("next_action", {}).get("command")),
        "",
        str(report.get("next_action", {}).get("reason") or ""),
        "",
    ])
    return "\n".join(lines)


def _write_verification_artifacts(
    mission_dir: Path,
    report: dict[str, Any],
    proposal: dict[str, Any],
    units: list[dict[str, Any]],
    implementation_assessment: dict[str, Any],
) -> dict[str, Any]:
    verification_dir = _mission_verification_dir(mission_dir)
    verification_dir.mkdir(parents=True, exist_ok=True)
    _mission_verification_evidence_dir(mission_dir).mkdir(parents=True, exist_ok=True)
    _atomic_json(verification_dir / "commands.json", {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": report.get("mission_id"),
        "created_at": report.get("created_at"),
        "commands": report.get("verification_commands", []),
    })
    _atomic_json(verification_dir / "file_checks.json", {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": report.get("mission_id"),
        "created_at": report.get("created_at"),
        "file_integrity": report.get("file_integrity", {}),
    })
    _atomic_json(verification_dir / "unexpected_changes.json", {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": report.get("mission_id"),
        "created_at": report.get("created_at"),
        "unexpected_changes": report.get("unexpected_changes", []),
    })
    try:
        visual_requests = _collect_visual_capture_requests(
            proposal,
            report.get("acceptance_criteria", []),
        )
        if visual_requests:
            visual_captures = _execute_visual_captures(visual_requests, mission_dir)
            report = _apply_visual_capture_results_to_report(report, visual_captures)
        evidence_manifest = _collect_verification_evidence(
            mission_dir,
            proposal,
            units,
            implementation_assessment,
            report,
        )
        required_kinds = _required_evidence_kinds(report, units)
        validation_errors = _validate_evidence_manifest(
            mission_dir,
            evidence_manifest,
            required_kinds=required_kinds,
        )
        if validation_errors:
            status = _evidence_error_status(validation_errors)
            raise VerificationEvidenceError(
                status,
                "Evidence manifest failed validation.",
                validation_errors,
            )
        _atomic_json(_mission_evidence_manifest_path(mission_dir), evidence_manifest)
        final_report = _attach_evidence_to_verification_report(report, evidence_manifest)
        validation_errors = _validate_evidence_manifest(
            mission_dir,
            evidence_manifest,
            final_report,
            required_kinds=required_kinds,
        )
        validation_errors.extend(_validate_verification_report(final_report, evidence_manifest))
        if validation_errors:
            status = _evidence_error_status(validation_errors)
            raise VerificationEvidenceError(
                status,
                "Verification evidence references failed validation.",
                validation_errors,
            )
        if final_report.get("visual_captures"):
            _atomic_json(verification_dir / "visual_captures.json", final_report["visual_captures"])
    except VerificationEvidenceError:
        raise
    except Exception as exc:
        raise VerificationEvidenceError(
            "evidence_write_failed",
            f"{type(exc).__name__}: {exc}",
        ) from exc
    _atomic_json(_mission_verification_report_json_path(mission_dir), final_report)
    _atomic_text(
        _mission_verification_report_md_path(mission_dir),
        _render_verification_markdown(final_report, evidence_manifest),
    )
    return final_report


def _update_state_after_verification(
    state_data: dict[str, Any],
    mission_id: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    result = str(report.get("result") or "inconclusive")
    if result == "passed":
        phase = "complete"
        status = "verification_passed"
    elif result == "failed":
        phase = "verification_failed"
        status = "verification_failed"
    else:
        phase = "verification_inconclusive"
        status = "verification_inconclusive"
    unresolved: list[str] = []
    for item in state_data.get("unresolved", []):
        text = str(item)
        if text in {
            "Implementation has not started.",
            "Implementation remains incomplete.",
            "Verification has not completed.",
        }:
            continue
        if text not in unresolved:
            unresolved.append(text)
    if result == "failed":
        for failure in report.get("failures", [])[:5]:
            text = f"Verification failure: {failure}"
            if text not in unresolved:
                unresolved.append(text)
    elif result == "inconclusive":
        for gap in report.get("evidence_gaps", [])[:5]:
            text = f"Verification inconclusive: {gap}"
            if text not in unresolved:
                unresolved.append(text)
    return {
        **state_data,
        "schema_version": state_data.get("schema_version", MISSION_SCHEMA_VERSION),
        "mission_id": mission_id,
        "updated_at": str(report.get("created_at") or _now()),
        "phase": phase,
        "status": status,
        "implementation_complete": True,
        "verification_complete": True,
        "mission_complete": bool(report.get("mission_complete")),
        "next_action": report["next_action"],
        "unresolved": unresolved,
        "verification": {
            "path": _stable(_mission_verification_report_json_path(MISSIONS_ROOT / mission_id)),
            "created_at": report.get("created_at"),
            "schema_version": MISSION_SCHEMA_VERSION,
            "result": result,
            "mission_complete": bool(report.get("mission_complete")),
        },
    }


def _verification_failure(
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
        "authority": "independent_post_implementation_verification",
        "source_files_modified": False,
    }
    if next_action:
        payload["next_action"] = next_action
    if extra:
        payload.update(extra)
    print(json.dumps(payload, indent=2))
    return exit_code


def _run_bound_mission_verify(args: argparse.Namespace) -> int:
    try:
        mission_dir = _resolve_mission_dir(args.mission)
    except ValueError as exc:
        return _verification_failure(
            "mission_not_found",
            str(args.mission),
            str(exc),
            exit_code=2,
        )

    mission_id = mission_dir.name
    if _mission_verification_report_json_path(mission_dir).exists():
        payload = {
            "ok": False,
            "status": "verification_already_completed",
            "mission_id": mission_id,
            "report_path": _stable(_mission_verification_report_json_path(mission_dir)),
            "markdown_path": _stable(_mission_verification_report_md_path(mission_dir)),
            "authority": "independent_post_implementation_verification",
            "source_files_modified": False,
        }
        print(json.dumps(payload, indent=2))
        return 0
    if not _mission_proposal_json_path(mission_dir).exists():
        return _verification_failure(
            "proposal_required",
            mission_id,
            "proposal/proposal.json is required before verification.",
            next_action={
                "command": mission_command("propose", mission_id),
                "authority": "implementation_proposal",
            },
            exit_code=1,
        )
    if not _mission_review_decision_json_path(mission_dir).exists():
        return _verification_failure(
            "review_required",
            mission_id,
            "review/decision.json is required before verification.",
            next_action={
                "command": mission_command("review", mission_id, "--approve"),
                "authority": "operator_review",
            },
            exit_code=1,
        )
    if not _mission_implementation_manifest_path(mission_dir).exists():
        return _verification_failure(
            "implementation_required",
            mission_id,
            "implementation/manifest.json is required before verification.",
            next_action={
                "command": mission_command("implement", mission_id),
                "authority": "approved_implementation_execution",
            },
            exit_code=1,
        )

    try:
        inputs = _load_verification_inputs(mission_dir)
    except ValueError as exc:
        return _verification_failure(
            "invalid_verification_input",
            mission_id,
            str(exc),
            exit_code=2,
        )

    units, unit_errors = _normalize_implementation_units(inputs["proposal"])
    if unit_errors or not units:
        return _verification_failure(
            "invalid_verification_input",
            mission_id,
            "Proposal implementation units are invalid.",
            extra={"validation_errors": unit_errors},
            exit_code=1,
        )

    ready, readiness_status, readiness_reason = _validate_verification_readiness(inputs, units)
    if not ready:
        next_action = None
        if readiness_status == "implementation_incomplete":
            next_action = {
                "command": mission_command("implement", mission_id),
                "authority": "approved_implementation_execution",
            }
        return _verification_failure(
            readiness_status or "invalid_verification_input",
            mission_id,
            readiness_reason or "Mission is not ready for verification.",
            next_action=next_action,
            exit_code=1,
        )

    implementation_assessment = _assess_implementation_unit_artifacts(
        mission_dir,
        units,
        inputs["implementation"],
    )
    file_integrity = _compare_file_integrity(
        mission_dir,
        units,
        implementation_assessment,
    )
    command_specs = _collect_verification_commands(units, implementation_assessment)
    verification_commands = _run_final_verification_commands(command_specs)
    unexpected_changes = _detect_unexpected_changes(
        inputs["implementation"],
        units,
        implementation_assessment,
    )
    provisional_failures: list[str] = []
    provisional_gaps: list[str] = []
    if implementation_assessment.get("failed_units"):
        provisional_failures.append("one or more implementation units are recorded as failed")
    if implementation_assessment.get("incomplete_units"):
        provisional_gaps.append("one or more implementation unit artifacts are missing or incomplete")
    if not file_integrity.get("all_match_recorded_after_state"):
        if file_integrity.get("mismatched") or file_integrity.get("missing") or file_integrity.get("unexpected_existing"):
            provisional_failures.append("file integrity mismatch found")
        if file_integrity.get("invalid_records"):
            provisional_gaps.append("invalid after.json records found")
    for item in verification_commands:
        if item.get("required") and item.get("skipped"):
            provisional_gaps.append(f"required verification command skipped: {item.get('command')}")
        elif item.get("required") and not item.get("passed"):
            provisional_failures.append(f"required verification command failed: {item.get('command')}")
    for item in unexpected_changes:
        if item.get("reason") == "unexpected_new_change":
            provisional_failures.append(f"unexpected repository change: {item.get('path')}")
    acceptance = _assess_acceptance_criteria(
        inputs["proposal"],
        blocking_failures=provisional_failures,
        evidence_gaps=provisional_gaps,
        file_integrity=file_integrity,
        verification_commands=verification_commands,
    )
    report = _build_verification_report(
        mission_id,
        inputs,
        implementation_assessment,
        file_integrity,
        verification_commands,
        unexpected_changes,
        acceptance,
    )
    validation_errors = _validate_verification_report(report)
    if validation_errors:
        return _verification_failure(
            "invalid_verification_input",
            mission_id,
            "Generated verification report failed validation.",
            extra={"validation_errors": validation_errors},
            exit_code=1,
        )

    try:
        report = _write_verification_artifacts(
            mission_dir,
            report,
            inputs["proposal"],
            units,
            implementation_assessment,
        )
        state_payload = _update_state_after_verification(
            inputs["state"],
            mission_id,
            report,
        )
        _atomic_json(_mission_state_path(mission_dir), state_payload)
    except VerificationEvidenceError as exc:
        return _verification_failure(
            exc.status,
            mission_id,
            exc.reason,
            extra={"validation_errors": exc.errors},
            exit_code=1,
        )
    except Exception as exc:
        return _verification_failure(
            "verification_write_failed",
            mission_id,
            f"{type(exc).__name__}: {exc}",
            exit_code=1,
        )

    observation = {
        "command": "mission verify",
        "status": state_payload.get("status"),
        "mission_id": mission_id,
        "result": report.get("result"),
        "mission_complete": report.get("mission_complete"),
        "report_path": _stable(_mission_verification_report_json_path(mission_dir)),
        "source_files_modified": False,
        "authority": "independent_post_implementation_verification",
    }
    _append_mission_event(mission_dir, "verified", observation)
    refresh_pinboard(
        mission=str(inputs["intent"].get("intent") or mission_id),
        last_observation=observation,
        next_action=state_payload["next_action"],
    )
    payload = {
        "ok": True,
        "status": state_payload.get("status"),
        "mission_id": mission_id,
        "result": report.get("result"),
        "mission_complete": report.get("mission_complete"),
        "report_path": _stable(_mission_verification_report_json_path(mission_dir)),
        "markdown_path": _stable(_mission_verification_report_md_path(mission_dir)),
        "next_action": state_payload["next_action"],
        "source_files_modified": False,
        "authority": "independent_post_implementation_verification",
    }
    print(json.dumps(payload, indent=2))
    return 0