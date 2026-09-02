from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from Agency.Core.work.planning import mission_planning as _mission_planning
from Agency.Core.work.planning import proposal_generation as _proposal_generation
from Agency.Core.work.missions.pipeline.review.execution import (
    ReviewExecutionDependencies,
    run_mission_review as _core_run_mission_review,
)
from Agency.Core.runtime.commands import mission_command
from Agency.Core.work.missions.pipeline.review.helpers import (
    _render_review_markdown,
    _review_next_action,
    _validate_review_request,
)
from Agency.Core.work.missions.pipeline.review.state import (
    ReviewStateDependencies,
    _load_operator_notes,
    _load_proposal as _core_load_proposal,
    _load_review_inputs as _core_load_review_inputs,
    _mission_review_decision_md_path as _core_mission_review_decision_md_path,
    _review_failure as _core_review_failure,
    _update_state_after_review as _core_update_state_after_review,
)
from Agency.Core.work.missions.pipeline.implementation import execution as _implementation_execution
from Agency.Core.work.missions.pipeline.verification import execution as _verification_execution
from Agency.Core.runtime.resourcefulness import (
    ResourcefulnessContext,
    default_planner,
)
from Agency.Core.runtime.runtime_config import effective_model_context_tokens

from Agency.Core.repository.inspection.analysis import (
    InspectionAnalysisDependencies,
    classify_mission_files as _core_classify_mission_files,
    coverage_evidence_from_context as _core_coverage_evidence_from_context,
)
from Agency.Core.repository.inspection.context import (
    InspectionContextDependencies,
    build_inspection_context as _core_build_inspection_context,
)
from Agency.Core.repository.inspection.coverage import (
    InspectionCoverageDependencies,
    update_inspection_coverage as _core_update_inspection_coverage,
)

from Agency.Core.foundation.paths import (
    AGENCY_ROOT,
    DASHBOARD_ROOT,
    MISSIONS_ROOT as DEFAULT_MISSIONS_ROOT,
    PINBOARD_ROOT as DEFAULT_PINBOARD_ROOT,
    stable_path,
)


MISSION_SCHEMA_VERSION = 1
DEFAULT_MISSION_BUDGETS = {
    "max_inspection_passes": 8,
    "max_files_per_pass": 8,
    "max_total_files": 40,
    "max_seconds_per_model_call": 300,
    "max_mission_seconds": 1800,
}

ALLOWED_SCOPE_ROOTS = [
    "UI/OperatorShell",
    "UI/Workbench",
    "UI/Main",
    "UI/shared",
    "Agency/Core/foundation",
    "Agency/Core/knowledge",
    "Agency/Core/repository",
    "Agency/Core/runtime",
    "Agency/Core/work",
]
ALLOWED_SCOPE_FILES = [
    "UI/project.godot",
    "Agency/Core/runtime/_inference_map.md",
]
MISSION_COVERAGE_CATEGORIES = [
    "route_ownership",
    "workspace_host",
    "workbench_root",
    "creation_lifecycle",
    "cleanup_lifecycle",
    "expected_modified_files",
    "verification_surfaces",
]

_MISSIONS_ROOT_ENV = os.environ.get("AGENCY_MISSIONS_ROOT")
MISSIONS_ROOT = (
    Path(_MISSIONS_ROOT_ENV)
    if _MISSIONS_ROOT_ENV
    else DEFAULT_MISSIONS_ROOT
)
if not MISSIONS_ROOT.is_absolute():
    MISSIONS_ROOT = (DASHBOARD_ROOT / MISSIONS_ROOT).resolve()

_PINBOARD_ROOT_ENV = os.environ.get("AGENCY_PINBOARD_ROOT")
PINBOARD_ROOT = (
    Path(_PINBOARD_ROOT_ENV)
    if _PINBOARD_ROOT_ENV
    else DEFAULT_PINBOARD_ROOT
)
if not PINBOARD_ROOT.is_absolute():
    PINBOARD_ROOT = (DASHBOARD_ROOT / PINBOARD_ROOT).resolve()

PINBOARD_JSON = PINBOARD_ROOT / "current.json"
AGENCY_AUDIT = AGENCY_ROOT / "audit" / "output" / "agency_state.json"
OPERATOR_AUDIT = (
    DASHBOARD_ROOT
    / "UI"
    / "OperatorShell"
    / "audit"
    / "output"
    / "operator_shell_state.json"
)
WORKBENCH_AUDIT = (
    DASHBOARD_ROOT
    / "UI"
    / "Workbench"
    / "audit"
    / "output"
    / "capability_state.json"
)
REQUIRED_CONTEXT_FILES = [
    PINBOARD_JSON,
    AGENCY_AUDIT,
    OPERATOR_AUDIT,
    WORKBENCH_AUDIT,
]
PREFERRED_CONTEXT_FILES = [
    "UI/Main/Main.gd",
    "UI/OperatorShell/Main.gd",
    "UI/OperatorShell/layout/WorkspaceSurface.gd",
    "UI/OperatorShell/layout/BottomDock.gd",
    "UI/Workbench/Main/Main.tscn",
    "UI/Workbench/Main/Main.gd",
    "UI/Workbench/scenes/Workbench.gd",
    "UI/Workbench/layout/WorkbenchShellBuilder.gd",
    "UI/shared/ScreenshotController.gd",
]
TEXT_SUFFIXES = {
    ".gd", ".tscn", ".tres", ".godot", ".py", ".yaml", ".yml", ".json", ".md",
    ".txt", ".cfg", ".ini", ".sh", ".ps1", ".gdshader", ".csv", ".tsv",
}
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svgz", ".zip", ".gz",
    ".tar", ".7z", ".rar", ".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".so",
    ".dll", ".exe", ".bin", ".gguf", ".onnx", ".pt", ".safetensors", ".log", ".pid",
}
EXCLUDED_PARTS = {".git", ".godot", "__pycache__", "node_modules", ".venv", "venv"}
INSPECTION_CLASSES = ("primary", "secondary", "evidence", "ignored")
PRIMARY_INSPECTION_SUFFIXES = {".gd", ".tscn", ".tres", ".godot", ".yaml", ".yml", ".py", ".sh", ".ps1"}
SECONDARY_INSPECTION_SUFFIXES = {".md", ".json", ".txt", ".cfg", ".ini", ".csv", ".tsv"}
MAX_CONTEXT_FILES = 40
MAX_TOTAL_SOURCE_BYTES = 65000
MAX_PROMPT_SOURCE_CHARS = 1400
MAX_PROMPT_CHARS = 3600
INSPECTION_MAX_NEW_TOKENS = 768
PLAN_MAX_NEW_TOKENS = 1024
PROPOSAL_MAX_NEW_TOKENS = 1024
IMPLEMENTATION_MAX_NEW_TOKENS = 1536
MAX_IMPLEMENTATION_FILE_BYTES = 20000
MAX_IMPLEMENTATION_PROMPT_CHARS = 6000
MAX_VERIFICATION_OUTPUT_CHARS = 4000
PYTHON = Path(sys.executable)



class MissionOperationError(ValueError):
    def __init__(self, payload: dict[str, Any], return_code: int) -> None:
        super().__init__(str(payload.get("reason") or payload.get("status")))
        self.payload = payload
        self.return_code = return_code



def _noop_refresh_pinboard(**_kwargs: Any) -> dict[str, Any]:
    return {}


def _refresh_callback(refresh_pinboard: Callable[..., Any] | None) -> Callable[..., Any]:
    return refresh_pinboard or _noop_refresh_pinboard


def _emit_to(outputs: list[dict[str, Any]]) -> Callable[[dict[str, Any]], None]:
    def emit(payload: dict[str, Any]) -> None:
        outputs.append(payload)
    return emit


def _payload_from_text(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(str(text or "")):
        if char != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _operation_payload(outputs: list[dict[str, Any]], code: int, fallback_status: str) -> dict[str, Any]:
    payload = outputs[-1] if outputs else {
        "ok": code == 0,
        "status": fallback_status,
        "authority": "shared_mission_runtime",
    }
    if code != 0:
        raise MissionOperationError(payload, code)
    return payload


def _run_emitting_operation(operation: Callable[[Callable[[dict[str, Any]], None]], int], fallback_status: str) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    code = operation(_emit_to(outputs))
    return _operation_payload(outputs, code, fallback_status)


def _run_printing_operation(operation: Callable[[], int], fallback_status: str) -> dict[str, Any]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = operation()
    text = stdout.getvalue().strip()
    payload = _payload_from_text(text) or {
        "ok": code == 0,
        "status": fallback_status,
        "stdout": text,
        "authority": "shared_mission_runtime",
    }
    if code != 0:
        raise MissionOperationError(payload, code)
    return payload


def _resolve_with_root(root: Path | None) -> Callable[[str | None], Path]:
    return lambda mission: resolve_mission_dir(str(mission), root=root)


def _parse_model_json_object(text: str) -> dict[str, Any] | None:
    draft = str(text or "").strip()
    if not draft:
        return None
    if draft.startswith("```"):
        draft = re.sub(r"^```(?:json)?\s*", "", draft, flags=re.IGNORECASE)
        draft = re.sub(r"\s*```$", "", draft)
    decoder = json.JSONDecoder()
    for index, char in enumerate(draft):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(draft[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _as_string_list(value: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(item.get("summary") or item.get("statement") or item.get("name") or "").strip()
        else:
            text = str(item).strip()
        if text:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _run_command(command: list[str], timeout: int = 20) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=DASHBOARD_ROOT, text=True, capture_output=True, timeout=timeout)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:]}


def _git_status_lines() -> list[str]:
    result = _run_command(["git", "status", "--porcelain"], timeout=20)
    return result.get("stdout", "").splitlines()


def _status_path(line: str) -> str:
    return line[3:] if len(line) > 3 else line


def _model_status() -> dict[str, Any]:
    try:
        from Agency.Core.runtime import model_server_manager
        manager = model_server_manager.status_payload()
    except Exception as exc:
        return {"status": "error", "configured": False, "healthy": False, "reason": f"{type(exc).__name__}: {exc}"}
    status = str(manager.get("status") or "unknown")
    if status == "ready" and bool(manager.get("healthy")) and bool(manager.get("localhost_only", True)):
        local_status = "ready"
    elif status in {"stopped", "unconfigured", "starting", "stopping"}:
        local_status = status
    else:
        local_status = "error"
    return {
        "status": local_status,
        "manager_status": status,
        "configured": bool(manager.get("configured")),
        "healthy": bool(manager.get("healthy")),
        "localhost_only": bool(manager.get("localhost_only", True)),
        "pid": manager.get("pid"),
        "endpoint": manager.get("chat_endpoint") or manager.get("endpoint"),
        "model_path": manager.get("model_path"),
        "server_path": manager.get("server_path"),
        "ctx_size": manager.get("ctx_size"),
        "model_context_tokens": manager.get("model_context_tokens") or manager.get("ctx_size"),
        "runtime_profiles_path": manager.get("runtime_profiles_path"),
        "runtime_profile": manager.get("runtime_profile"),
        "model_path_source": manager.get("model_path_source"),
        "context_source": manager.get("context_source"),
        "gpu_layers_source": manager.get("gpu_layers_source"),
        "reason": manager.get("reason") or manager.get("stderr") or "",
        "manager": manager,
    }


def _model_context_tokens(model_server_status: dict[str, Any] | None = None) -> int:
    status = model_server_status or {}
    for key in ("model_context_tokens", "ctx_size"):
        try:
            value = int(status.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    manager = status.get("manager")
    if isinstance(manager, dict):
        for key in ("model_context_tokens", "ctx_size"):
            try:
                value = int(manager.get(key))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return effective_model_context_tokens()


def _require_model_ready(*, start_model_server: bool) -> tuple[bool, dict[str, Any], bool]:
    if (os.environ.get("AGENCY_MOCK_MODEL_RESPONSE") is not None
        or os.environ.get("AGENCY_MOCK_IMPLEMENTATION_RESPONSE") is not None
        or os.environ.get("AGENCY_MOCK_EMPTY_MODEL") == "1"):
        return True, {
            "status": "ready",
            "configured": True,
            "healthy": True,
            "localhost_only": True,
            "mock": True,
            "reason": "Agency mock model environment is active.",
        }, False
    status = _model_status()
    if status.get("status") == "ready":
        return True, status, False
    status["failure_code"] = "configured_but_server_unavailable"
    return False, status, False


def _call_model(prompt: str, system_context: str, max_new_tokens: int) -> dict[str, Any]:
    if os.environ.get("AGENCY_MOCK_EMPTY_MODEL") == "1":
        return {"ok": False, "status": "ExpectedFailure", "reason": "AGENCY_MOCK_EMPTY_MODEL requested empty response", "draft": "", "usage": {}}
    mock = os.environ.get("AGENCY_MOCK_MODEL_RESPONSE")
    if mock is not None:
        return {"ok": True, "status": "draft_generated", "reason": "AGENCY_MOCK_MODEL_RESPONSE supplied draft", "draft": mock, "usage": {"mock": True}}
    from Agency.Core.runtime import model_service
    started = time.monotonic()
    payload = model_service.ask_model(prompt=prompt, system_context=system_context, max_new_tokens=max_new_tokens)
    payload["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return payload


def _mission_plan_dir(mission_dir: Path) -> Path:
    return mission_dir / "plan"


def _mission_plan_md_path(mission_dir: Path) -> Path:
    return _mission_plan_dir(mission_dir) / "plan.md"


def _mission_proposal_dir(mission_dir: Path) -> Path:
    return mission_dir / "proposal"


def _mission_proposal_md_path(mission_dir: Path) -> Path:
    return _mission_proposal_dir(mission_dir) / "proposal.md"


def _mission_review_dir(mission_dir: Path) -> Path:
    return mission_dir / "review"


def _load_plan(mission_dir: Path) -> dict[str, Any]:
    return _load_required_mission_json(_mission_plan_json_path(mission_dir))


def _mission_review_decision_md_path(mission_dir: Path) -> Path:
    return _core_mission_review_decision_md_path(mission_dir, _review_state_dependencies())


def _review_state_dependencies(emit: Callable[[dict[str, Any]], None] | None = None) -> ReviewStateDependencies:
    return ReviewStateDependencies(
        load_required_mission_json=_load_required_mission_json,
        mission_intent_path=_mission_intent_path,
        mission_state_path=_mission_state_path,
        mission_proposal_json_path=_mission_proposal_json_path,
        mission_review_dir=_mission_review_dir,
        load_plan=_load_plan,
        now=_now,
        stable=_stable,
        schema_version=MISSION_SCHEMA_VERSION,
        emit_payload=emit or (lambda _payload: None),
    )


def _load_proposal(mission_dir: Path) -> dict[str, Any]:
    return _core_load_proposal(mission_dir, _review_state_dependencies())


def _load_review_inputs(mission_dir: Path) -> dict[str, Any]:
    return _core_load_review_inputs(mission_dir, _review_state_dependencies())


def _update_state_after_review(state_data: dict[str, Any], mission_id: str, decision_payload: dict[str, Any], decision_path: Path) -> dict[str, Any]:
    return _core_update_state_after_review(state_data, mission_id, decision_payload, decision_path, _review_state_dependencies())


def _review_failure_factory(emit: Callable[[dict[str, Any]], None]) -> Callable[..., int]:
    def review_failure(status: str, mission_id: str | None, reason: str, *, next_action: dict[str, Any] | None = None, extra: dict[str, Any] | None = None, exit_code: int = 1) -> int:
        return _core_review_failure(status, mission_id, reason, next_action=next_action, extra=extra, exit_code=exit_code, dependencies=_review_state_dependencies(emit))
    return review_failure


def _planning_dependencies(*, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None, emit: Callable[[dict[str, Any]], None] | None = None) -> _mission_planning.MissionPlanningDependencies:
    return _mission_planning.MissionPlanningDependencies(
        INSPECTION_CLASSES=INSPECTION_CLASSES,
        MISSION_COVERAGE_CATEGORIES=MISSION_COVERAGE_CATEGORIES,
        MISSION_SCHEMA_VERSION=MISSION_SCHEMA_VERSION,
        PLAN_MAX_NEW_TOKENS=PLAN_MAX_NEW_TOKENS,
        _append_mission_event=append_mission_event,
        _as_string_list=_as_string_list,
        _assess_plan_proposal_readiness=_assess_plan_proposal_readiness,
        _atomic_json=_atomic_json,
        _atomic_text=_atomic_text,
        _call_model=_call_model,
        _dedupe_manifest_paths=_dedupe_manifest_paths,
        _load_json=_load_json,
        _load_operator_notes=_load_operator_notes,
        _load_required_mission_json=_load_required_mission_json,
        _mission_coverage_path=_mission_coverage_path,
        _mission_inspect_dir=_mission_inspect_dir,
        _mission_intent_path=_mission_intent_path,
        _mission_manifest_path=_mission_manifest_path,
        _mission_plan_dir=_mission_plan_dir,
        _mission_plan_json_path=_mission_plan_json_path,
        _mission_proposal_json_path=_mission_proposal_json_path,
        _mission_proposal_md_path=_mission_proposal_md_path,
        _mission_state_path=_mission_state_path,
        _next_action_after_plan=_next_action_after_plan,
        _scope_expansion_candidates=_planning_scope_expansion_candidates,
        _now=_now,
        _parse_model_json_object=_parse_model_json_object,
        _require_model_ready=_require_model_ready,
        _resolve_mission_dir=_resolve_with_root(root),
        _stable=_stable,
        refresh_pinboard=_refresh_callback(refresh_pinboard),
        emit=emit or (lambda _payload: None),
    )


def _proposal_dependencies(*, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None, emit: Callable[[dict[str, Any]], None] | None = None) -> _proposal_generation.ProposalGenerationDependencies:
    return _proposal_generation.ProposalGenerationDependencies(
        MISSION_SCHEMA_VERSION=MISSION_SCHEMA_VERSION,
        PROPOSAL_MAX_NEW_TOKENS=PROPOSAL_MAX_NEW_TOKENS,
        _append_mission_event=append_mission_event,
        _as_string_list=_as_string_list,
        _assess_plan_proposal_readiness=_assess_plan_proposal_readiness,
        _atomic_json=_atomic_json,
        _atomic_text=_atomic_text,
        _call_model=_call_model,
        _dedupe_manifest_paths=_dedupe_manifest_paths,
        _load_operator_notes=_load_operator_notes,
        _load_plan=_load_plan,
        _load_required_mission_json=_load_required_mission_json,
        _mission_intent_path=_mission_intent_path,
        _mission_plan_json_path=_mission_plan_json_path,
        _mission_proposal_dir=_mission_proposal_dir,
        _mission_proposal_json_path=_mission_proposal_json_path,
        _mission_proposal_md_path=_mission_proposal_md_path,
        _mission_state_path=_mission_state_path,
        _next_action_after_plan=_next_action_after_plan,
        _now=_now,
        _parse_model_json_object=_parse_model_json_object,
        _require_model_ready=_require_model_ready,
        _resolve_mission_dir=_resolve_with_root(root),
        _stable=_stable,
        refresh_pinboard=_refresh_callback(refresh_pinboard),
        emit=emit or (lambda _payload: None),
    )


def _review_execution_dependencies(*, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None, emit: Callable[[dict[str, Any]], None] | None = None) -> ReviewExecutionDependencies:
    emit_payload = emit or (lambda _payload: None)
    return ReviewExecutionDependencies(
        schema_version=MISSION_SCHEMA_VERSION,
        resolve_mission_dir=_resolve_with_root(root),
        validate_review_request=_validate_review_request,
        review_failure=_review_failure_factory(emit_payload),
        mission_review_decision_json_path=_mission_review_decision_json_path,
        mission_review_decision_md_path=_mission_review_decision_md_path,
        mission_proposal_json_path=_mission_proposal_json_path,
        load_review_inputs=_load_review_inputs,
        now=_now,
        review_next_action=_review_next_action,
        stable=_stable,
        mission_review_dir=_mission_review_dir,
        atomic_json=_atomic_json,
        atomic_text=_atomic_text,
        render_review_markdown=_render_review_markdown,
        update_state_after_review=_update_state_after_review,
        mission_state_path=_mission_state_path,
        append_mission_event=append_mission_event,
        refresh_pinboard=_refresh_callback(refresh_pinboard),
        emit_payload=emit_payload,
    )


def _implementation_execution_dependencies(*, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> _implementation_execution.ImplementationExecutionDependencies:
    return _implementation_execution.ImplementationExecutionDependencies(
        DASHBOARD_ROOT=DASHBOARD_ROOT,
        MISSIONS_ROOT=_missions_root(root),
        MISSION_SCHEMA_VERSION=MISSION_SCHEMA_VERSION,
        IMPLEMENTATION_MAX_NEW_TOKENS=IMPLEMENTATION_MAX_NEW_TOKENS,
        MAX_IMPLEMENTATION_FILE_BYTES=MAX_IMPLEMENTATION_FILE_BYTES,
        MAX_IMPLEMENTATION_PROMPT_CHARS=MAX_IMPLEMENTATION_PROMPT_CHARS,
        MAX_VERIFICATION_OUTPUT_CHARS=MAX_VERIFICATION_OUTPUT_CHARS,
        PYTHON=PYTHON,
        _append_mission_event=append_mission_event,
        _as_string_list=_as_string_list,
        _atomic_json=_atomic_json,
        _atomic_text=_atomic_text,
        _call_model=_call_model,
        _dedupe_manifest_paths=_dedupe_manifest_paths,
        _git_status_lines=_git_status_lines,
        _is_relative_to=_is_relative_to,
        _load_json=_load_json,
        _load_operator_notes=_load_operator_notes,
        _load_plan=_load_plan,
        _load_proposal=_load_proposal,
        _load_required_mission_json=_load_required_mission_json,
        _mission_intent_path=_mission_intent_path,
        _mission_proposal_json_path=_mission_proposal_json_path,
        _mission_review_decision_json_path=_mission_review_decision_json_path,
        _mission_state_path=_mission_state_path,
        _now=_now,
        _parse_model_json_object=_parse_model_json_object,
        _read_text_file=_read_text_file,
        _require_model_ready=_require_model_ready,
        _resolve_mission_dir=_resolve_with_root(root),
        _run_command=_run_command,
        _stable=_stable,
        refresh_pinboard=_refresh_callback(refresh_pinboard),
    )


def _verification_execution_dependencies(*, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> _verification_execution.VerificationExecutionDependencies:
    implementation_deps = _implementation_execution_dependencies(root=root, refresh_pinboard=refresh_pinboard)
    _implementation_execution.bind_dependencies(implementation_deps)
    return _verification_execution.VerificationExecutionDependencies(
        DASHBOARD_ROOT=DASHBOARD_ROOT,
        MISSIONS_ROOT=_missions_root(root),
        MISSION_SCHEMA_VERSION=MISSION_SCHEMA_VERSION,
        MAX_VERIFICATION_OUTPUT_CHARS=MAX_VERIFICATION_OUTPUT_CHARS,
        _append_mission_event=append_mission_event,
        _atomic_json=_atomic_json,
        _atomic_text=_atomic_text,
        _capture_file_state=_implementation_execution._capture_file_state,
        _git_status_lines=_git_status_lines,
        _implementation_execution_order=_implementation_execution._implementation_execution_order,
        _is_relative_to=_is_relative_to,
        _load_json=_load_json,
        _load_operator_notes=_load_operator_notes,
        _load_plan=_load_plan,
        _load_proposal=_load_proposal,
        _load_required_mission_json=_load_required_mission_json,
        _load_review_decision=_implementation_execution._load_review_decision,
        _mission_implementation_manifest_path=_implementation_execution._mission_implementation_manifest_path,
        _mission_intent_path=_mission_intent_path,
        _mission_proposal_json_path=_mission_proposal_json_path,
        _mission_review_decision_json_path=_mission_review_decision_json_path,
        _mission_state_path=_mission_state_path,
        _mission_unit_dir=_implementation_execution._mission_unit_dir,
        _normalize_implementation_operation=_implementation_execution._normalize_implementation_operation,
        _normalize_implementation_units=_implementation_execution._normalize_implementation_units,
        _now=_now,
        _proposal_operation_map=_implementation_execution._proposal_operation_map,
        _resolve_mission_dir=_resolve_with_root(root),
        _resolve_repo_file_path=_implementation_execution._resolve_repo_file_path,
        _sha256_bytes=_implementation_execution._sha256_bytes,
        _stable=_stable,
        _status_path=_status_path,
        _verification_command_allowed=_implementation_execution._verification_command_allowed,
        refresh_pinboard=_refresh_callback(refresh_pinboard),
    )

def _missions_root(root: Path | None = None) -> Path:
    return root or MISSIONS_ROOT


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable(path: Path) -> str:
    return stable_path(path, DASHBOARD_ROOT)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except Exception as exc:
        return {"load_error": str(exc), "path": _stable(path)}


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def agency_blocks_dependent_operations(
    *,
    audit_path: Path = AGENCY_AUDIT,
) -> list[str]:
    data = _load_json(audit_path) or {}
    summary = data.get("summary") if isinstance(data, dict) else {}
    unresolved: list[str] = []
    for key in ("FAIL", "BLOCKED_TIMEOUT"):
        try:
            if int(summary.get(key, 0)) > 0:
                unresolved.append(f"Agency audit reports {key}={summary.get(key)}")
        except Exception:
            pass
    text = json.dumps(data).lower()
    if "approval" in text and "defect" in text and "unresolved" in text:
        unresolved.append("Agency audit contains unresolved approval defect language")
    return unresolved


def validate_engineering_scopes(
    raw_scopes: list[str],
    *,
    dashboard_root: Path = DASHBOARD_ROOT,
) -> list[dict[str, Any]]:
    if not raw_scopes:
        raise ValueError("at least one --scope is required")
    repo_root = dashboard_root.resolve()
    allowed_roots = [
        (rel, (dashboard_root / rel).resolve())
        for rel in ALLOWED_SCOPE_ROOTS
    ]
    allowed_files = [
        (rel, (dashboard_root / rel).resolve())
        for rel in ALLOWED_SCOPE_FILES
    ]
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_scope in raw_scopes:
        raw = str(raw_scope).strip()
        if not raw:
            raise ValueError("empty scope is not allowed")
        raw_path = Path(raw)
        if ".." in raw_path.parts:
            raise ValueError(f"scope contains parent traversal: {raw}")
        candidate = raw_path if raw_path.is_absolute() else dashboard_root / raw_path
        if not candidate.exists():
            raise ValueError(f"scope does not exist: {raw}")
        resolved = candidate.resolve(strict=True)
        if not _is_relative_to(resolved, repo_root):
            raise ValueError(f"scope escapes repository root: {raw}")
        allowed_root = next(
            (rel for rel, allowed_file in allowed_files if resolved == allowed_file),
            None,
        )
        if allowed_root is None:
            allowed_root = next(
                (
                    rel
                    for rel, root in allowed_roots
                    if resolved == root or _is_relative_to(resolved, root)
                ),
                None,
            )
        if allowed_root is None:
            raise ValueError(f"scope is outside the active agent proposal allowlist: {raw}")
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        validated.append({
            "input": raw,
            "relative": resolved.relative_to(repo_root).as_posix(),
            "resolved": str(resolved),
            "allowed_root": allowed_root,
            "kind": "file" if resolved.is_file() else "directory",
        })
    return validated

def _mission_number_from_name(name: str) -> int | None:
    match = re.fullmatch(r"mission-(\d+)", str(name).strip())
    if not match:
        return None
    number = int(match.group(1))
    return number if number > 0 else None


def _next_mission_number(root: Path | None = None) -> int:
    highest = 0
    missions_root = _missions_root(root)
    if missions_root.exists():
        for path in missions_root.iterdir():
            if not path.is_dir():
                continue
            number = _mission_number_from_name(path.name)
            if number is not None:
                highest = max(highest, number)
    return highest + 1


def mission_id(
    _intent: str,
    _scopes: list[dict[str, Any]],
    _created_at: str,
    *,
    root: Path | None = None,
) -> str:
    return f"mission-{_next_mission_number(root)}"


def _normalize_mission_reference(raw_mission: str) -> str:
    mission_text = str(raw_mission).strip()
    if re.fullmatch(r"\d+", mission_text):
        return f"mission-{int(mission_text)}"
    return mission_text


def mission_list_sort_key(path: Path) -> tuple[int, int, str]:
    number = _mission_number_from_name(path.name)
    if number is not None:
        return (1, number, path.name)
    return (0, 0, path.name)


def resolve_mission_dir(raw_mission: str, *, root: Path | None = None) -> Path:
    mission_text = str(raw_mission).strip()
    if not mission_text:
        raise ValueError("mission id is required")
    mission_path = Path(mission_text)
    if mission_path.is_absolute():
        raise ValueError("absolute mission paths are not allowed")
    if ".." in mission_path.parts:
        raise ValueError("mission path traversal is not allowed")
    if len(mission_path.parts) != 1:
        raise ValueError("mission must be identified by mission id only")

    missions_root = _missions_root(root).resolve()
    normalized_mission = _normalize_mission_reference(mission_text)
    candidate = (_missions_root(root) / normalized_mission).resolve()
    if not _is_relative_to(candidate, missions_root):
        raise ValueError("mission path escapes mission root")
    if not candidate.exists():
        raise ValueError(f"mission not found: {mission_text}")
    if not candidate.is_dir():
        raise ValueError(f"mission path is not a directory: {mission_text}")
    return candidate


def _mission_state_path(mission_dir: Path) -> Path:
    return mission_dir / "state.json"


def _mission_intent_path(mission_dir: Path) -> Path:
    return mission_dir / "intent.json"


def _mission_inspect_dir(mission_dir: Path) -> Path:
    return mission_dir / "inspect"


def _mission_manifest_path(mission_dir: Path) -> Path:
    return _mission_inspect_dir(mission_dir) / "manifest.json"


def _mission_coverage_path(mission_dir: Path) -> Path:
    return _mission_inspect_dir(mission_dir) / "coverage.json"


def _mission_knowledge_dir(mission_dir: Path) -> Path:
    return _mission_inspect_dir(mission_dir) / "knowledge"


def _mission_resourcefulness_reconstruction_path(mission_dir: Path) -> Path:
    return _mission_knowledge_dir(mission_dir) / "resourcefulness_reconstruction.json"


def _mission_plan_json_path(mission_dir: Path) -> Path:
    return mission_dir / "plan" / "plan.json"


def _mission_proposal_json_path(mission_dir: Path) -> Path:
    return mission_dir / "proposal" / "proposal.json"


def _mission_review_decision_json_path(mission_dir: Path) -> Path:
    return mission_dir / "review" / "decision.json"


def _mission_implementation_dir(mission_dir: Path) -> Path:
    return mission_dir / "implementation"


def _mission_implementation_manifest_path(mission_dir: Path) -> Path:
    return _mission_implementation_dir(mission_dir) / "manifest.json"


def _mission_verification_dir(mission_dir: Path) -> Path:
    return mission_dir / "verification"


def _mission_verification_report_json_path(mission_dir: Path) -> Path:
    return _mission_verification_dir(mission_dir) / "report.json"


def _mission_verification_evidence_dir(mission_dir: Path) -> Path:
    return _mission_verification_dir(mission_dir) / "evidence"


def _mission_evidence_manifest_path(mission_dir: Path) -> Path:
    return _mission_verification_evidence_dir(mission_dir) / "manifest.json"


def _mission_events_dir(mission_dir: Path) -> Path:
    return mission_dir / "events"


def _load_required_mission_json(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if data is None:
        raise ValueError(f"required mission file is missing: {_stable(path)}")
    if "load_error" in data:
        raise ValueError(
            f"mission file is unreadable: {_stable(path)}: {data.get('load_error')}"
        )
    return data


def _load_optional_mission_json(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if data is None or "load_error" in data:
        return {}
    return data


def _event_slug(event_type: str) -> str:
    slug = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        str(event_type or "event").strip().lower(),
    )
    return slug.strip(".-") or "event"


def _next_event_sequence(events_dir: Path) -> int:
    sequence = 1
    if events_dir.exists():
        for path in events_dir.glob("*.json"):
            match = re.match(r"^(\d+)-", path.name)
            if match:
                sequence = max(sequence, int(match.group(1)) + 1)
    return sequence


def append_mission_event(
    mission_dir: Path,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    events_dir = _mission_events_dir(mission_dir)
    try:
        events_dir.mkdir(parents=True, exist_ok=True)
        sequence = _next_event_sequence(events_dir)
        event = {
            "schema_version": MISSION_SCHEMA_VERSION,
            "mission_id": mission_dir.name,
            "sequence": sequence,
            "event_type": event_type,
            "timestamp": _now(),
            "authority": "mission_event_log",
            "payload": payload,
        }
        path = events_dir / f"{sequence:04d}-{_event_slug(event_type)}.json"
        _atomic_json(path, event)
        return {"ok": True, "path": _stable(path), "sequence": sequence}
    except Exception as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}


def _path_in_validated_scopes(path: Path, scopes: list[dict[str, Any]]) -> bool:
    resolved = path.resolve(strict=True)
    for scope in scopes:
        root = Path(scope["resolved"])
        if root.is_file() and resolved == root:
            return True
        if root.is_dir() and (resolved == root or _is_relative_to(resolved, root)):
            return True
    return False


def _ignore_reason_for_path(
    path: Path,
    *,
    intent_requests: set[str] | None = None,
) -> str | None:
    intent_requests = intent_requests or set()
    rel_parts = path.relative_to(DASHBOARD_ROOT).parts
    name = path.name
    lower_name = name.lower()
    lower_parts = [part.lower() for part in rel_parts]
    if "__pycache__" in rel_parts or path.suffix.lower() in {".pyc", ".pyo"}:
        return "python_cache_file"
    if (
        "audit" in lower_parts
        and "output" in lower_parts
        and "history" in lower_parts
        and "history" not in intent_requests
    ):
        return "historical_generated_audit_output"
    if (
        "audit" in lower_parts
        and "output" in lower_parts
        and re.search(r"(?:20\d{2}[-_]\d{2}[-_]\d{2}|20\d{6}t\d{6}z)", lower_name)
        and "history" not in intent_requests
    ):
        return "historical_generated_audit_output"
    if (
        ".bak" in lower_name
        or lower_name.endswith("~")
        or lower_name.endswith(".tmp")
        or lower_name.endswith(".swp")
    ):
        return "backup_or_temporary_file"
    if any(part in EXCLUDED_PARTS for part in rel_parts):
        return "excluded_path_part"
    if any(part in {"tmp", "temp"} for part in lower_parts):
        return "temporary_output_path"
    if "history" in rel_parts and "audit" in rel_parts:
        return "historical_generated_audit_output"
    if path.suffix.lower() in BINARY_SUFFIXES:
        return "binary_or_runtime_suffix"
    if path.suffix and path.suffix.lower() not in TEXT_SUFFIXES:
        return "unsupported_text_suffix"
    return None


def _skip_reason_for_path(path: Path) -> str | None:
    return _ignore_reason_for_path(path)


def _mission_intent_requests(intent: str) -> set[str]:
    text = str(intent or "").lower()
    requests: set[str] = set()
    if re.search(r"\baudit(?:s|ing)?\b", text):
        requests.add("audit")
    if re.search(r"\b(verif(?:y|ication)|evidence|proof|confirm)\b", text):
        requests.add("verification")
    if re.search(r"\b(regression|smoke|test(?:ing)?)\b", text):
        requests.add("regression_evidence")
    if re.search(r"\b(runtime state|state\.json|pinboard|operational state)\b", text):
        requests.add("runtime_state")
    if re.search(r"\b(history|historical|timeline|compare|comparison)\b", text):
        requests.add("history")
    return requests


def _is_evidence_path(path: Path) -> bool:
    parts = [part.lower() for part in path.relative_to(DASHBOARD_ROOT).parts]
    name = path.name.lower()
    if "audit" in parts and any(part in {"output", "evidence"} for part in parts):
        return True
    if "audit" in parts and name in {"observations.json", "operator_shell_state.json", "capability_state.json"}:
        return True
    return False


def _classify_inspection_file(
    path: Path,
    *,
    intent_requests: set[str] | None = None,
) -> dict[str, str]:
    rel = path.relative_to(DASHBOARD_ROOT).as_posix()
    ignore_reason = _ignore_reason_for_path(path, intent_requests=intent_requests)
    if ignore_reason:
        return {"path": rel, "class": "ignored", "reason": ignore_reason}
    suffix = path.suffix.lower()
    if _is_evidence_path(path):
        return {"path": rel, "class": "evidence"}
    if suffix in PRIMARY_INSPECTION_SUFFIXES:
        return {"path": rel, "class": "primary"}
    if suffix in SECONDARY_INSPECTION_SUFFIXES:
        return {"path": rel, "class": "secondary"}
    return {"path": rel, "class": "ignored", "reason": "unsupported_text_suffix"}


def _classification_map(files_by_class: dict[str, list[str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for class_name in INSPECTION_CLASSES:
        for path in files_by_class.get(class_name, []):
            mapping[path] = class_name
    return mapping


def _entrypoint_rank(path: str) -> int:
    explicit = [
        "UI/Main/Main.gd",
        "UI/Main/Main.tscn",
        "UI/OperatorShell/Main.gd",
        "UI/OperatorShell/scenes/Main.tscn",
        "UI/Workbench/Main/Main.gd",
        "UI/Workbench/Main/Main.tscn",
        "UI/Workbench/scenes/Workbench.gd",
        "UI/Workbench/scenes/Workbench.tscn",
    ]
    if path in explicit:
        return explicit.index(path)
    name = Path(path).name.lower()
    if name in {"main.gd", "main.tscn", "workbench.gd", "workbench.tscn"}:
        return len(explicit)
    return len(explicit) + 1


def _owner_rank(path: str) -> int:
    lower = path.lower()
    owner_markers = (
        "workspace",
        "route",
        "router",
        "missionservice",
        "workbenchshell",
        "bottomdock",
    )
    return 0 if any(marker in lower for marker in owner_markers) else 1


def _normalize_dependency_target(raw_target: str, source_path: str) -> str | None:
    target = str(raw_target or "").split(":", 1)[0].strip()
    if not target:
        return None
    if target.startswith("res://"):
        return target.removeprefix("res://")
    if target.startswith("uid://"):
        return None
    target_path = Path(target)
    if target_path.is_absolute():
        try:
            return target_path.resolve().relative_to(DASHBOARD_ROOT.resolve()).as_posix()
        except ValueError:
            return None
    if target.startswith("."):
        base = Path(source_path).parent
        return (base / target).as_posix()
    return target


def _mission_referenced_paths(mission_dir: Path) -> set[str]:
    referenced: set[str] = set()
    for pass_path in sorted(_mission_inspect_dir(mission_dir).glob("pass_*.json")):
        data = _load_json(pass_path) or {}
        for item in data.get("dependencies", []):
            if not isinstance(item, dict):
                continue
            normalized = _normalize_dependency_target(
                str(item.get("target") or ""),
                str(item.get("file") or ""),
            )
            if normalized:
                referenced.add(normalized)
    return referenced


def _sort_class_paths(paths: list[str], referenced_paths: set[str]) -> list[str]:
    return sorted(
        paths,
        key=lambda path: (
            _entrypoint_rank(path),
            _owner_rank(path),
            0 if path in referenced_paths else 1,
            path.lower(),
            path,
        ),
    )


def _read_text_file(path: Path) -> tuple[str | None, str | None]:
    try:
        raw = path.read_bytes()
    except Exception as exc:
        return None, f"read_error:{exc}"
    if b"\x00" in raw[:4096]:
        return None, "binary_nul_detected"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        try:
            return raw.decode("utf-8-sig"), None
        except UnicodeDecodeError as exc:
            return None, f"decode_error:{exc}"


def _candidate_files(scopes: list[dict[str, Any]]) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for scope in scopes:
        root = Path(scope["resolved"])
        candidates = [root] if root.is_file() else sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(DASHBOARD_ROOT).as_posix())
        for candidate in candidates:
            key = str(candidate.resolve(strict=True))
            if key not in seen:
                seen.add(key)
                paths.append(candidate)
    preferred = {rel: index for index, rel in enumerate(PREFERRED_CONTEXT_FILES)}
    def sort_key(path: Path) -> tuple[int, int, str]:
        rel = path.resolve(strict=True).relative_to(DASHBOARD_ROOT.resolve()).as_posix()
        if rel in preferred:
            return (0, preferred[rel], rel)
        return (1, 0, rel)
    return sorted(paths, key=sort_key)


def _compact_json_context(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if data is None:
        return {"path": _stable(path), "status": "missing"}
    if "load_error" in data:
        return {"path": _stable(path), "status": "unreadable", "error": data.get("load_error")}
    if path == PINBOARD_JSON:
        keep = {key: data.get(key) for key in ("schema_version", "updated_at", "mission", "current_capability", "allowed_actions", "forbidden_actions", "last_observation", "unresolved", "next_action", "active_proposal")}
    else:
        keep = {key: data.get(key) for key in ("schema_version", "generated_at", "rule", "summary", "current_test")}
    keep["path"] = _stable(path)
    keep["status"] = "present"
    return keep


def _extract_symbols(path: Path, text: str) -> list[dict[str, Any]]:
    rel = _stable(path)
    patterns = [
        ("class_name", re.compile(r"^\s*class_name\s+([A-Za-z_][A-Za-z0-9_]*)\b")),
        ("extends", re.compile(r"^\s*extends\s+(.+?)\s*$")),
        ("func", re.compile(r"^\s*(?:static\s+)?func\s+([A-Za-z_][A-Za-z0-9_]*)\b")),
        ("signal", re.compile(r"^\s*signal\s+([A-Za-z_][A-Za-z0-9_]*)\b")),
        ("const", re.compile(r"^\s*const\s+([A-Za-z_][A-Za-z0-9_]*)\b")),
        ("var", re.compile(r"^\s*(?:@onready\s+)?var\s+([A-Za-z_][A-Za-z0-9_]*)\b")),
        ("python_class", re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b")),
        ("python_function", re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\b")),
    ]
    symbols: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in patterns:
            match = pattern.match(line)
            if match:
                symbols.append({
                    "file": rel,
                    "line": line_number,
                    "kind": kind,
                    "name": match.group(1).strip().strip("\"'"),
                })
                break
        if len(symbols) >= 50:
            symbols.append({
                "file": rel,
                "kind": "truncated",
                "name": "symbol_limit_reached",
            })
            break
    return symbols


def _extract_dependencies(path: Path, text: str) -> list[dict[str, Any]]:
    rel = _stable(path)
    patterns = [
        ("preload", re.compile(r"\bpreload\(\s*[\"']([^\"']+)[\"']")),
        ("load", re.compile(r"\bload\(\s*[\"']([^\"']+)[\"']")),
        ("ext_resource", re.compile(r"\bpath=[\"']([^\"']+)[\"']")),
        ("python_from", re.compile(r"^\s*from\s+([A-Za-z0-9_\.]+)\s+import\s+(.+?)\s*$")),
        ("python_import", re.compile(r"^\s*import\s+(.+?)\s*$")),
    ]
    dependencies: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in patterns:
            for match in pattern.finditer(line):
                target = match.group(1).strip()
                if kind == "python_from" and len(match.groups()) > 1:
                    target = f"{target}:{match.group(2).strip()}"
                dependencies.append({
                    "file": rel,
                    "line": line_number,
                    "kind": kind,
                    "target": target,
                })
                if len(dependencies) >= 50:
                    dependencies.append({
                        "file": rel,
                        "kind": "truncated",
                        "target": "dependency_limit_reached",
                    })
                    return dependencies
    return dependencies


def _inspection_evidence_terms(text: str) -> list[str]:
    lower = text.lower()
    terms = [
        "route",
        "workspace",
        "workbench",
        "instantiate",
        "add_child",
        "remove_child",
        "queue_free",
        "cleanup",
        "screenshot",
        "audit",
        "test",
        "verify",
    ]
    return [term for term in terms if term in lower]


def _manifest_path_value(entry: Any) -> str | None:
    if isinstance(entry, str):
        value = entry
    elif isinstance(entry, dict):
        value = str(entry.get("path") or "")
    else:
        value = ""
    value = value.strip()
    return value or None


def _manifest_candidate_paths(entries: list[Any]) -> tuple[list[Path], list[dict[str, Any]]]:
    repo_root = DASHBOARD_ROOT.resolve()
    paths: list[Path] = []
    skipped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        rel = _manifest_path_value(entry)
        if rel is None:
            skipped.append({"path": str(entry), "reason": "invalid_manifest_entry"})
            continue
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            skipped.append({"path": rel, "reason": "invalid_manifest_path"})
            continue
        candidate = (DASHBOARD_ROOT / rel_path).resolve()
        try:
            normalized = candidate.relative_to(repo_root).as_posix()
        except ValueError:
            skipped.append({"path": rel, "reason": "manifest_path_escapes_repository"})
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        paths.append(candidate)
    return paths, skipped


def _inspection_context_dependencies() -> InspectionContextDependencies:
    return InspectionContextDependencies(
        dashboard_root=DASHBOARD_ROOT,
        required_context_files=tuple(REQUIRED_CONTEXT_FILES),
        max_total_source_bytes=MAX_TOTAL_SOURCE_BYTES,
        max_prompt_source_chars=MAX_PROMPT_SOURCE_CHARS,
        max_prompt_chars=MAX_PROMPT_CHARS,
        candidate_files=_candidate_files,
        manifest_candidate_paths=_manifest_candidate_paths,
        path_in_validated_scopes=_path_in_validated_scopes,
        skip_reason_for_path=_skip_reason_for_path,
        read_text_file=_read_text_file,
        inspection_evidence_terms=_inspection_evidence_terms,
        extract_symbols=_extract_symbols,
        extract_dependencies=_extract_dependencies,
        compact_json_context=_compact_json_context,
    )


def _build_inspection_context(
    intent: str,
    scopes: list[dict[str, Any]],
    *,
    candidate_paths: list[Any] | None = None,
    previously_inspected: set[str] | None = None,
    file_classification: dict[str, str] | None = None,
    max_files: int | None = MAX_CONTEXT_FILES,
    stop_at_file_limit: bool = False,
) -> dict[str, Any]:
    return _core_build_inspection_context(
        intent,
        scopes,
        dependencies=_inspection_context_dependencies(),
        candidate_paths=candidate_paths,
        previously_inspected=previously_inspected,
        file_classification=file_classification,
        max_files=max_files,
        stop_at_file_limit=stop_at_file_limit,
    )


def _dedupe_manifest_paths(entries: list[Any]) -> list[str]:
    if not isinstance(entries, list):
        return []
    paths: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        value = _manifest_path_value(entry)
        if value is None or value in seen:
            continue
        seen.add(value)
        paths.append(value)
    return paths


def _merge_skipped_files(
    existing: list[Any],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in [*existing, *incoming]:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        reason = str(item.get("reason") or "")
        if not path or not reason:
            continue
        key = (path, reason)
        if key in seen:
            continue
        seen.add(key)
        merged.append(dict(item))
    return merged


def _discover_mission_files(scopes: list[dict[str, Any]]) -> list[str]:
    return [
        path.resolve(strict=True).relative_to(DASHBOARD_ROOT.resolve()).as_posix()
        for path in _candidate_files(scopes)
    ]


def _inspection_analysis_dependencies() -> InspectionAnalysisDependencies:
    return InspectionAnalysisDependencies(
        dashboard_root=DASHBOARD_ROOT,
        inspection_classes=INSPECTION_CLASSES,
        mission_coverage_categories=tuple(MISSION_COVERAGE_CATEGORIES),
        dedupe_manifest_paths=_dedupe_manifest_paths,
        classify_inspection_file=_classify_inspection_file,
        sort_class_paths=_sort_class_paths,
        next_action_after_plan=_next_action_after_plan,
    )


def _classify_mission_files(
    discovered_files: list[str],
    *,
    intent_requests: set[str],
    referenced_paths: set[str],
) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    return _core_classify_mission_files(
        discovered_files,
        intent_requests=intent_requests,
        referenced_paths=referenced_paths,
        dependencies=_inspection_analysis_dependencies(),
    )


def _mission_class_order(
    intent_requests: set[str],
    coverage: dict[str, Any],
) -> list[str]:
    evidence_requested = bool(
        intent_requests.intersection({
            "audit",
            "verification",
            "history",
            "regression_evidence",
            "runtime_state",
        })
    )
    if evidence_requested:
        return ["primary", "evidence", "secondary"]
    categories = coverage.get("categories", {})
    verification_status = ""
    if isinstance(categories, dict):
        verification_status = str(categories.get("verification_surfaces") or "")
    if verification_status == "not_started":
        return ["primary", "secondary", "evidence"]
    return ["primary", "secondary", "evidence"]


def _active_inspection_queue(
    files_by_class: dict[str, list[str]],
    *,
    inspected_files: set[str],
    intent_requests: set[str],
    coverage: dict[str, Any],
) -> list[str]:
    queue: list[str] = []
    seen: set[str] = set()
    for class_name in _mission_class_order(intent_requests, coverage):
        for path in files_by_class.get(class_name, []):
            if path in inspected_files or path in seen:
                continue
            seen.add(path)
            queue.append(path)
    return queue


def _mission_scopes_from_intent(intent_data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_scopes: list[str] = []
    for entry in intent_data.get("scopes", []):
        if isinstance(entry, dict):
            value = str(entry.get("relative") or entry.get("input") or "").strip()
        else:
            value = str(entry).strip()
        if value:
            raw_scopes.append(value)
    return validate_engineering_scopes(raw_scopes)


def _next_inspection_pass_number(inspect_dir: Path) -> int:
    numbers: list[int] = []
    for path in inspect_dir.glob("pass_*.json"):
        suffix = path.stem.removeprefix("pass_")
        try:
            numbers.append(int(suffix))
        except ValueError:
            continue
    return (max(numbers) + 1) if numbers else 1


def _coverage_evidence_from_context(
    context: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    return _core_coverage_evidence_from_context(
        context,
        dependencies=_inspection_analysis_dependencies(),
    )


def _inspection_coverage_dependencies() -> InspectionCoverageDependencies:
    return InspectionCoverageDependencies(
        schema_version=MISSION_SCHEMA_VERSION,
        coverage_categories=tuple(MISSION_COVERAGE_CATEGORIES),
        coverage_evidence_from_context=_coverage_evidence_from_context,
    )


def _update_inspection_coverage(
    coverage: dict[str, Any],
    context: dict[str, Any],
    *,
    timestamp: str,
    inspection_complete: bool,
    next_files: list[str],
) -> dict[str, Any]:
    return _core_update_inspection_coverage(
        coverage,
        context,
        timestamp=timestamp,
        inspection_complete=inspection_complete,
        next_files=next_files,
        dependencies=_inspection_coverage_dependencies(),
    )


def _recover_primary_source_byte_limit_skips(
    context: dict[str, Any],
    *,
    file_classification: dict[str, str],
) -> dict[str, Any]:
    skipped_files = context.get("skipped_files", [])
    if not isinstance(skipped_files, list):
        return context

    recovered: list[dict[str, Any]] = []
    retained_skipped: list[dict[str, Any]] = []
    recovered_paths: set[str] = set()
    symbols = list(context.get("symbols", []))
    dependencies = list(context.get("dependencies", []))

    for item in skipped_files:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if (
            not path
            or reason != "source_byte_limit_reached"
            or file_classification.get(path) != "primary"
        ):
            retained_skipped.append(item)
            continue

        source_path = (DASHBOARD_ROOT / path).resolve(strict=False)
        text, read_error = _read_text_file(source_path)
        if text is None:
            retained_skipped.append({
                **item,
                "reason": read_error or "not_text",
            })
            continue

        encoded_len = len(text.encode("utf-8"))
        record = {
            "path": path,
            "bytes": encoded_len,
            "lines": len(text.splitlines()),
            "included_in_prompt": False,
            "prompt_excerpt_chars": 0,
            "evidence_terms": _inspection_evidence_terms(text),
            "class": "primary",
            "inspection_note": "recorded_after_source_byte_limit",
        }
        recovered.append(record)
        recovered_paths.add(path)
        symbols.extend(_extract_symbols(source_path, text))
        dependencies.extend(_extract_dependencies(source_path, text))

    if not recovered:
        return context

    context_bytes = context.get("context_bytes", {})
    if not isinstance(context_bytes, dict):
        context_bytes = {}
    source_bytes = int(context_bytes.get("source_bytes_inspected") or 0)
    source_bytes += sum(int(item.get("bytes") or 0) for item in recovered)

    return {
        **context,
        "inspected_files": [
            *list(context.get("inspected_files", [])),
            *recovered,
        ],
        "remaining_files": [
            path
            for path in context.get("remaining_files", [])
            if path not in recovered_paths
        ],
        "skipped_files": retained_skipped,
        "symbols": symbols,
        "dependencies": dependencies,
        "context_bytes": {
            **context_bytes,
            "source_bytes_inspected": source_bytes,
        },
    }

def _inspection_pass_observations(
    pass_number: int,
    inspected_files: list[Any],
    *,
    files_by_class: dict[str, list[str]],
    file_classification: dict[str, str],
) -> list[dict[str, Any]]:
    class_counts = {
        class_name: len(files_by_class.get(class_name, []))
        for class_name in INSPECTION_CLASSES
    }
    observations: list[dict[str, Any]] = [
        {
            "kind": "pass_observation",
            "summary": f"Read {len(inspected_files)} files in inspection pass {pass_number}.",
            "file_count": len(inspected_files),
        },
        {
            "kind": "pass_observation",
            "summary": (
                "Active queue by class: "
                f"primary={class_counts.get('primary', 0)}, "
                f"secondary={class_counts.get('secondary', 0)}, "
                f"evidence={class_counts.get('evidence', 0)}, "
                f"ignored={class_counts.get('ignored', 0)}."
            ),
            "class_counts": class_counts,
        },
    ]
    for item in inspected_files:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        classification = str(
            item.get("class") or file_classification.get(path) or "unclassified"
        )
        record: dict[str, Any] = {
            "kind": "file_inspected",
            "path": path,
            "class": classification,
            "summary": (
                f"Inspection pass {pass_number} read {classification} file "
                f"{path} ({item.get('lines', '?')} lines)."
            ),
        }
        for key in ("bytes", "lines", "included_in_prompt", "prompt_excerpt_chars"):
            if key in item:
                record[key] = item.get(key)
        evidence_terms = item.get("evidence_terms")
        if isinstance(evidence_terms, list) and evidence_terms:
            record["evidence_terms"] = [
                str(term) for term in evidence_terms[:12] if str(term)
            ]
        observations.append(record)
    return observations

def _inspection_pass_markdown(
    pass_payload: dict[str, Any],
    coverage: dict[str, Any],
) -> str:
    files = pass_payload.get("files_inspected", [])
    symbols = pass_payload.get("symbols", [])
    dependencies = pass_payload.get("dependencies", [])
    skipped = pass_payload.get("skipped_files", [])
    lines = [
        f"# Inspection Pass {int(pass_payload.get('pass', 0)):03d}",
        "",
        f"- Mission: {pass_payload.get('mission_id')}",
        f"- Timestamp: {pass_payload.get('timestamp')}",
        f"- Inspection complete: {pass_payload.get('inspection_complete')}",
        "",
        "## Files Inspected",
    ]
    lines.extend(
        (
            f"- {item.get('path')}"
            f" [{item.get('class', 'unclassified')}]"
            f" ({item.get('bytes')} bytes, {item.get('lines')} lines)"
        )
        for item in files
    )
    if not files:
        lines.append("- none")
    lines.extend(["", "## Observations"])
    observations = pass_payload.get("observations", [])
    if not isinstance(observations, list):
        observations = []
    for item in observations:
        if isinstance(item, dict):
            summary = str(item.get("summary") or item.get("kind") or "").strip()
            if not summary:
                continue
            detail_parts = []
            path = str(item.get("path") or "").strip()
            classification = str(item.get("class") or "").strip()
            if path and path not in summary:
                detail_parts.append(path)
            if classification and classification not in summary:
                detail_parts.append(classification)
            suffix = f" ({', '.join(detail_parts)})" if detail_parts else ""
            lines.append(f"- {summary}{suffix}")
        elif item:
            lines.append(f"- {item}")
    if not observations:
        lines.append("- none")
    lines.extend(["", "## Symbols"])
    lines.extend(
        f"- {item.get('file')}:{item.get('line', '?')} {item.get('kind')} {item.get('name')}"
        for item in symbols[:80]
    )
    if len(symbols) > 80:
        lines.append(f"- truncated: {len(symbols) - 80} additional symbols")
    if not symbols:
        lines.append("- none")
    lines.extend(["", "## Dependencies"])
    lines.extend(
        f"- {item.get('file')}:{item.get('line', '?')} {item.get('kind')} {item.get('target')}"
        for item in dependencies[:80]
    )
    if len(dependencies) > 80:
        lines.append(f"- truncated: {len(dependencies) - 80} additional dependencies")
    if not dependencies:
        lines.append("- none")
    lines.extend(["", "## Skipped"])
    lines.extend(
        f"- {item.get('path')}: {item.get('reason')}"
        for item in skipped
    )
    if not skipped:
        lines.append("- none")
    lines.extend([
        "",
        "## Coverage",
        "```json",
        json.dumps(coverage.get("categories", {}), indent=2),
        "```",
        "",
        "## Unresolved",
    ])
    unresolved = pass_payload.get("unresolved", [])
    lines.extend(f"- {item}" for item in unresolved)
    if not unresolved:
        lines.append("- none")
    lines.extend(["", "## Next Files"])
    next_files = pass_payload.get("next_files", [])
    lines.extend(f"- {path}" for path in next_files)
    if not next_files:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _inspection_next_action(
    mission_id: str,
    inspection_complete: bool,
    *,
    plan_exists: bool = False,
) -> dict[str, Any]:
    if inspection_complete:
        action = "replan" if plan_exists else "plan"
        return {
            "command": mission_command(action, mission_id),
            "authority": "read_only_planning",
        }
    return {
        "command": mission_command("inspect", mission_id),
        "authority": "read_only_inspection",
    }


def _mission_event_files(mission_dir: Path) -> list[Path]:
    events_dir = _mission_events_dir(mission_dir)
    if not events_dir.exists():
        return []
    return sorted(events_dir.glob("*.json"))


def _safe_unit_dir_name(unit_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(unit_id or "").strip())
    return safe.strip(".-") or "unit"


def _unit_status_path(mission_dir: Path, unit_id: str) -> Path:
    return _mission_implementation_dir(mission_dir) / "units" / _safe_unit_dir_name(unit_id) / "status.json"


def _load_unit_status(mission_dir: Path, unit_id: str) -> dict[str, Any]:
    data = _load_json(_unit_status_path(mission_dir, unit_id))
    if not isinstance(data, dict) or "load_error" in data:
        return {"unit_id": unit_id, "status": "pending", "attempt": 0}
    return data

def _implementation_units(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    raw_units = proposal.get("implementation_units", [])
    if not isinstance(raw_units, list):
        return []
    units: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_units, start=1):
        if not isinstance(raw, dict):
            continue
        unit_id = str(raw.get("id") or f"unit-{index:03d}").strip()
        if not unit_id:
            unit_id = f"unit-{index:03d}"
        if unit_id in seen_ids:
            continue
        seen_ids.add(unit_id)
        units.append({"id": unit_id})
    return units


def _manifest_unit_status(manifest: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for item in manifest.get("units", []):
        if isinstance(item, dict) and item.get("id"):
            statuses[str(item["id"])] = str(item.get("status") or "pending")
    return statuses


def _mission_unit_progress(mission_dir: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    units = _implementation_units(proposal) if proposal else []
    manifest = _load_optional_mission_json(_mission_implementation_manifest_path(mission_dir))
    status_by_id = _manifest_unit_status(manifest) if manifest else {}
    unit_records: list[dict[str, Any]] = []
    for unit in units:
        unit_status = _load_unit_status(mission_dir, unit["id"])
        status = str(
            unit_status.get("status")
            or status_by_id.get(unit["id"])
            or "pending"
        )
        unit_records.append({
            "id": unit["id"],
            "status": status,
            "attempt": int(unit_status.get("attempt") or 0),
            "artifact_path": _stable(_unit_status_path(mission_dir, unit["id"])),
        })
    total = len(unit_records)
    complete = sum(1 for item in unit_records if item.get("status") == "complete")
    failed = sum(1 for item in unit_records if item.get("status") == "failed")
    blocked = sum(1 for item in unit_records if item.get("status") == "blocked")
    pending = total - complete - failed - blocked
    return {
        "total": total,
        "complete": complete,
        "failed": failed,
        "blocked": blocked,
        "pending": max(pending, 0),
        "implementation_complete": total > 0 and complete == total and failed == 0,
        "units": unit_records,
    }



def _plan_scope_paths(plan: dict[str, Any]) -> list[str]:
    scope = plan.get("scope", {}) if isinstance(plan, dict) else {}
    if not isinstance(scope, dict):
        scope = {}
    assessment = plan.get("inspection_assessment", {}) if isinstance(plan, dict) else {}
    if not isinstance(assessment, dict):
        assessment = {}
    raw: list[Any] = []
    for key in ("files_requiring_confirmation", "likely_modified_files"):
        value = scope.get(key, [])
        if isinstance(value, list):
            raw.extend(value)
    value = assessment.get("additional_inspection_recommended", [])
    if isinstance(value, list):
        raw.extend(value)
    return _dedupe_manifest_paths(raw)


def _scope_flag_args(paths: list[str]) -> list[str]:
    args: list[str] = []
    for path in paths:
        args.extend(["--scope", shlex.quote(path)])
    return args


def _scope_expansion_next_action(
    mission_id: str,
    plan: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    candidates = _plan_scope_paths(plan)[:8]
    if candidates:
        return {
            "command": mission_command(
                "scope-add",
                mission_id,
                *_scope_flag_args(candidates),
            ),
            "authority": "mission_scope_expansion",
            "reason": (
                "Plan needs more bounded evidence: "
                f"{reason}. Add the proposed dependent files, then inspect again."
            ),
            "scope_candidates": candidates,
        }
    return {
        "command": mission_command("replan", mission_id),
        "authority": "read_only_planning",
        "reason": (
            "Plan still needs more bounded evidence, but no concrete dependent "
            "files were identified. Regenerate the plan to refresh scope hints."
        ),
        "scope_candidates": [],
    }


def _module_dependency_candidates(target: str) -> list[str]:
    raw = str(target or "").strip()
    if not raw:
        return []
    module, _, imported = raw.partition(":")
    module = module.strip()
    if not module.startswith("Agency."):
        return []
    module_path = module.replace(".", "/")
    candidates = [f"{module_path}.py", f"{module_path}/__init__.py"]
    for item in imported.split(","):
        name = item.strip().split(" as ", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            candidates.append(f"{module_path}/{name}.py")
            candidates.append(f"{module_path}/{name}/__init__.py")
    return candidates


def _validate_scope_candidate_paths(raw_candidates: list[Any], current_scope: set[str]) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in raw_candidates:
        rel = _manifest_path_value(raw)
        if rel is None or rel in seen or rel in current_scope:
            continue
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            continue
        path = (DASHBOARD_ROOT / rel_path).resolve(strict=False)
        if not path.exists() or not path.is_file():
            continue
        try:
            normalized = path.relative_to(DASHBOARD_ROOT.resolve()).as_posix()
            validate_engineering_scopes([normalized])
        except ValueError:
            continue
        if normalized in seen or normalized in current_scope:
            continue
        seen.add(normalized)
        candidates.append(normalized)
        if len(candidates) >= 12:
            break
    return candidates


def _planning_scope_expansion_candidates(
    artifacts: dict[str, Any],
    evidence: dict[str, Any],
    model_plan: dict[str, Any] | None = None,
) -> list[str]:
    intent = artifacts.get("intent", {}) if isinstance(artifacts, dict) else {}
    current_scope = {
        str(item.get("relative") or item.get("input") or "").strip()
        for item in intent.get("scopes", [])
        if isinstance(item, dict)
    }
    current_scope.update(
        str(item.get("path") or "").strip()
        for item in evidence.get("files_inspected", [])
        if isinstance(item, dict)
    )
    raw_candidates: list[Any] = []
    if isinstance(model_plan, dict):
        scope = model_plan.get("scope", {})
        if isinstance(scope, dict):
            for key in ("files_requiring_confirmation", "likely_modified_files"):
                value = scope.get(key, [])
                if isinstance(value, list):
                    raw_candidates.extend(value)
        assessment = model_plan.get("inspection_assessment", {})
        if isinstance(assessment, dict):
            value = assessment.get("additional_inspection_recommended", [])
            if isinstance(value, list):
                raw_candidates.extend(value)
    raw_candidates.extend(evidence.get("files_remaining", []))
    for item in evidence.get("observations", []):
        if not isinstance(item, dict) or item.get("kind") != "dependency":
            continue
        raw_candidates.extend(_module_dependency_candidates(str(item.get("target") or "")))
    return _validate_scope_candidate_paths(raw_candidates, current_scope)

def _plan_blocking_unresolved(plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for item in plan.get("unresolved_questions", []):
        if not isinstance(item, dict):
            continue
        if bool(item.get("blocking")):
            question = str(item.get("question") or "").strip()
            blockers.append(question or str(item.get("id") or "blocking unresolved question"))
    return blockers


def _assess_plan_proposal_readiness(plan: dict[str, Any]) -> dict[str, Any]:
    assessment = plan.get("inspection_assessment", {}) if isinstance(plan, dict) else {}
    if not isinstance(assessment, dict):
        assessment = {}
    blockers = _plan_blocking_unresolved(plan) if isinstance(plan, dict) else []
    if not bool(assessment.get("sufficient_for_proposal", False)):
        blockers.insert(0, "inspection_assessment.sufficient_for_proposal is false")
    if blockers:
        return {
            "ready": False,
            "error": "proposal_not_ready",
            "reason": "; ".join(blockers[:4]),
        }
    return {
        "ready": True,
        "reason": "Plan is available for implementation proposal synthesis.",
    }


def _next_action_after_plan(
    mission_id: str,
    plan: dict[str, Any],
    *,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness = _assess_plan_proposal_readiness(plan)
    if readiness.get("ready"):
        return {
            "command": mission_command("propose", mission_id),
            "authority": "proposal_generation",
            "reason": "Architecture plan is complete and ready for proposal generation.",
        }
    state = state or {}
    reason = str(readiness.get("reason") or "proposal readiness is false")
    if state.get("inspection_complete") is False:
        return {
            "command": mission_command("inspect", mission_id),
            "authority": "read_only_inspection",
            "reason": (
                "Plan is not ready for proposal generation: "
                f"{reason}. Additional declared-scope inspection is required."
            ),
        }
    scope_action = _scope_expansion_next_action(mission_id, plan, reason=reason)
    if scope_action.get("scope_candidates"):
        return scope_action
    if not bool(state.get("resourcefulness_complete", False)):
        return {
            "command": mission_command(
                "resourcefulness",
                mission_id,
            ),
            "authority": "bounded_self_diagnosis",
            "reason": (
                "Plan is not ready for proposal generation: "
                f"{reason}. Run bounded reconstruction from existing inspection evidence "
                "before expanding scope."
            ),
        }
    return scope_action


def _mission_next_action(
    mission_dir: Path,
    *,
    state: dict[str, Any],
    plan: dict[str, Any],
    proposal: dict[str, Any],
    review: dict[str, Any],
    unit_progress: dict[str, Any],
    verification: dict[str, Any],
    inspection_passes: list[Path],
) -> dict[str, Any]:
    mission_id_value = mission_dir.name
    if verification.get("result") == "passed":
        return {"command": None, "reason": "Mission completed successfully."}
    if verification:
        return {"command": "Review verification/report.json", "reason": "Final verification did not pass."}
    if unit_progress.get("implementation_complete"):
        return {
            "command": mission_command("verify", mission_id_value),
            "reason": "Implementation is complete and final verification is pending.",
        }
    if review.get("decision") == "approved" and review.get("implementation_authorized") is True:
        return {
            "command": mission_command("implement", mission_id_value),
            "reason": "Approved implementation units remain incomplete.",
        }
    if review.get("decision") in {"rejected", "changes_requested"}:
        return {
            "command": "Review proposal or regenerate.",
            "reason": "Operator review did not approve implementation.",
        }
    if proposal:
        return {
            "command": mission_command("review", mission_id_value, "--approve"),
            "reason": "No approved operator review artifact is recorded.",
        }
    if plan:
        return _next_action_after_plan(mission_id_value, plan, state=state)
    if inspection_passes:
        return {
            "command": mission_command("plan", mission_id_value),
            "reason": "No architecture plan artifact is recorded.",
        }
    return {
        "command": mission_command("inspect", mission_id_value),
        "reason": "No inspection passes are recorded.",
    }


def _mission_artifact_path_map(mission_dir: Path) -> dict[str, str]:
    inspect_dir = _mission_inspect_dir(mission_dir)
    implementation_dir = _mission_implementation_dir(mission_dir)
    verification_dir = _mission_verification_dir(mission_dir)
    return {
        "intent": _stable(_mission_intent_path(mission_dir)),
        "state": _stable(_mission_state_path(mission_dir)),
        "inspect_manifest": _stable(_mission_manifest_path(mission_dir)),
        "inspect_coverage": _stable(_mission_coverage_path(mission_dir)),
        "inspection_passes": str(len(sorted(inspect_dir.glob("pass_*.json")))),
        "resourcefulness": _stable(_mission_resourcefulness_reconstruction_path(mission_dir)),
        "plan": _stable(_mission_plan_json_path(mission_dir)),
        "proposal": _stable(_mission_proposal_json_path(mission_dir)),
        "review": _stable(_mission_review_decision_json_path(mission_dir)),
        "implementation": _stable(_mission_implementation_manifest_path(mission_dir)),
        "verification": _stable(_mission_verification_report_json_path(mission_dir)),
        "verification_evidence_manifest": _stable(_mission_evidence_manifest_path(mission_dir)),
        "verification_evidence": _stable(_mission_verification_evidence_dir(mission_dir)),
        "events": _stable(_mission_events_dir(mission_dir)),
        "implementation_units": _stable(implementation_dir / "units"),
        "verification_support": _stable(verification_dir),
    }

def _mission_file_timestamp(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _mission_timestamps(mission_dir: Path) -> dict[str, str | None]:
    inspect_passes = sorted(_mission_inspect_dir(mission_dir).glob("pass_*.json"))
    event_files = _mission_event_files(mission_dir)
    return {
        "created": _mission_file_timestamp(_mission_intent_path(mission_dir)),
        "last_state_update": _mission_file_timestamp(_mission_state_path(mission_dir)),
        "last_inspection_pass": _mission_file_timestamp(inspect_passes[-1]) if inspect_passes else None,
        "planned": _mission_file_timestamp(_mission_plan_json_path(mission_dir)),
        "proposed": _mission_file_timestamp(_mission_proposal_json_path(mission_dir)),
        "reviewed": _mission_file_timestamp(_mission_review_decision_json_path(mission_dir)),
        "implemented": _mission_file_timestamp(_mission_implementation_manifest_path(mission_dir)),
        "verified": _mission_file_timestamp(_mission_verification_report_json_path(mission_dir)),
        "last_event": _mission_file_timestamp(event_files[-1]) if event_files else None,
    }


def mission_reconstruction(mission_dir: Path) -> dict[str, Any]:
    intent = _load_optional_mission_json(_mission_intent_path(mission_dir))
    state = _load_optional_mission_json(_mission_state_path(mission_dir))
    plan = _load_optional_mission_json(_mission_plan_json_path(mission_dir))
    proposal = _load_optional_mission_json(_mission_proposal_json_path(mission_dir))
    review = _load_optional_mission_json(_mission_review_decision_json_path(mission_dir))
    verification = _load_optional_mission_json(_mission_verification_report_json_path(mission_dir))
    inspection_passes = sorted(_mission_inspect_dir(mission_dir).glob("pass_*.json"))
    unit_progress = _mission_unit_progress(mission_dir, proposal)

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

    next_action = _mission_next_action(
        mission_dir,
        state=state,
        plan=plan,
        proposal=proposal if proposed else {},
        review=review,
        unit_progress=unit_progress,
        verification=verification,
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
        readiness = _assess_plan_proposal_readiness(plan)
        phase = "planned"
        status = "waiting_proposal" if readiness.get("ready") else "proposal_not_ready"
    elif inspected:
        phase = "inspection"
        status = "waiting_plan"
    else:
        phase = str(state.get("phase") or "created")
        status = str(state.get("status") or "ready_for_inspection")

    event_files = _mission_event_files(mission_dir)
    return {
        "mission_id": mission_dir.name,
        "mission_path": _stable(mission_dir),
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
            "complete": bool(verification and verification.get("mission_complete") is True),
        },
        "inspection": {
            "passes": len(inspection_passes),
            "latest_pass": _stable(inspection_passes[-1]) if inspection_passes else None,
        },
        "unit_progress": unit_progress,
        "verification": {
            "exists": verified,
            "result": verification.get("result"),
            "mission_complete": verification.get("mission_complete"),
            "report": _stable(_mission_verification_report_json_path(mission_dir)),
        },
        "next_action": next_action,
        "artifacts": _mission_artifact_path_map(mission_dir),
        "timestamps": _mission_timestamps(mission_dir),
        "events": {
            "count": len(event_files),
            "latest": _stable(event_files[-1]) if event_files else None,
        },
        "state_phase": state.get("phase"),
        "state_status": state.get("status"),
    }


def mission_status(mission: str, *, root: Path | None = None) -> dict[str, Any]:
    try:
        mission_dir = resolve_mission_dir(mission, root=root)
        intent_data = _load_required_mission_json(_mission_intent_path(mission_dir))
        state_data = _load_required_mission_json(_mission_state_path(mission_dir))
    except ValueError as exc:
        raise MissionOperationError({
            "ok": False,
            "status": "mission_status_failed",
            "reason": str(exc),
            "authority": "read_only_mission_status",
        }, 2) from exc

    inspect_dir = _mission_inspect_dir(mission_dir)
    pass_files = sorted(inspect_dir.glob("pass_*.json"))
    return {
        "ok": True,
        "status": "mission_status",
        "mission_id": mission_dir.name,
        "mission_path": _stable(mission_dir),
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
            "intent": _stable(_mission_intent_path(mission_dir)),
            "state": _stable(_mission_state_path(mission_dir)),
            "manifest": _stable(inspect_dir / "manifest.json"),
            "coverage": _stable(inspect_dir / "coverage.json"),
            "operator_notes": _stable(mission_dir / "review" / "operator_notes.md"),
            "inspection_passes": [_stable(pass_path) for pass_path in pass_files],
        },
        "authority": "read_only_mission_status",
    }



def plan_mission(mission: str, *, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> dict[str, Any]:
    return _run_emitting_operation(
        lambda emit: _mission_planning.run_mission_plan(
            _planning_dependencies(root=root, refresh_pinboard=refresh_pinboard, emit=emit),
            mission,
        ),
        "plan_complete",
    )


def replan_mission(mission: str, *, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> dict[str, Any]:
    return _run_emitting_operation(
        lambda emit: _mission_planning.run_mission_replan(
            _planning_dependencies(root=root, refresh_pinboard=refresh_pinboard, emit=emit),
            mission,
        ),
        "replan_complete",
    )



def resourcefulness_mission(mission: str, *, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    emit = _emit_to(outputs)
    planning_deps = _planning_dependencies(root=root, refresh_pinboard=refresh_pinboard, emit=emit)
    try:
        mission_dir = resolve_mission_dir(mission, root=root)
    except ValueError as exc:
        return _operation_payload(outputs, _mission_planning._planning_failure(planning_deps, "mission_not_found", str(mission), str(exc), exit_code=2), "mission_not_found")

    mission_id_value = mission_dir.name
    plan_json_path = _mission_plan_json_path(mission_dir)
    plan_md_path = _mission_planning._mission_plan_md_path(planning_deps, mission_dir)
    if not plan_json_path.exists() and not plan_md_path.exists():
        return _operation_payload(outputs, _mission_planning._planning_failure(
            planning_deps,
            "resourcefulness_plan_required",
            mission_id_value,
            "Resourcefulness requires an existing plan artifact to diagnose.",
            next_action={"command": mission_command("plan", mission_id_value), "authority": "read_only_planning"},
            exit_code=1,
        ), "resourcefulness_plan_required")

    proposal_json_path = _mission_proposal_json_path(mission_dir)
    proposal_md_path = _mission_proposal_md_path(mission_dir)
    if proposal_json_path.exists() or proposal_md_path.exists():
        raise MissionOperationError({
            "ok": False,
            "status": "resourcefulness_blocked_proposal_exists",
            "error": "resourcefulness_blocked_proposal_exists",
            "mission_id": mission_id_value,
            "reason": "Resourcefulness is only permitted before proposal artifacts exist.",
            "proposal_path": _stable(proposal_json_path),
            "markdown_path": _stable(proposal_md_path),
            "authority": "bounded_self_diagnosis",
            "source_files_modified": False,
        }, 1)

    try:
        state_data = _load_required_mission_json(_mission_state_path(mission_dir))
        plan = _load_plan(mission_dir)
    except ValueError as exc:
        return _operation_payload(outputs, _mission_planning._planning_failure(planning_deps, "invalid_mission_artifact", mission_id_value, str(exc), exit_code=2), "invalid_mission_artifact")

    readiness = _assess_plan_proposal_readiness(plan)
    if readiness.get("ready"):
        return {
            "ok": True,
            "status": "resourcefulness_not_required",
            "mission_id": mission_id_value,
            "reason": "The current plan is already ready for proposal generation.",
            "next_action": _next_action_after_plan(mission_id_value, plan, state=state_data),
            "authority": "bounded_self_diagnosis",
            "source_files_modified": False,
        }

    reconstruction_path = _mission_resourcefulness_reconstruction_path(mission_dir)
    if bool(state_data.get("resourcefulness_complete", False)):
        resourceful_state = {**state_data, "resourcefulness_complete": True}
        return {
            "ok": True,
            "status": "resourcefulness_already_complete",
            "mission_id": mission_id_value,
            "reason": "Bounded Resourcefulness has already been applied for this mission.",
            "artifacts": {"resourcefulness_reconstruction": _stable(reconstruction_path)} if reconstruction_path.exists() else {},
            "next_action": _next_action_after_plan(mission_id_value, plan, state=resourceful_state),
            "authority": "bounded_self_diagnosis",
            "source_files_modified": False,
        }

    try:
        artifacts = _mission_planning._load_mission_artifacts(planning_deps, mission_dir)
    except ValueError as exc:
        return _operation_payload(outputs, _mission_planning._planning_failure(planning_deps, "invalid_mission_artifact", mission_id_value, str(exc), exit_code=2), "invalid_mission_artifact")
    evidence = _mission_planning._normalize_inspection_evidence(planning_deps, artifacts)
    planning_readiness = _mission_planning._assess_planning_readiness(planning_deps, artifacts, evidence)
    if not planning_readiness.get("ready"):
        return _operation_payload(outputs, _mission_planning._planning_failure(
            planning_deps,
            "resourcefulness_not_ready",
            mission_id_value,
            str(planning_readiness.get("reason") or "Inspection evidence is insufficient."),
            next_action={"command": mission_command("inspect", mission_id_value), "authority": "read_only_inspection"},
            exit_code=1,
        ), "resourcefulness_not_ready")

    created_at = _now()
    context = ResourcefulnessContext(
        mission_id=mission_id_value,
        plan=plan,
        artifacts=artifacts,
        evidence=evidence,
        created_at=created_at,
        schema_version=MISSION_SCHEMA_VERSION,
        coverage_categories=list(MISSION_COVERAGE_CATEGORIES),
        proposal_readiness=readiness,
    )
    result = default_planner().run(context)
    if not result.artifacts:
        scope_action = _scope_expansion_next_action(
            mission_id_value,
            plan,
            reason=str(readiness.get("reason") or result.reason),
        )
        return {
            "ok": True,
            "status": result.status,
            "mission_id": mission_id_value,
            "reason": result.reason,
            "resourcefulness": result.summary(),
            "next_action": scope_action,
            "authority": "bounded_self_diagnosis",
            "source_files_modified": False,
        }

    artifact_paths: dict[str, str] = {}
    artifact_targets: list[tuple[Path, dict[str, Any]]] = []
    for artifact_name, artifact_payload in result.artifacts.items():
        if not re.fullmatch(r"[a-z0-9_]+", str(artifact_name)) or not isinstance(artifact_payload, dict):
            return _operation_payload(outputs, _mission_planning._planning_failure(planning_deps, "resourcefulness_invalid_result", mission_id_value, "Resourcefulness returned an invalid artifact.", exit_code=1), "resourcefulness_invalid_result")
        artifact_path = _mission_knowledge_dir(mission_dir) / f"{artifact_name}.json"
        artifact_paths[str(artifact_name)] = _stable(artifact_path)
        artifact_targets.append((artifact_path, artifact_payload))
    result_summary = result.summary(artifact_paths)

    try:
        _mission_knowledge_dir(mission_dir).mkdir(parents=True, exist_ok=True)
        for artifact_path, artifact_payload in artifact_targets:
            _atomic_json(artifact_path, artifact_payload)
        state_payload = {
            **state_data,
            "schema_version": state_data.get("schema_version", MISSION_SCHEMA_VERSION),
            "mission_id": mission_id_value,
            "updated_at": created_at,
            "resourcefulness_complete": True,
            "resourcefulness": {
                "strategy": result.strategy,
                "status": result.status,
                "reason": result.reason,
                "confidence": result.confidence,
                "next_recommendation": result.next_recommendation,
                "artifacts": artifact_paths,
                "path": next(iter(artifact_paths.values()), None),
                "created_at": created_at,
                "schema_version": MISSION_SCHEMA_VERSION,
            },
            "next_action": {
                "command": mission_command("replan", mission_id_value),
                "authority": "read_only_planning",
                "reason": "Resourcefulness result is recorded; regenerate the plan from existing inspection evidence.",
            },
        }
        _atomic_json(_mission_state_path(mission_dir), state_payload)
    except Exception as exc:
        return _operation_payload(outputs, _mission_planning._planning_failure(planning_deps, "resourcefulness_write_failed", mission_id_value, f"{type(exc).__name__}: {exc}", exit_code=1), "resourcefulness_write_failed")

    observation = {
        "command": "mission resourcefulness",
        "status": result.status,
        "mission_id": mission_id_value,
        "strategy": result.strategy,
        "reason": result.reason,
        "artifacts": artifact_paths,
        "source_files_modified": False,
        "authority": "bounded_self_diagnosis",
    }
    append_mission_event(mission_dir, "resourcefulness", observation)
    _refresh_callback(refresh_pinboard)(mission=str(artifacts["intent"].get("intent") or mission_id_value), last_observation=observation, next_action=state_payload["next_action"])

    return _operation_payload(outputs, _mission_planning.execute_mission_planning(
        planning_deps,
        mission_dir,
        command_label="mission resourcefulness",
        result_status="resourcefulness_replan_complete",
        extra_payload={"resourcefulness": result_summary},
    ), "resourcefulness_replan_complete")

def propose_mission(mission: str, *, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> dict[str, Any]:
    return _run_emitting_operation(
        lambda emit: _proposal_generation.run_mission_propose(
            _proposal_dependencies(root=root, refresh_pinboard=refresh_pinboard, emit=emit),
            mission,
        ),
        "proposal_complete",
    )


def review_mission(mission: str, *, approve: bool = False, reject: bool = False, request_changes: bool = False, note: str = "", root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> dict[str, Any]:
    args = argparse.Namespace(mission=mission, approve=approve, reject=reject, request_changes=request_changes, note=note)
    return _run_emitting_operation(
        lambda emit: _core_run_mission_review(
            _review_execution_dependencies(root=root, refresh_pinboard=refresh_pinboard, emit=emit),
            args,
        ),
        "review_recorded",
    )


def implement_mission(mission: str, *, dry_run: bool = False, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> dict[str, Any]:
    return _run_printing_operation(
        lambda: _implementation_execution.run_mission_implement(
            _implementation_execution_dependencies(root=root, refresh_pinboard=refresh_pinboard),
            mission,
            dry_run=dry_run,
        ),
        "implementation_complete",
    )


def verify_mission(mission: str, *, root: Path | None = None, refresh_pinboard: Callable[..., Any] | None = None) -> dict[str, Any]:
    return _run_printing_operation(
        lambda: _verification_execution.run_mission_verify(
            _verification_execution_dependencies(root=root, refresh_pinboard=refresh_pinboard),
            mission,
        ),
        "verification_complete",
    )


def resume_mission(mission: str, *, root: Path | None = None) -> dict[str, Any]:
    try:
        mission_dir = resolve_mission_dir(mission, root=root)
        return mission_reconstruction(mission_dir)
    except ValueError as exc:
        raise MissionOperationError({
            "ok": False,
            "status": "mission_resume_failed",
            "reason": str(exc),
            "authority": "read_only_mission_reconstruction",
        }, 2) from exc

def inspect_mission(
    mission: str,
    *,
    root: Path | None = None,
    refresh_pinboard: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    try:
        mission_dir = resolve_mission_dir(mission, root=root)
        intent_data = _load_required_mission_json(_mission_intent_path(mission_dir))
        state_data = _load_required_mission_json(_mission_state_path(mission_dir))
        manifest_path = _mission_manifest_path(mission_dir)
        coverage_path = _mission_coverage_path(mission_dir)
        manifest_data = _load_required_mission_json(manifest_path)
        coverage_data = _load_required_mission_json(coverage_path)
        scopes = _mission_scopes_from_intent(intent_data)
    except ValueError as exc:
        raise MissionOperationError({
            "ok": False,
            "status": "mission_inspect_failed",
            "reason": str(exc),
            "authority": "read_only_inspection",
            "source_files_modified": False,
        }, 2) from exc

    mission_id_value = mission_dir.name
    timestamp = _now()
    inspect_dir = _mission_inspect_dir(mission_dir)
    inspect_dir.mkdir(parents=True, exist_ok=True)

    configured_budgets = state_data.get("budgets", {})
    if not isinstance(configured_budgets, dict):
        configured_budgets = {}
    budgets = {
        **DEFAULT_MISSION_BUDGETS,
        **configured_budgets,
    }
    int(budgets["max_inspection_passes"])
    max_files_per_pass = int(budgets["max_files_per_pass"])
    int(budgets["max_total_files"])
    int(state_data.get("inspection_passes", 0))

    pass_number = _next_inspection_pass_number(inspect_dir)
    pass_json_path = inspect_dir / f"pass_{pass_number:03d}.json"
    pass_md_path = inspect_dir / f"pass_{pass_number:03d}.md"
    if pass_json_path.exists() or pass_md_path.exists():
        raise MissionOperationError({
            "ok": False,
            "status": "mission_inspect_failed",
            "reason": f"inspection pass artifact already exists: pass_{pass_number:03d}",
            "authority": "read_only_inspection",
            "source_files_modified": False,
        }, 1)

    discovered_existing = _dedupe_manifest_paths(
        manifest_data.get("files_discovered", [])
    )
    inspected_existing = _dedupe_manifest_paths(
        manifest_data.get("files_inspected", [])
    )
    discovered_files = discovered_existing or _discover_mission_files(scopes)
    intent_requests = _mission_intent_requests(
        str(intent_data.get("intent") or "")
    )
    referenced_paths = _mission_referenced_paths(mission_dir)
    files_by_class, ignored_files = _classify_mission_files(
        discovered_files,
        intent_requests=intent_requests,
        referenced_paths=referenced_paths,
    )
    file_classification = _classification_map(files_by_class)
    active_queue = _active_inspection_queue(
        files_by_class,
        inspected_files=set(inspected_existing),
        intent_requests=intent_requests,
        coverage=coverage_data,
    )

    try:
        context = _build_inspection_context(
            str(intent_data.get("intent") or ""),
            scopes,
            candidate_paths=active_queue,
            previously_inspected=set(inspected_existing),
            file_classification=file_classification,
            max_files=max_files_per_pass,
            stop_at_file_limit=True,
        )
        context = _recover_primary_source_byte_limit_skips(
            context,
            file_classification=file_classification,
        )
    except Exception as exc:
        raise MissionOperationError({
            "ok": False,
            "status": "mission_inspect_failed",
            "reason": f"{type(exc).__name__}: {exc}",
            "authority": "read_only_inspection",
            "source_files_modified": False,
        }, 1) from exc

    inspected_now = [
        item["path"]
        for item in context.get("inspected_files", [])
    ]
    inspected_files = _dedupe_manifest_paths(
        [*inspected_existing, *inspected_now]
    )
    skipped_files = _merge_skipped_files(
        manifest_data.get("skipped_files", []),
        [*ignored_files, *context.get("skipped_files", [])],
    )
    remaining_files = _dedupe_manifest_paths(context.get("remaining_files", []))
    inspection_complete = len(remaining_files) == 0
    next_files = remaining_files[:max_files_per_pass]

    observations = _inspection_pass_observations(
        pass_number,
        context.get("inspected_files", []),
        files_by_class=files_by_class,
        file_classification=file_classification,
    )
    unresolved = []
    if not inspection_complete:
        unresolved.append(
            f"{len(remaining_files)} discovered files remain uninspected."
        )
    unresolved.extend(
        f"Skipped {item.get('path')}: {item.get('reason')}"
        for item in context.get("skipped_files", [])
        if str(item.get("reason") or "").startswith(("read_error", "decode_error"))
    )

    pass_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": mission_id_value,
        "pass": pass_number,
        "timestamp": timestamp,
        "files_inspected": context.get("inspected_files", []),
        "file_classification": {
            item["path"]: file_classification.get(item["path"], "unknown")
            for item in context.get("inspected_files", [])
        },
        "symbols": context.get("symbols", []),
        "dependencies": context.get("dependencies", []),
        "observations": observations,
        "unresolved": unresolved,
        "next_files": next_files,
        "inspection_complete": inspection_complete,
        "skipped_files": context.get("skipped_files", []),
        "operational_context": context.get("operational_context", []),
        "context_limits": {
            **context.get("context_limits", {}),
            "max_files_per_pass": max_files_per_pass,
            "inspection_generation_limit": INSPECTION_MAX_NEW_TOKENS,
        },
        "context_bytes": context.get("context_bytes", {}),
        "source_files_modified": False,
        "authority": "read_only_inspection",
    }

    coverage_payload = _update_inspection_coverage(
        coverage_data,
        context,
        timestamp=timestamp,
        inspection_complete=inspection_complete,
        next_files=next_files,
    )
    manifest_payload = {
        **manifest_data,
        "schema_version": manifest_data.get("schema_version", MISSION_SCHEMA_VERSION),
        "mission_id": mission_id_value,
        "updated_at": timestamp,
        "files_discovered": discovered_files,
        "files_by_class": files_by_class,
        "files_inspected": inspected_files,
        "files_remaining": remaining_files,
        "skipped_files": skipped_files,
        "authority": "inspection_inventory_only",
    }
    next_action = _inspection_next_action(
        mission_id_value,
        inspection_complete,
        plan_exists=_mission_plan_json_path(mission_dir).exists(),
    )
    state_unresolved = [
        item for item in [
            None if inspection_complete else (
                f"Inspection remains incomplete: {len(remaining_files)} files remain."
            ),
            "Architecture plan has not been generated.",
            "No implementation proposal exists.",
        ]
        if item
    ]
    state_payload = {
        **state_data,
        "schema_version": state_data.get("schema_version", MISSION_SCHEMA_VERSION),
        "mission_id": mission_id_value,
        "updated_at": timestamp,
        "phase": "inspection_complete" if inspection_complete else "inspection",
        "status": "ready_for_planning" if inspection_complete else "inspection_in_progress",
        "inspection_complete": inspection_complete,
        "inspection_passes": int(state_data.get("inspection_passes", 0)) + 1,
        "next_action": next_action,
        "blocked_reason": None,
        "unresolved": state_unresolved,
    }

    _atomic_json(pass_json_path, pass_payload)
    _atomic_text(pass_md_path, _inspection_pass_markdown(pass_payload, coverage_payload))
    _atomic_json(manifest_path, manifest_payload)
    _atomic_json(coverage_path, coverage_payload)
    _atomic_json(_mission_state_path(mission_dir), state_payload)

    observation = {
        "command": "mission inspect",
        "status": "inspection_complete" if inspection_complete else "inspection_pass_recorded",
        "mission_id": mission_id_value,
        "pass": pass_number,
        "files_inspected": inspected_now,
        "files_remaining": len(remaining_files),
        "inspection_complete": inspection_complete,
        "source_files_modified": False,
        "authority": "read_only_inspection",
    }
    append_mission_event(mission_dir, "inspected", observation)
    if refresh_pinboard is not None:
        refresh_pinboard(
            mission=str(intent_data.get("intent") or mission_id_value),
            last_observation=observation,
            next_action=next_action,
        )

    return {
        "ok": True,
        "status": observation["status"],
        "mission_id": mission_id_value,
        "pass": pass_number,
        "files_inspected": inspected_now,
        "files_remaining": len(remaining_files),
        "inspection_complete": inspection_complete,
        "artifacts": {
            "pass_json": _stable(pass_json_path),
            "pass_markdown": _stable(pass_md_path),
            "manifest": _stable(manifest_path),
            "coverage": _stable(coverage_path),
            "state": _stable(_mission_state_path(mission_dir)),
        },
        "next_action": next_action,
        "source_files_modified": False,
        "authority": "read_only_inspection",
    }


def add_mission_scope(
    mission: str,
    scopes: list[str],
    *,
    root: Path | None = None,
    refresh_pinboard: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    try:
        mission_dir = resolve_mission_dir(mission, root=root)
        intent_data = _load_required_mission_json(_mission_intent_path(mission_dir))
        state_data = _load_required_mission_json(_mission_state_path(mission_dir))
        manifest_path = _mission_manifest_path(mission_dir)
        coverage_path = _mission_coverage_path(mission_dir)
        manifest_data = _load_required_mission_json(manifest_path)
        coverage_data = _load_required_mission_json(coverage_path)
        validated_scopes = validate_engineering_scopes(list(scopes or []))
    except ValueError as exc:
        raise MissionOperationError({
            "ok": False,
            "status": "mission_scope_add_failed",
            "reason": str(exc),
            "authority": "mission_scope_expansion",
            "source_files_modified": False,
        }, 2) from exc

    mission_id_value = mission_dir.name
    existing_scope_records = [
        item for item in intent_data.get("scopes", [])
        if isinstance(item, dict)
    ]
    existing_scopes = {
        str(item.get("relative") or item.get("input") or "").strip()
        for item in existing_scope_records
    }
    new_scope_records = [
        {
            "input": scope["input"],
            "relative": scope["relative"],
            "resolved": scope["resolved"],
            "allowed_root": scope["allowed_root"],
            "kind": scope["kind"],
        }
        for scope in validated_scopes
        if scope["relative"] not in existing_scopes
    ]
    next_action = {
        "command": mission_command("inspect", mission_id_value),
        "authority": "read_only_inspection",
        "reason": "Inspect the expanded mission scope.",
    }
    if not new_scope_records:
        return {
            "ok": True,
            "status": "mission_scope_unchanged",
            "mission_id": mission_id_value,
            "reason": "All requested scope paths were already declared.",
            "next_action": next_action,
            "source_files_modified": False,
            "authority": "mission_scope_expansion",
        }

    timestamp = _now()
    all_scope_records = [*existing_scope_records, *new_scope_records]
    discovered_existing = _dedupe_manifest_paths(manifest_data.get("files_discovered", []))
    inspected_files = _dedupe_manifest_paths(manifest_data.get("files_inspected", []))
    newly_discovered = _discover_mission_files(new_scope_records)
    files_discovered = _dedupe_manifest_paths([*discovered_existing, *newly_discovered])
    remaining_existing = _dedupe_manifest_paths(manifest_data.get("files_remaining", []))
    files_remaining = _dedupe_manifest_paths([
        *remaining_existing,
        *(path for path in newly_discovered if path not in inspected_files),
    ])
    budgets = state_data.get("budgets", {})
    if not isinstance(budgets, dict):
        budgets = {}
    max_files_per_pass = int(budgets.get("max_files_per_pass", DEFAULT_MISSION_BUDGETS["max_files_per_pass"]))

    intent_payload = {**intent_data, "scopes": all_scope_records}
    manifest_payload = {
        **manifest_data,
        "schema_version": manifest_data.get("schema_version", MISSION_SCHEMA_VERSION),
        "mission_id": mission_id_value,
        "updated_at": timestamp,
        "declared_scopes": [item["relative"] for item in all_scope_records],
        "files_discovered": files_discovered,
        "files_remaining": files_remaining,
        "authority": "inspection_inventory_only",
    }
    coverage_payload = {
        **coverage_data,
        "schema_version": coverage_data.get("schema_version", MISSION_SCHEMA_VERSION),
        "mission_id": mission_id_value,
        "updated_at": timestamp,
        "inspection_complete": False if files_remaining else bool(coverage_data.get("inspection_complete", False)),
        "next_inspection": files_remaining[:max_files_per_pass],
        "authority": "inspection_coverage_not_capability",
    }
    unresolved = [
        item for item in state_data.get("unresolved", [])
        if str(item) != "No implementation proposal exists."
    ]
    scope_note = f"Mission scope expanded with {len(new_scope_records)} path(s); inspection must run again."
    if scope_note not in unresolved:
        unresolved.insert(0, scope_note)
    if "No implementation proposal exists." not in unresolved:
        unresolved.append("No implementation proposal exists.")
    state_payload = {
        **state_data,
        "schema_version": state_data.get("schema_version", MISSION_SCHEMA_VERSION),
        "mission_id": mission_id_value,
        "updated_at": timestamp,
        "phase": "inspection",
        "status": "scope_expanded_ready_for_inspection",
        "inspection_complete": False if files_remaining else bool(state_data.get("inspection_complete", False)),
        "planning_complete": False,
        "resourcefulness_complete": False,
        "next_action": next_action,
        "blocked_reason": None,
        "unresolved": unresolved,
    }

    _atomic_json(_mission_intent_path(mission_dir), intent_payload)
    _atomic_json(manifest_path, manifest_payload)
    _atomic_json(coverage_path, coverage_payload)
    _atomic_json(_mission_state_path(mission_dir), state_payload)

    observation = {
        "command": "mission scope-add",
        "status": "mission_scope_expanded",
        "mission_id": mission_id_value,
        "scopes_added": [item["relative"] for item in new_scope_records],
        "files_remaining": len(files_remaining),
        "source_files_modified": False,
        "authority": "mission_scope_expansion",
    }
    append_mission_event(mission_dir, "scope_expanded", observation)
    if refresh_pinboard is not None:
        refresh_pinboard(
            mission=str(intent_data.get("intent") or mission_id_value),
            last_observation=observation,
            next_action=next_action,
        )

    return {
        "ok": True,
        "status": "mission_scope_expanded",
        "mission_id": mission_id_value,
        "scopes_added": [item["relative"] for item in new_scope_records],
        "files_discovered": newly_discovered,
        "files_remaining": len(files_remaining),
        "next_action": next_action,
        "source_files_modified": False,
        "authority": "mission_scope_expansion",
    }

def create_mission(
    intent: str,
    scopes: list[str],
    *,
    root: Path | None = None,
    required_context_files: list[Path] | None = None,
    refresh_pinboard: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    blockers = agency_blocks_dependent_operations()
    if blockers:
        raise MissionOperationError({
            "ok": False,
            "status": "blocked_by_audit",
            "unresolved": blockers,
            "authority": "mission_creation_only",
        }, 1)

    try:
        validated_scopes = validate_engineering_scopes(list(scopes or []))
    except ValueError as exc:
        raise MissionOperationError({
            "ok": False,
            "status": "invalid_scope",
            "reason": str(exc),
            "authority": "mission_creation_only",
        }, 2) from exc

    clean_intent = str(intent).strip()
    if not clean_intent:
        raise MissionOperationError({
            "ok": False,
            "status": "invalid_intent",
            "reason": "intent must not be empty",
            "authority": "mission_creation_only",
        }, 2)

    created_at = _now()
    mission_root = _missions_root(root)
    new_mission_id = mission_id(
        clean_intent,
        validated_scopes,
        created_at,
        root=mission_root,
    )
    mission_dir = mission_root / new_mission_id
    if mission_dir.exists():
        raise MissionOperationError({
            "ok": False,
            "status": "mission_collision",
            "mission_id": new_mission_id,
            "authority": "mission_creation_only",
        }, 1)

    inspect_dir = mission_dir / "inspect"
    plan_dir = mission_dir / "plan"
    proposals_dir = mission_dir / "proposals"
    review_dir = mission_dir / "review"
    for directory in (inspect_dir, plan_dir, proposals_dir, review_dir):
        directory.mkdir(parents=True, exist_ok=False)

    scope_records = [
        {
            "input": scope["input"],
            "relative": scope["relative"],
            "resolved": scope["resolved"],
            "allowed_root": scope["allowed_root"],
            "kind": scope["kind"],
        }
        for scope in validated_scopes
    ]
    context_files = required_context_files or REQUIRED_CONTEXT_FILES
    intent_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": new_mission_id,
        "created_at": created_at,
        "intent": clean_intent,
        "scopes": scope_records,
        "authority": "read_only_inspection_and_proposal_only",
        "source_mutation_allowed": False,
        "required_context": [_stable(path) for path in context_files],
    }
    state_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": new_mission_id,
        "updated_at": created_at,
        "phase": "created",
        "status": "ready_for_inspection",
        "inspection_complete": False,
        "inspection_passes": 0,
        "planning_complete": False,
        "proposals_complete": False,
        "implementation_enabled": False,
        "next_action": {
            "command": mission_command(
                "inspect",
                new_mission_id,
            ),
            "authority": "read_only_inspection",
        },
        "blocked_reason": None,
        "unresolved": [
            "Inspection has not started.",
            "Architecture plan has not been generated.",
            "No implementation proposal exists.",
        ],
        "budgets": dict(DEFAULT_MISSION_BUDGETS),
    }
    manifest_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": new_mission_id,
        "generated_at": created_at,
        "declared_scopes": [scope["relative"] for scope in validated_scopes],
        "files_discovered": [],
        "files_inspected": [],
        "files_remaining": [],
        "skipped_files": [],
        "authority": "inspection_inventory_only",
    }
    coverage_payload = {
        "schema_version": MISSION_SCHEMA_VERSION,
        "mission_id": new_mission_id,
        "updated_at": created_at,
        "inspection_complete": False,
        "categories": {category: "not_started" for category in MISSION_COVERAGE_CATEGORIES},
        "unresolved": ["No inspection pass has run."],
        "next_inspection": [],
        "authority": "inspection_coverage_not_capability",
    }

    _atomic_json(_mission_intent_path(mission_dir), intent_payload)
    _atomic_json(_mission_state_path(mission_dir), state_payload)
    _atomic_json(_mission_manifest_path(mission_dir), manifest_payload)
    _atomic_json(_mission_coverage_path(mission_dir), coverage_payload)
    _atomic_text(
        review_dir / "operator_notes.md",
        "# Operator Notes\n\nNo operator review has been recorded.\n",
    )

    observation = {
        "command": "mission create",
        "status": "mission_created",
        "mission_id": new_mission_id,
        "intent": clean_intent,
        "scopes": [scope["relative"] for scope in validated_scopes],
        "mission_path": _stable(mission_dir),
        "source_files_modified": False,
        "authority": "mission_creation_only",
    }
    append_mission_event(mission_dir, "created", observation)

    if refresh_pinboard is not None:
        refresh_pinboard(
            mission=clean_intent,
            last_observation=observation,
            next_action=state_payload["next_action"],
        )

    return {
        "ok": True,
        "status": "mission_created",
        "mission_id": new_mission_id,
        "mission_path": _stable(mission_dir),
        "intent_path": _stable(_mission_intent_path(mission_dir)),
        "state_path": _stable(_mission_state_path(mission_dir)),
        "next_action": state_payload["next_action"],
        "source_files_modified": False,
        "authority": "mission_creation_only",
    }


def list_missions(*, root: Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missions_root = _missions_root(root)
    if not missions_root.exists():
        return rows
    for mission_dir in sorted(
        (path for path in missions_root.iterdir() if path.is_dir()),
        key=mission_list_sort_key,
        reverse=True,
    ):
        try:
            rows.append(mission_reconstruction(mission_dir))
        except Exception:
            rows.append({
                "mission_id": mission_dir.name,
                "phase": "unreadable",
                "status": "invalid_artifacts",
                "unit_progress": {"total": 0, "complete": 0},
            })
    return rows


def show_mission(mission: str, *, root: Path | None = None) -> dict[str, Any]:
    try:
        mission_dir = resolve_mission_dir(mission, root=root)
        return mission_reconstruction(mission_dir)
    except ValueError as exc:
        raise MissionOperationError({
            "ok": False,
            "status": "mission_show_failed",
            "reason": str(exc),
            "authority": "read_only_mission_reconstruction",
        }, 2) from exc
