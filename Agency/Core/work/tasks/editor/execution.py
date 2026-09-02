from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.work.tasks.editor.contracts import (
    EditorResult,
    EditorTask,
    ACTIVE_EDITOR_NAME,
    PatchAuthorization,
    editor_task_from_mapping,
    now_utc,
    patch_authorization_from_mapping,
    repo_relative,
    resolve_repo_path,
    validate_editor_task,
)
from Agency.Core.work.tasks.editor import persistence
from Agency.Core.repository.git_authority import apply_patch as git_apply_patch
from Agency.Core.repository.git_authority import check_patch as git_check_patch
from Agency.Core.repository.git_authority import diff_check as git_diff_check
from Agency.Core.repository.git_authority import get_blob_oid, repository_ref, status_short as git_status_short
from Agency.Core.repository.git_authority.contracts import GitAuthorityError, GitObservation
from Agency.Core.foundation.paths import DASHBOARD_ROOT, stable_path
from Agency.Core.repository.context.builder import (
    DEFAULT_LIMITS,
    EvidenceBundle,
    RepositoryContextRequest,
    build_repository_context,
)


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_observation_result(observation: GitObservation) -> dict[str, Any]:
    data = observation.to_dict()
    data["command"] = " ".join(observation.git_command)
    data["returncode"] = observation.git_exit_code
    return data


def _jsonable_evidence(bundle: EvidenceBundle | None) -> dict[str, Any] | None:
    return bundle.to_dict()["EvidenceBundle"] if bundle else None


def _limits_reached(bundle: EvidenceBundle | None) -> list[str]:
    if bundle is None:
        return []
    return [key for key, value in bundle.limits.get("reached", {}).items() if value]


def _result(
    task: EditorTask,
    *,
    status: str,
    play_outcome: str,
    started_at: str,
    persistence_path: str,
    evidence_bundle: EvidenceBundle | None = None,
    observations: list[dict[str, Any]] | None = None,
    proposed_changes: list[dict[str, Any]] | None = None,
    patch_artifacts: list[dict[str, Any]] | None = None,
    repository_mutations: list[dict[str, Any]] | None = None,
    before_hashes: dict[str, str] | None = None,
    after_hashes: dict[str, str] | None = None,
    verification_results: list[dict[str, Any]] | None = None,
    authorization_id: str | None = None,
    proposal_sha256: str | None = None,
    unresolveds: list[dict[str, Any]] | None = None,
    contradictions: list[dict[str, Any]] | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> EditorResult:
    base_observations = [
        {
            "classification": "confirmed",
            "claim": f"{task.editor} returned the ball to {task.play_owner}; {task.editor} did not acquire play authority.",
            "authority": "editor_handoff_contract",
        }
    ]
    if observations:
        base_observations.extend(observations)
    return EditorResult(
        task_id=task.task_id,
        schema_version=1,
        status=status,
        operation=task.operation,
        editor=task.editor,
        issued_by=task.issued_by,
        play_owner=task.play_owner,
        ball_holder=task.play_owner,
        next_decision_owner=task.play_owner,
        throw_completed=True,
        play_outcome=play_outcome,
        objective=task.objective,
        evidence_bundle=_jsonable_evidence(evidence_bundle),
        observations=base_observations,
        proposed_changes=proposed_changes or [],
        patch_artifacts=patch_artifacts or [],
        repository_mutations=repository_mutations or [],
        before_hashes=before_hashes or {},
        after_hashes=after_hashes or {},
        verification=verification_results or [],
        verification_results=verification_results or [],
        authorization_id=authorization_id,
        proposal_sha256=proposal_sha256,
        commit_performed=False,
        acceptance_claimed=False,
        unresolveds=unresolveds or [],
        contradictions=contradictions or [],
        limits_reached=_limits_reached(evidence_bundle),
        errors=errors or [],
        started_at=started_at,
        completed_at=now_utc(),
        persistence_path=persistence_path,
    )


def _rejected_result(task: EditorTask, errors: list[str], directory: Path, started_at: str) -> EditorResult:
    return _result(
        task,
        status="rejected",
        play_outcome="blocked",
        started_at=started_at,
        persistence_path=stable_path(directory),
        errors=[{
            "code": "editor_task_rejected",
            "message": "Current Editor authority boundary rejected the task before execution.",
            "details": errors,
        }],
        unresolveds=[{"classification": "unresolved", "reason": "task_rejected_before_execution"}],
    )


def _repository_context_request(task: EditorTask) -> RepositoryContextRequest:
    raw = dict(task.request.get("repository_context") or {})
    query = raw.get("query") if isinstance(raw.get("query"), dict) else {}
    constraints = task.constraints or {}
    limits = dict(DEFAULT_LIMITS)
    raw_limits = raw.get("limits") if isinstance(raw.get("limits"), dict) else {}
    for key, value in {**raw_limits, **constraints}.items():
        if key in limits and value not in {None, ""}:
            limits[key] = int(value)
    symbols = raw.get("symbols", raw.get("symbol", query.get("symbols", query.get("symbol"))))
    text = raw.get("text", query.get("text"))
    paths = raw.get("paths", query.get("paths"))
    operations = raw.get("operations") or raw.get("operation") or ["path_discovery", "text_search", "symbol_definition", "imports", "references"]
    return RepositoryContextRequest(
        request_id=f"{task.task_id}-evidence",
        objective=task.objective,
        include=list(task.scope.get("include") or []),
        exclude=list(task.scope.get("exclude") or []),
        operations=operations if isinstance(operations, list) else [str(operations)],
        symbols=symbols if isinstance(symbols, list) else ([str(symbols)] if symbols else []),
        text=text if isinstance(text, list) else ([str(text)] if text else []),
        paths=paths if isinstance(paths, list) else ([str(paths)] if paths else list(task.scope.get("include") or [])),
        limits=limits,
        constraints=["read_only", "preserve_unknowns", "require_line_citations"],
        synthesis=False,
    )


def _persist_evidence(directory: Path, bundle: EvidenceBundle) -> None:
    persistence.atomic_json(directory / "evidence_bundle.json", bundle.to_dict()["EvidenceBundle"])


def _run_inspection(task: EditorTask, directory: Path) -> EvidenceBundle:
    persistence.append_event(directory / "events.jsonl", "inspection_started")
    bundle = build_repository_context(_repository_context_request(task), persist=True)
    _persist_evidence(directory, bundle)
    persistence.append_event(
        directory / "events.jsonl",
        "inspection_completed",
        status=bundle.status,
        files_examined=len(bundle.files_examined),
        findings=len(bundle.findings),
    )
    return bundle


def _evidence_refs_for_path(bundle: EvidenceBundle, rel_path: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for collection_name in ("findings", "symbols", "references", "imports", "dependency_edges"):
        for item in getattr(bundle, collection_name, []):
            evidence_values = item.get("evidence") if isinstance(item, dict) else None
            candidates = evidence_values if isinstance(evidence_values, list) else ([evidence_values] if isinstance(evidence_values, dict) else [])
            if not candidates and isinstance(item, dict) and item.get("path") == rel_path:
                refs.append({"collection": collection_name, "path": rel_path, "line": item.get("start_line") or item.get("line")})
                continue
            for evidence in candidates:
                if isinstance(evidence, dict) and evidence.get("path") == rel_path:
                    refs.append({
                        "collection": collection_name,
                        "path": rel_path,
                        "start_line": evidence.get("start_line"),
                        "end_line": evidence.get("end_line"),
                        "evidence_type": evidence.get("evidence_type"),
                    })
    return refs[:12]


REPLACE_RE = re.compile(
    r"replace\s+(?P<old>'[^']*'|\"[^\"]*\")\s+with\s+(?P<new>'[^']*'|\"[^\"]*\")\s+in\s+(?P<path>[^\s]+)",
    re.IGNORECASE | re.DOTALL,
)

CHANGE_INTENT_ERROR_CODE = "change_intent_must_match_replace_quoted_text_with_quoted_text_in_path"
CHANGE_INTENT_EXPECTED = 'replace "<old>" with "<new>" in <repository path>'
CHANGE_INTENT_EXPECTED_FORMAT = 'replace "<old text>" with "<new text>" in <repository path>'
CHANGE_INTENT_EXAMPLE = 'replace "alpha" with "gamma" in Agency/Core/runtime/target.txt'
CHANGE_INTENT_GUIDANCE = (
    "Invalid change_intent.\n\n"
    "Expected:\n\n"
    f"{CHANGE_INTENT_EXPECTED}\n\n"
    "Expected format:\n\n"
    f"{CHANGE_INTENT_EXPECTED_FORMAT}\n\n"
    "Example:\n\n"
    f"{CHANGE_INTENT_EXAMPLE}"
)


def change_intent_help() -> dict[str, str]:
    return {
        "error_code": CHANGE_INTENT_ERROR_CODE,
        "expected": CHANGE_INTENT_EXPECTED,
        "expected_format": CHANGE_INTENT_EXPECTED_FORMAT,
        "example": CHANGE_INTENT_EXAMPLE,
        "guidance": CHANGE_INTENT_GUIDANCE,
    }


def _invalid_change_intent_unresolved() -> dict[str, Any]:
    guidance = change_intent_help()
    return {
        "classification": "unresolved",
        "reason": guidance["error_code"],
        "message": "Invalid change_intent.",
        "expected": guidance["expected"],
        "expected_format": guidance["expected_format"],
        "example": guidance["example"],
        "guidance": guidance["guidance"],
        "deterministic_contract": True,
    }


def _parse_replace_intent(change_intent: str) -> dict[str, str] | None:
    match = REPLACE_RE.search(str(change_intent or ""))
    if not match:
        return None
    try:
        old = ast.literal_eval(match.group("old"))
        new = ast.literal_eval(match.group("new"))
    except Exception:
        return None
    return {"old": str(old), "new": str(new), "path": match.group("path").strip().rstrip(".,;:")}


def _path_within_scope(rel_path: str, scope: list[str]) -> bool:
    if "." in scope or "./" in scope:
        return True
    normalized = rel_path.strip("/")
    for item in scope:
        scope_value = item.strip().strip("/")
        if normalized == scope_value or normalized.startswith(scope_value + "/"):
            return True
    return False


def _build_patch_proposal(task: EditorTask, bundle: EvidenceBundle) -> tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    parsed = _parse_replace_intent(str(task.request.get("change_intent") or ""))
    unresolveds: list[dict[str, Any]] = []
    if parsed is None:
        return "", {}, [], [_invalid_change_intent_unresolved()]
    target = resolve_repo_path(parsed["path"], root=DASHBOARD_ROOT)
    rel = repo_relative(target, root=DASHBOARD_ROOT)
    if not _path_within_scope(rel, task.scope.get("include") or []):
        return "", {}, [], [{"classification": "unresolved", "reason": "target_path_outside_task_scope", "path": rel}]
    if not target.is_file():
        return "", {}, [], [{"classification": "unresolved", "reason": "target_is_not_a_file", "path": rel}]
    supporting_evidence = _evidence_refs_for_path(bundle, rel)
    if not supporting_evidence:
        return "", {}, [], [{"classification": "unresolved", "reason": "no_repository_evidence_for_target_path", "path": rel}]
    before = target.read_text(encoding="utf-8-sig")
    old = parsed["old"]
    if old not in before:
        return "", {}, [], [{"classification": "not_found_within_scope", "reason": "old_text_not_found_in_target", "path": rel}]
    after = before.replace(old, parsed["new"], 1)
    diff = "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{rel}",
        tofile=f"b/{rel}",
    ))
    proposed_change = {
        "target_file": rel,
        "intended_change": "deterministic_text_replacement",
        "supporting_evidence": supporting_evidence,
        "assumptions": ["The requested replacement is intentional and remains subject to Gear/Seth approval."],
        "unresolveds": [],
    }
    proposal = {
        "schema_version": 1,
        "authority": "editor_patch_proposal_not_implementation",
        "proposal_method": "deterministic_text_replacement",
        "model_assistance_used": False,
        "patch_construction_is_not_implementation": True,
        "repository_mutation_performed": False,
        "target_files": [rel],
        "proposed_changes": [proposed_change],
        "supporting_evidence": supporting_evidence,
        "suggested_verification_commands": [
            "Review proposed.patch before any application.",
            "Apply only after explicit Gear PatchAuthorization.",
            "Run verification after an authorized apply step.",
        ],
    }
    return diff, proposal, [proposed_change], unresolveds


def _parse_patch_paths(patch_text: str) -> list[str]:
    paths: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path != "/dev/null" and path not in paths:
                paths.append(path)
    return paths


def _load_authorization(task: EditorTask) -> tuple[PatchAuthorization | None, Path | None, str | None]:
    raw = task.request.get("authorization")
    path_value = task.request.get("authorization_path")
    if isinstance(raw, dict):
        return patch_authorization_from_mapping(raw), None, None
    if path_value:
        path = resolve_repo_path(str(path_value), root=DASHBOARD_ROOT)
        return patch_authorization_from_mapping(json.loads(path.read_text(encoding="utf-8"))), path, None
    return None, None, "authorization_missing"


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _proposal_path(task: EditorTask, authorization: PatchAuthorization) -> Path:
    value = task.request.get("proposal_patch_path") or authorization.proposal_path
    if not value:
        raise ValueError("proposal_patch_path_missing")
    return resolve_repo_path(str(value), root=DASHBOARD_ROOT)


def _validate_patch_authorization(task: EditorTask, authorization: PatchAuthorization, patch_path: Path, patch_text: str) -> list[str]:
    errors: list[str] = []
    if not authorization.authorization_id:
        errors.append("authorization_id_required")
    if authorization.used_at:
        errors.append("authorization_already_used")
    try:
        if _utc(authorization.expires_at) < datetime.now(timezone.utc):
            errors.append("authorization_expired")
    except Exception:
        errors.append("authorization_expires_at_invalid")
    proposal_sha = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    if proposal_sha != authorization.proposal_sha256:
        errors.append("proposal_sha256_mismatch")
    if authorization.authorized_editor != ACTIVE_EDITOR_NAME:
        errors.append(f"authorization_editor_must_be_{ACTIVE_EDITOR_NAME}")
    if authorization.authorized_editor != task.editor:
        errors.append("authorization_editor_mismatch")
    if authorization.play_owner != task.play_owner:
        errors.append("authorization_play_owner_mismatch")
    if "apply_patch" not in authorization.allowed_operations:
        errors.append("authorization_does_not_allow_apply_patch")
    patch_paths = _parse_patch_paths(patch_text)
    for rel in patch_paths:
        if rel not in authorization.allowed_paths:
            errors.append(f"unauthorized_path:{rel}")
        if not _path_within_scope(rel, task.scope.get("include") or []):
            errors.append(f"path_outside_task_scope:{rel}")
    for rel, expected in authorization.baseline_hashes.items():
        path = resolve_repo_path(rel, root=DASHBOARD_ROOT)
        if not path.exists():
            errors.append(f"baseline_path_missing:{rel}")
            continue
        actual = _sha256_path(path)
        if actual != expected:
            errors.append(f"baseline_hash_mismatch:{rel}")
    return errors


def _mark_authorization_used(auth_path: Path | None, authorization: PatchAuthorization) -> None:
    if auth_path is None:
        return
    data = authorization.to_dict()
    data["used_at"] = now_utc()
    persistence.atomic_json(auth_path, data)


def _run_apply_patch(task: EditorTask, directory: Path, started_at: str) -> EditorResult:
    repository = repository_ref(DASHBOARD_ROOT)
    authorization, auth_path, auth_error = _load_authorization(task)
    if auth_error or authorization is None:
        return _result(
            task,
            status="rejected",
            play_outcome="blocked",
            started_at=started_at,
            persistence_path=stable_path(directory),
            errors=[{"code": auth_error or "authorization_unavailable", "message": "Missing PatchAuthorization."}],
            unresolveds=[{"classification": "unresolved", "reason": "patch_authorization_required"}],
        )
    try:
        patch_path = _proposal_path(task, authorization)
        patch_text = patch_path.read_text(encoding="utf-8")
    except Exception as exc:
        return _result(
            task,
            status="rejected",
            play_outcome="blocked",
            started_at=started_at,
            persistence_path=stable_path(directory),
            authorization_id=authorization.authorization_id,
            errors=[{"code": "proposal_load_failed", "message": f"{type(exc).__name__}: {exc}"}],
        )
    errors = _validate_patch_authorization(task, authorization, patch_path, patch_text)
    if errors:
        return _result(
            task,
            status="rejected",
            play_outcome="blocked",
            started_at=started_at,
            persistence_path=stable_path(directory),
            authorization_id=authorization.authorization_id,
            proposal_sha256=hashlib.sha256(patch_path.read_bytes()).hexdigest(),
            errors=[{"code": "patch_authorization_rejected", "details": errors}],
            before_hashes={path: _sha256_path(resolve_repo_path(path, root=DASHBOARD_ROOT)) for path in authorization.baseline_hashes if resolve_repo_path(path, root=DASHBOARD_ROOT).exists()},
        )

    patch_paths = _parse_patch_paths(patch_text)
    before_hashes = {rel: _sha256_path(resolve_repo_path(rel, root=DASHBOARD_ROOT)) for rel in patch_paths}
    before_blob_oids = {}
    for rel in patch_paths:
        try:
            before_blob_oids[rel] = get_blob_oid(repository, rel).oid
        except GitAuthorityError:
            before_blob_oids[rel] = None
    backups = {rel: resolve_repo_path(rel, root=DASHBOARD_ROOT).read_bytes() for rel in patch_paths if resolve_repo_path(rel, root=DASHBOARD_ROOT).exists()}
    check = git_check_patch(repository, patch_path)
    if check.git_exit_code != 0:
        return _result(
            task,
            status="failed",
            play_outcome="blocked",
            started_at=started_at,
            persistence_path=stable_path(directory),
            authorization_id=authorization.authorization_id,
            proposal_sha256=authorization.proposal_sha256,
            before_hashes=before_hashes,
            verification_results=[_git_observation_result(check)],
            errors=[{"code": "git_apply_check_failed", "message": check.stderr.strip()}],
        )
    apply = git_apply_patch(repository, patch_path)
    if apply.git_exit_code != 0:
        for rel, content in backups.items():
            resolve_repo_path(rel, root=DASHBOARD_ROOT).write_bytes(content)
        return _result(
            task,
            status="failed",
            play_outcome="blocked",
            started_at=started_at,
            persistence_path=stable_path(directory),
            authorization_id=authorization.authorization_id,
            proposal_sha256=authorization.proposal_sha256,
            before_hashes=before_hashes,
            verification_results=[_git_observation_result(apply)],
            errors=[{"code": "git_apply_failed", "message": apply.stderr.strip()}],
        )
    after_hashes = {rel: _sha256_path(resolve_repo_path(rel, root=DASHBOARD_ROOT)) for rel in patch_paths}
    after_blob_oids = {}
    for rel in patch_paths:
        try:
            after_blob_oids[rel] = get_blob_oid(repository, rel).oid
        except GitAuthorityError:
            after_blob_oids[rel] = None
    _mark_authorization_used(auth_path, authorization)
    mutations = [
        {
            "path": rel,
            "operation": "apply_patch",
            "before_sha256": before_hashes.get(rel),
            "after_sha256": after_hashes.get(rel),
            "before_blob_oid": before_blob_oids.get(rel),
            "after_blob_oid": after_blob_oids.get(rel),
        }
        for rel in patch_paths
    ]
    return _result(
        task,
        status="completed",
        play_outcome="returned",
        started_at=started_at,
        persistence_path=stable_path(directory),
        repository_mutations=mutations,
        before_hashes=before_hashes,
        after_hashes=after_hashes,
        authorization_id=authorization.authorization_id,
        proposal_sha256=authorization.proposal_sha256,
        verification_results=[_git_observation_result(check), _git_observation_result(apply)],
        observations=[{"classification": "confirmed", "claim": "Authorized patch was applied through the Git Authority Boundary; no commit or acceptance was performed.", "authority": "patch_authorization"}],
    )


def _run_verify(task: EditorTask, directory: Path, started_at: str) -> EditorResult:
    repository = repository_ref(DASHBOARD_ROOT)
    raw_commands = task.request.get("verification", {}).get("commands") if isinstance(task.request.get("verification"), dict) else None
    commands = raw_commands if isinstance(raw_commands, list) and raw_commands else ["git diff --check", "git status --short"]
    allowed = {"git diff --check", "git status --short"}
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for command in commands:
        text = str(command).strip()
        if text not in allowed:
            results.append({"command": text, "status": "rejected", "reason": "verification_command_not_allowed"})
            errors.append({"code": "verification_command_not_allowed", "command": text})
            continue
        observation = git_diff_check(repository) if text == "git diff --check" else git_status_short(repository)
        results.append(_git_observation_result(observation))
        if observation.git_exit_code != 0:
            errors.append({"code": "verification_command_failed", "command": text, "returncode": observation.git_exit_code})
    status = "completed" if not errors else "failed"
    return _result(
        task,
        status=status,
        play_outcome="returned" if status == "completed" else "blocked",
        started_at=started_at,
        persistence_path=stable_path(directory),
        verification_results=results,
        errors=errors,
        observations=[{"classification": "confirmed", "claim": "Verification produced evidence only; it did not claim acceptance.", "authority": "verification_not_acceptance"}],
    )


def execute_editor_task(task: EditorTask, *, reject_duplicates: bool = True) -> EditorResult:
    started_at = now_utc()
    directory = persistence.task_dir(task.task_id or f"rejected-{hashlib.sha256(started_at.encode()).hexdigest()[:12]}")
    if reject_duplicates and (directory / "task.json").exists():
        return _result(
            task,
            status="rejected",
            play_outcome="blocked",
            started_at=started_at,
            persistence_path=stable_path(directory),
            errors=[{"code": "duplicate_task_id", "message": "duplicate task IDs do not overwrite prior Editor work."}],
            unresolveds=[{"classification": "unresolved", "reason": "duplicate_task_id"}],
        )

    persistence.append_event(directory / "events.jsonl", "task_received", ball_holder=task.ball_holder)
    persistence.persist_task(task, directory)
    errors = validate_editor_task(task, root=DASHBOARD_ROOT)
    if errors:
        result = _rejected_result(task, errors, directory, started_at)
        persistence.append_event(directory / "events.jsonl", "task_rejected", errors=errors)
        persistence.persist_result(result, directory)
        return result
    persistence.append_event(directory / "events.jsonl", "task_validated")

    try:
        if task.operation == "inspect":
            bundle = _run_inspection(task, directory)
            status = "partial" if bundle.status == "partial" else ("blocked" if bundle.status in {"rejected", "failed"} else "completed")
            result = _result(
                task,
                status=status,
                play_outcome="returned" if status in {"completed", "partial"} else "blocked",
                started_at=started_at,
                persistence_path=stable_path(directory),
                evidence_bundle=bundle,
                observations=[{"classification": "confirmed", "claim": "Inspection used deterministic repository evidence only; memory retrieval and general model inference were not used.", "authority": "repository_context_builder"}],
                unresolveds=list(bundle.unresolveds),
                contradictions=list(bundle.contradictions),
                errors=[] if bundle.status not in {"rejected", "failed"} else [{"code": "inspection_failed", "message": bundle.status}],
            )
        elif task.operation == "propose_patch":
            bundle = _run_inspection(task, directory)
            if bundle.status in {"rejected", "failed"}:
                result = _result(task, status="blocked", play_outcome="blocked", started_at=started_at, persistence_path=stable_path(directory), evidence_bundle=bundle, unresolveds=[{"classification": "unresolved", "reason": "inspection_failed_before_patch_proposal"}])
                persistence.append_event(directory / "events.jsonl", "task_blocked", reason="inspection_failed_before_patch_proposal")
            elif not (bundle.findings or bundle.symbols or bundle.references or bundle.imports):
                result = _result(task, status="blocked", play_outcome="blocked", started_at=started_at, persistence_path=stable_path(directory), evidence_bundle=bundle, unresolveds=[{"classification": "unresolved", "reason": "insufficient_repository_evidence_for_patch_proposal"}])
                persistence.append_event(directory / "events.jsonl", "task_blocked", reason="insufficient_repository_evidence_for_patch_proposal")
            else:
                persistence.append_event(directory / "events.jsonl", "proposal_started")
                diff, proposal, changes, unresolveds = _build_patch_proposal(task, bundle)
                if unresolveds:
                    result = _result(task, status="blocked", play_outcome="blocked", started_at=started_at, persistence_path=stable_path(directory), evidence_bundle=bundle, unresolveds=unresolveds)
                    persistence.append_event(directory / "events.jsonl", "task_blocked", reason="proposal_unresolved")
                else:
                    patch_path = directory / "proposed.patch"
                    persistence.atomic_text(patch_path, diff)
                    proposal["proposal_sha256"] = hashlib.sha256(patch_path.read_bytes()).hexdigest()
                    persistence.atomic_json(directory / "proposal.json", proposal)
                    result = _result(
                        task,
                        status="completed" if bundle.status == "completed" else "partial",
                        play_outcome="returned",
                        started_at=started_at,
                        persistence_path=stable_path(directory),
                        evidence_bundle=bundle,
                        observations=[{"classification": "confirmed", "claim": "Patch construction is not implementation; no repository source files were changed.", "authority": "editor_handoff_contract"}],
                        proposed_changes=changes,
                        patch_artifacts=[{"path": stable_path(patch_path), "artifact_type": "unified_diff", "applied": False}],
                        verification_results=[{"classification": "not_repository_verification", "claim": "The patch artifact was constructed, but repository verification has not run."}],
                        proposal_sha256=proposal["proposal_sha256"],
                    )
                    persistence.append_event(directory / "events.jsonl", "proposal_completed", patch="proposed.patch")
        elif task.operation == "apply_patch":
            result = _run_apply_patch(task, directory, started_at)
        elif task.operation == "verify":
            result = _run_verify(task, directory, started_at)
        else:
            result = _rejected_result(task, [f"unknown_operation:{task.operation}"], directory, started_at)
    except Exception as exc:
        result = _result(
            task,
            status="failed",
            play_outcome="blocked",
            started_at=started_at,
            persistence_path=stable_path(directory),
            errors=[{"code": "editor_execution_failed", "message": f"{type(exc).__name__}: {exc}"}],
        )
        persistence.append_event(directory / "events.jsonl", "task_failed", error=f"{type(exc).__name__}: {exc}")

    persistence.persist_result(result, directory)
    persistence.append_event(directory / "events.jsonl", "ball_returned", from_holder=task.editor, to_holder=task.play_owner, result_status=result.status)
    persistence.append_event(directory / "events.jsonl", "task_returned", status=result.status, play_outcome=result.play_outcome)
    return result


def result_payload(result: EditorResult) -> dict[str, Any]:
    return {
        "ok": result.status in {"completed", "partial"},
        "task_id": result.task_id,
        "status": result.status,
        "operation": result.operation,
        "editor": result.editor,
        "issued_by": result.issued_by,
        "play_owner": result.play_owner,
        "ball_holder": result.ball_holder,
        "ball_owner": result.play_owner,
        "next_decision_owner": result.next_decision_owner,
        "throw_completed": result.throw_completed,
        "play_outcome": result.play_outcome,
        "repository_mutation_performed": bool(result.repository_mutations),
        "evidence_loaded": result.evidence_bundle is not None,
        "proposal_created": bool(result.patch_artifacts),
        "commit_performed": result.commit_performed,
        "acceptance_claimed": result.acceptance_claimed,
        "authorization_id": result.authorization_id,
        "proposal_sha256": result.proposal_sha256,
        "persistence_path": result.persistence_path,
        "unresolveds": result.unresolveds,
        "result": result.to_dict(),
    }


def load_task_file(path: str | Path) -> EditorTask:
    task_path = Path(path)
    text = task_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) if task_path.suffix.lower() in {".yaml", ".yml"} else json.loads(text)
    return editor_task_from_mapping(data)


def dry_run_task_file(path: str | Path) -> dict[str, Any]:
    try:
        task = load_task_file(path)
    except Exception as exc:
        return {
            "ok": False,
            "status": "rejected",
            "reason": "--task expects a YAML or JSON EditorTask file",
            "details": f"malformed_editor_task:{type(exc).__name__}: {exc}",
            "repository_mutation_performed": False,
            "authority": "editor_dry_run_contract_validation_only",
        }

    errors = validate_editor_task(task, root=DASHBOARD_ROOT)
    return {
        "ok": not errors,
        "status": "dry_run_validated" if not errors else "rejected",
        "task_id": task.task_id,
        "operation": task.operation,
        "editor": task.editor,
        "issued_by": task.issued_by,
        "play_owner": task.play_owner,
        "ball_holder": task.ball_holder,
        "next_decision_owner": task.next_decision_owner,
        "would_execute": task.operation if not errors else None,
        "repository_mutation_performed": False,
        "source_files_modified": False,
        "dry_run": True,
        "errors": errors,
        "authority": "editor_dry_run_contract_validation_only",
        "notes": [
            "Dry-run validates the bounded EditorTask contract only.",
            "Patch construction is not implementation.",
            "Patch application requires an explicit PatchAuthorization and is not performed in dry-run.",
        ],
    }


def submit_task_file(path: str | Path) -> EditorResult:
    try:
        task = load_task_file(path)
    except Exception as exc:
        digest = hashlib.sha256(str(path).encode("utf-8", errors="replace")).hexdigest()[:12]
        task = EditorTask(
            task_id=f"rejected-intake-{digest}",
            schema_version=1,
            issued_by="unknown",
            editor=ACTIVE_EDITOR_NAME,
            play_owner="unknown",
            ball_holder=ACTIVE_EDITOR_NAME,
            next_decision_owner="unknown",
            objective="Rejected malformed EditorTask intake.",
            operation="inspect",
            scope={"include": [], "exclude": []},
            constraints={"read_only": True, "mutation_authorized": False},
        )
        directory = persistence.task_dir(task.task_id)
        persistence.append_event(directory / "events.jsonl", "task_received", source=str(path))
        result = _rejected_result(task, ["--task expects a YAML or JSON EditorTask file", f"malformed_task:{type(exc).__name__}: {exc}"], directory, now_utc())
        persistence.persist_result(result, directory)
        return result
    return execute_editor_task(task)


def _load_result_payload(task_id: str) -> dict[str, Any]:
    return persistence.load_result(task_id)


def _make_inspect_task(args: argparse.Namespace) -> EditorTask:
    seed = json.dumps(vars(args), sort_keys=True, default=str)
    task_id = args.task_id or "editor-inspect-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    repo_request: dict[str, Any] = {"operations": args.operation or ["symbol_definition", "references"]}
    symbol_values = args.symbol or []
    if isinstance(symbol_values, str):
        symbol_values = [symbol_values]

    symbols = list(dict.fromkeys(
        value.strip()
        for value in symbol_values
        if isinstance(value, str) and value.strip()
    ))

    if symbols:
        repo_request["symbols"] = symbols
    if args.text:
        repo_request["text"] = args.text
    return EditorTask(
        task_id=task_id,
        schema_version=1,
        issued_by=args.issued_by,
        editor=args.editor,
        play_owner=args.play_owner,
        ball_holder=args.editor,
        next_decision_owner=args.play_owner,
        objective=args.objective or f"Inspect {', '.join(args.scope)}",
        operation="inspect",
        scope={"include": args.scope, "exclude": args.exclude or []},
        request={"repository_context": repo_request},
        constraints={"read_only": True, "mutation_authorized": False, "max_files": args.max_files, "max_matches": args.max_matches, "max_total_context_bytes": args.max_total_context_bytes},
        evidence_requirements=["repository_relative_path", "line_range", "excerpt"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python run.py task", description="Submit, inspect, and retrieve Editor tasks.")
    sub = parser.add_subparsers(dest="command")
    submit = sub.add_parser("submit")
    submit.add_argument("task_path", nargs="?")
    submit.add_argument("--task", dest="task_option")
    show = sub.add_parser("show")
    show.add_argument("task_id", nargs="?")
    result_cmd = sub.add_parser("result")
    result_cmd.add_argument("task_id", nargs="?")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--editor", default=ACTIVE_EDITOR_NAME)
    inspect.add_argument("--issued-by", default="Gear")
    inspect.add_argument("--play-owner", default="Gear")
    inspect.add_argument("--ball-owner", dest="play_owner_alias")
    inspect.add_argument("--scope", action="append", required=True)
    inspect.add_argument("--exclude", action="append")
    inspect.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Repository symbol to inspect; repeat for multiple symbols.",
    )
    inspect.add_argument("--text")
    inspect.add_argument("--operation", action="append")
    inspect.add_argument("--objective")
    inspect.add_argument("--task-id")
    inspect.add_argument("--max-files", type=int, default=DEFAULT_LIMITS["max_files"])
    inspect.add_argument("--max-matches", type=int, default=DEFAULT_LIMITS["max_matches"])
    inspect.add_argument("--max-total-context-bytes", type=int, default=DEFAULT_LIMITS["max_total_context_bytes"])
    args = parser.parse_args(argv or [])
    if hasattr(args, "play_owner_alias") and args.play_owner_alias:
        args.play_owner = args.play_owner_alias

    if args.command == "submit":
        supplied_paths = [
            value
            for value in (args.task_path, args.task_option)
            if value
        ]
        if len(supplied_paths) != 1:
            parser.error(
                "submit requires exactly one task path, "
                "provided positionally or with --task"
            )

        result = submit_task_file(supplied_paths[0])
        print(json.dumps(result_payload(result), indent=2, sort_keys=True))
        return 0 if result.status in {"completed", "partial"} else 1
    if args.command == "show":
        task_id = args.task_id or persistence.latest_task_id()
        print(json.dumps(persistence.load_task(task_id), indent=2, sort_keys=True))
        return 0
    if args.command == "result":
        task_id = args.task_id or persistence.latest_task_id()
        print(json.dumps(_load_result_payload(task_id), indent=2, sort_keys=True))
        return 0
    if args.command == "inspect":
        result = execute_editor_task(_make_inspect_task(args))
        print(json.dumps(result_payload(result), indent=2, sort_keys=True))
        return 0 if result.status in {"completed", "partial"} else 1
    parser.print_help()
    return 2
