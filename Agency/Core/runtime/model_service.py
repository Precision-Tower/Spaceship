from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request

from typer import prompt

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.agents.discovery import discover_agents
from Agency.Core.runtime.reasoners.gguf import AUTHORITY, CodeReasoner
from Agency.Core.runtime.context_builder import (
    build_direct_file_context,
    build_memory_context,
    compose_agent_system_context,
    detects_patch_recommendation,
    _patch_recommendation_contract_violated,
    _patch_recommendation_fallback_answer,
    _direct_file_observation_answer,
    find_unresolved_file_mentions,
)
from Agency.Core.runtime.inference_policy import (
    InferencePolicy,
    exact_response_text,
    is_text_transform_request,
    select_inference_policy,
)
from Agency.Core.runtime.runtime_config import (
    configured_max_tokens as _runtime_configured_max_tokens,
    load_model_server_config as _runtime_load_model_server_config,
)
from Agency.Core.runtime.authoritative_state import (
    answer_authoritative_state_question,
    authoritative_state,
    classify_authoritative_state_request,
)
from Agency.Core.repository.context import repository_inspection_payload

from Agency.Core.capabilities.context_bites import (
    ValidationFeedback,
    run_refinement,
)


DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SYSTEM_WRAPPER = """You are a local Dashboard draft generator.
Follow the user's instruction exactly.
If the user asks for exact text, output only that exact text.
Do not explain unless explicitly asked.
"""
EXACT_RESPONSE_RE = re.compile(
    r"^\s*(?:respond|reply|return|output)\s+with\s+exactly:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)

AGENCY_ROOT = DASHBOARD_ROOT / "Agency"
AGENT_ROOT = AGENCY_ROOT / "Agents"

AGENT_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")

def normalize_agent_name(raw: str) -> str:
    cleaned = AGENT_NAME_RE.sub("", raw.strip())
    if not cleaned:
        raise ValueError("agent_name_empty")
    return cleaned[:1].upper() + cleaned[1:]


def stable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(DASHBOARD_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)

def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}

def _available_agent_names() -> list[str]:
    return sorted(discover_agents(AGENT_ROOT))


def _agent_not_available_payload(agent_name: str, agent_dir: Path) -> dict[str, Any]:
    available = _available_agent_names()
    available_text = ", ".join(available) if available else "(none)"
    return {
        "ok": False,
        "status": "agent_not_available",
        "reason": f"Agent not available: {agent_name}; available agents: {available_text}",
        "agent": agent_name,
        "agent_dir": stable_path(agent_dir),
        "available_agents": available,
        "response_provenance": "filesystem_agent_discovery",
        "model_inference_used": False,
        "draft": f"Agent not available: {agent_name}; available agents: {available_text}",
        "answer": f"Agent not available: {agent_name}; available agents: {available_text}",
        "response": f"Agent not available: {agent_name}; available agents: {available_text}",
    }



def _configured_max_tokens(key: str, fallback: int) -> int:
    return _runtime_configured_max_tokens(key, fallback)


def resolve_model_path() -> tuple[Path, str, list[Path]]:
    config = _runtime_load_model_server_config()
    return config.model_path, config.model_path_source, [config.model_path]

def _base_payload() -> dict[str, Any]:
    config = _runtime_load_model_server_config()
    model_path, model_path_source, checked = resolve_model_path()
    model_exists = model_path.is_file()
    server_exists = config.server_path.is_file()

    payload = {
        "authority": AUTHORITY,
        "service_module": "Dashboard/Agency/Core/runtime/model_service.py",
        "backend": "llama_server",
        "runtime_profile": config.profile_name,
        "endpoint": config.endpoint,
        "model_path": str(model_path),
        "model_path_source": model_path_source,
        "model_file_exists": model_exists,
        "server_path": str(config.server_path),
        "server_exists": server_exists,
        "context_tokens": config.ctx_size,
        "gpu_layers": config.gpu_layers,
        "checked_paths": [str(path) for path in checked],
    }

    if not model_exists:
        payload.update(
            {
                "ok": False,
                "status": "ExpectedFailure",
                "reason": f"GGUF model file not found: {model_path}",
            }
        )
    elif not server_exists:
        payload.update(
            {
                "ok": False,
                "status": "ExpectedFailure",
                "reason": f"llama-server binary missing or not executable: {config.server_path}",
            }
        )
    else:
        payload.update(
            {
                "ok": True,
                "status": "ready",
                "reason": "",
            }
        )

    return payload


def _status_without_runtime_state() -> dict[str, Any]:
    return _base_payload()



def _runtime_configuration_snapshot() -> dict[str, Any]:
    from Agency.Core.runtime.runtime_config import (
        load_model_server_config,
    )

    config = load_model_server_config()

    return {
        "profile": config.profile_name,
        "endpoint": config.endpoint,
        "model": str(config.model_path),
        "context_tokens": config.ctx_size,
        "gpu_layers": config.gpu_layers,
    }


def status() -> dict[str, Any]:
    from Agency.Core.runtime.environment import (
        bootstrap_environment_manifest,
        environment_manifest_path,
        runtime_configuration_drift,
    )
    payload = _status_without_runtime_state()

    manifest = bootstrap_environment_manifest(
        path=environment_manifest_path(),
        interactive=False,
    )

    runtimes = manifest.capabilities.get("runtimes", {})
    if not isinstance(runtimes, dict):
        runtimes = {}

    observed = runtimes.get("llama_server", {})
    if not isinstance(observed, dict):
        observed = {
            "running": bool(observed),
            "reachable": False,
        }

    configured = _runtime_configuration_snapshot()

    payload["runtime_state"] = {
        "authority": {
            "configured": "launch_intent",
            "observed": "machine_observation",
            "resolved": "runtime_selection",
        },
        "configured": configured,
        "observed": observed,
        "resolved": manifest.resolved_runtime.to_dict(),
        "drift": runtime_configuration_drift(
            configured,
            observed,
        ),
    }

    return payload


def _compose_system_context(system_context: str = "") -> str:
    extra = system_context.strip()
    if not extra:
        return DEFAULT_SYSTEM_WRAPPER

    return (
        f"{DEFAULT_SYSTEM_WRAPPER}\n"
        "Additional operator-provided system context:\n"
        f"{extra}"
    )


def _extract_exact_response(prompt: str) -> str | None:
    match = EXACT_RESPONSE_RE.match(prompt)
    if not match:
        return None

    exact = match.group("text").strip()
    if len(exact) >= 2 and exact[0] == exact[-1] and exact[0] in {"'", '"'}:
        exact = exact[1:-1].strip()

    return exact or None


def _effective_max_new_tokens(prompt: str, max_new_tokens: int) -> int:
    if _extract_exact_response(prompt) is None:
        return max_new_tokens

    return min(max_new_tokens, 32)


def _strip_assistant_preamble(text: str) -> str:
    cleaned = text.strip()
    prefixes = (
        "Assistant:",
        "assistant:",
        "Draft:",
        "draft:",
        "Answer:",
        "answer:",
        "Response:",
        "response:",
    )

    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                changed = True

    for polite in ("Sure, ", "Sure. ", "Here is the exact text: "):
        if cleaned.startswith(polite):
            cleaned = cleaned[len(polite):].strip()

    return cleaned


def _clean_draft(prompt: str, text: str) -> str:
    exact = _extract_exact_response(prompt)
    cleaned = _strip_assistant_preamble(text)

    if exact is not None:
        if cleaned == exact:
            return cleaned
        if exact in cleaned:
            return exact
        return cleaned

    if (
        detects_patch_recommendation(prompt)
        and _patch_recommendation_contract_violated(cleaned)
    ):
        return _patch_recommendation_fallback_answer(prompt)

    direct_file_answer = _direct_file_observation_answer(prompt)
    if direct_file_answer is not None:
        return direct_file_answer

    if "what is your role" in prompt.lower():
        if (
            not cleaned
            or cleaned.strip().lower() in {"none", "null", "unknown"}
            or "You are agent" in cleaned
            or "Primary behavior:" in cleaned
        ):
            return (
                "Identity:\n"
                "Cali is the Dashboard continuity and codebase observation agent.\n\n"
                "Owns:\n"
                "- Dashboard structure understanding\n"
                "- Route and capability mapping\n"
                "- Continuity briefs\n"
                "- Stale authority detection\n"
                "- Controlled change recommendations\n\n"
                "Does not own:\n"
                "- Validation\n"
                "- Direct mutation without approval\n"
                "- Runtime truth\n"
                "- Source authority\n"
                "- Canon promotion\n\n"
                "Current next action:\n"
                "Observe Dashboard context and recommend small reversible patches."
            )

    return cleaned

def ask_model(
    prompt: str,
    system_context: str = "",
    max_new_tokens: int = 192,
    inference_policy: InferencePolicy | dict[str, Any] | None = None,
) -> dict[str, Any]:
    if inference_policy is None:
        policy = select_inference_policy(
            prompt,
            requested_max_tokens=max_new_tokens,
            configured_reasoning_tokens=_configured_max_tokens("reasoning_max_tokens", 192),
            configured_patch_tokens=_configured_max_tokens("patch_recommendation_max_tokens", 512),
        )
    elif isinstance(inference_policy, InferencePolicy):
        policy = inference_policy
    else:
        policy = InferencePolicy(**{
            **inference_policy,
            "completion_validation": tuple(inference_policy.get("completion_validation", ())),
        })

    effective_max_new_tokens = int(policy.max_tokens)
    base = _base_payload()
    base["prompt_chars"] = len(prompt)
    base["max_new_tokens"] = effective_max_new_tokens
    base["inference_policy"] = policy.to_dict()
    base["thinking_enabled"] = policy.enable_thinking

    if not prompt.strip():
        base.update({
            "ok": False,
            "status": "ExpectedFailure",
            "reason": "Prompt is empty.",
        })
        return base

    if not base["ok"]:
        return base

    reasoner = CodeReasoner(base["model_path"])
    result = reasoner.generate_result(
        system_context=_compose_system_context(system_context),
        user_prompt=prompt,
        max_new_tokens=effective_max_new_tokens,
        inference_policy=policy,
    )

    base.update({
        "ok": result.ok,
        "status": result.status,
        "reason": result.reason,
        "draft": _clean_draft(prompt, result.text) if result.ok else result.text,
        "usage": result.usage or {},
        "finish_reason": result.finish_reason,
        "completion_status": result.completion_status,
    })
    return base

def build_workspace_snapshot_context(agent_dir: Path) -> str:
    snapshot_path = agent_dir / "state" / "current_workspace_snapshot.yaml"

    if not snapshot_path.exists():
        return ""

    snapshot_text = snapshot_path.read_text(encoding="utf-8")
    lines = []
    keep_prefixes = (
        "  timestamp_utc:",
        "  root:",
        "  authority:",
        "    Agency:",
        "    UI:",
        "    Engineering:",
        "      file_count:",
        "    modified_count:",
        "    untracked_count:",
        "    proposal_count:",
        "    result_count:",
    )

    for line in snapshot_text.splitlines():
        if line.startswith(keep_prefixes):
            lines.append(line)

    compact = "\n".join(lines).strip()
    if not compact:
        return ""

    return (
        "Current Workspace Snapshot Summary:\n"
        "Authority: workspace_snapshot_not_validation\n"
        "Priority: newer_than_retrieved_memory_for_workspace_state\n"
        "Use this for current workspace counts and git state.\n\n"
        f"{compact}"
    )

def classify_agent_request(prompt: str) -> str:
    if is_text_transform_request(prompt):
        return "rewrite"

    text = prompt.lower()

    workspace_phrases = (
        "current workspace",
        "workspace state",
        "workspace snapshot",
        "git state",
        "git status",
        "file count",
        "files scanned",
        "current project state",
        "current dashboard state",
    )
    if any(phrase in text for phrase in workspace_phrases):
        return "workspace_status"

    identity_phrases = (
        "who are you",
        "what are you",
        "what is your role",
        "what's your role",
        "what is your purpose",
        "what's your purpose",
    )
    if any(phrase in text for phrase in identity_phrases):
        return "identity"

    action_phrases = (
        "create ",
        "write ",
        "edit ",
        "modify ",
        "delete ",
        "apply ",
        "patch ",
        "make a file",
        "change file",
    )
    if any(phrase in text for phrase in action_phrases):
        return "action_request"

    code_phrases = (
        ".py",
        ".gd",
        ".yaml",
        ".json",
        "function",
        "class",
        "traceback",
        "error",
        "bug",
        "file ",
        "line ",
    )
    if any(phrase in text for phrase in code_phrases):
        return "code_question"

    architecture_phrases = (
        "agency",
        "ui",
        "engineering",
        "workbench",
        "ce-os",
        "cali.yaml",
        "architecture",
        "operating protocol",
        "action policy",
    )
    if any(phrase in text for phrase in architecture_phrases):
        return "architecture"

    return "general"

# BEGIN patch_008c_local_validator
# BEGIN patch_008d_semantic_patch_validation
def _patch_008d_extract_fenced_diff(draft: str) -> tuple[str, list[str]]:
    """Return the sole fenced unified diff or deterministic validation errors."""
    import re

    text = str(draft or "").strip()
    errors: list[str] = []

    match = re.fullmatch(
        r"```(?:diff)?[ \t]*\r?\n(?P<diff>.*?)\r?\n```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if match is None:
        errors.append(
            "return exactly one fenced unified diff with no prose outside it"
        )
        return "", errors

    diff_text = match.group("diff").strip()

    if diff_text.count("--- a/") != 1:
        errors.append(
            "the diff must contain exactly one source path beginning with '--- a/'"
        )

    if diff_text.count("+++ b/") != 1:
        errors.append(
            "the diff must contain exactly one destination path beginning with '+++ b/'"
        )

    if not any(line.startswith("@@ -") for line in diff_text.splitlines()):
        errors.append(
            "the diff must contain at least one hunk header beginning with '@@ -'"
        )

    return diff_text, errors


def _patch_008d_prompt_paths(prompt: str) -> set[str]:
    """Extract repository-like file paths explicitly named by the operator."""
    import re

    text = str(prompt or "")

    matches = re.findall(
        r"(?<![\w./-])"
        r"((?:[A-Za-z0-9_.-]+/)*"
        r"[A-Za-z0-9_.-]+\."
        r"(?:py|yaml|yml|json|toml|md|txt))"
        r"(?![\w./-])",
        text,
        flags=re.IGNORECASE,
    )

    return {
        path.replace("\\", "/").lstrip("./")
        for path in matches
    }


def _patch_008d_diff_paths(diff_text: str) -> tuple[str, str]:
    source_path = ""
    destination_path = ""

    for line in diff_text.splitlines():
        if line.startswith("--- a/") and not source_path:
            source_path = line[len("--- a/"):].strip().split("\t", 1)[0]
        elif line.startswith("+++ b/") and not destination_path:
            destination_path = line[len("+++ b/"):].strip().split("\t", 1)[0]

    return source_path, destination_path


def _patch_008d_is_comment_only_request(prompt: str) -> bool:
    text = str(prompt or "").lower()

    phrases = (
        "harmless comment",
        "comment only",
        "only a comment",
        "change one comment",
        "change a comment",
        "modify one comment",
        "modify a comment",
        "edit one comment",
        "edit a comment",
    )

    return any(phrase in text for phrase in phrases)


def _patch_008d_changed_content_lines(diff_text: str) -> list[str]:
    changed: list[str] = []

    for line in diff_text.splitlines():
        if line.startswith(("--- ", "+++ ", "@@")):
            continue

        if line.startswith("+") or line.startswith("-"):
            changed.append(line[1:])

    return changed


def _patch_008d_comment_change_errors(
    diff_text: str,
    target_path: str,
) -> list[str]:
    changed = _patch_008d_changed_content_lines(diff_text)
    suffix = Path(target_path).suffix.lower()

    if not changed:
        return ["the diff does not change any content"]

    if suffix == ".py":
        invalid = [
            line
            for line in changed
            if line.strip() and not line.lstrip().startswith("#")
        ]
    elif suffix in {".yaml", ".yml", ".toml"}:
        invalid = [
            line
            for line in changed
            if line.strip() and not line.lstrip().startswith("#")
        ]
    elif suffix in {".md", ".txt"}:
        # Prose files do not have a reliable universal comment syntax.
        invalid = []
    else:
        return [
            f"comment-only validation is unsupported for {suffix or 'this file type'}"
        ]

    if invalid:
        return [
            "the operator requested a comment-only change, but the diff changes "
            "executable or structured content"
        ]

    return []



# BEGIN patch_008e_fence_parser
def _patch_008e_fenced_blocks(draft: str) -> list[tuple[str, str]]:
    fence = "`" * 3
    blocks: list[tuple[str, str]] = []

    inside = False
    language = ""
    body: list[str] = []

    for line in str(draft or "").splitlines():
        stripped = line.strip()

        if not inside:
            if stripped.startswith(fence):
                inside = True
                language = stripped[len(fence):].strip().lower()
                body = []
            continue

        if stripped == fence:
            blocks.append(
                (
                    language,
                    "\n".join(body).strip(),
                )
            )
            inside = False
            language = ""
            body = []
            continue

        body.append(line)

    return blocks
# END patch_008e_fence_parser



# BEGIN patch_008e_diff_normalizer
def _patch_008e_normalize_model_patch(
    draft: str,
) -> tuple[str, bool, list[str]]:
    text = str(draft or "").strip()
    candidates: list[str] = []

    for language, body in _patch_008e_fenced_blocks(text):
        if language not in {"", "diff", "patch"}:
            continue

        lines = body.splitlines()

        has_source = any(
            line.startswith("--- a/")
            for line in lines
        )
        has_destination = any(
            line.startswith("+++ b/")
            for line in lines
        )
        has_hunk = any(
            line.startswith("@@ -")
            for line in lines
        )

        if has_source and has_destination and has_hunk:
            candidates.append(body.strip())

    if not candidates:
        return text, False, [
            "no fenced unified diff could be extracted"
        ]

    if len(candidates) > 1:
        return text, False, [
            "multiple fenced unified diffs were returned"
        ]

    fence = "`" * 3
    normalized = (
        fence
        + "diff\n"
        + candidates[0]
        + "\n"
        + fence
    )

    return normalized, normalized != text, []
# END patch_008e_diff_normalizer



# BEGIN patch_008e_candidate_validation
def _patch_008e_validate_candidate(
    draft: str,
    prompt: str,
    repo_root: Path | None = None,
) -> tuple[str, bool, list[str], bool, list[str]]:
    normalized, changed, normalization_errors = (
        _patch_008e_normalize_model_patch(draft)
    )

    format_violated = _patch_008c_contract_violated(
        normalized
    )

    semantic_errors = (
        []
        if normalization_errors or format_violated
        else _patch_008d_semantic_errors(
            draft=normalized,
            prompt=prompt,
            repo_root=repo_root,
        )
    )

    return (
        normalized,
        changed,
        normalization_errors,
        format_violated,
        semantic_errors,
    )
# END patch_008e_candidate_validation

# BEGIN patch_009a_context_bites_validation_adapter
def _context_bites_validation_feedback(
    *,
    draft: str,
    prompt: str,
    repo_root: Path | None = None,
) -> ValidationFeedback:
    (
        _normalized,
        _changed,
        normalization_errors,
        format_violated,
        semantic_errors,
    ) = _patch_008e_validate_candidate(
        draft=draft,
        prompt=prompt,
        repo_root=repo_root,
    )

    errors = list(normalization_errors)

    if format_violated:
        errors.append("patch contract violated")

    errors.extend(semantic_errors)

    return ValidationFeedback(
        valid=not errors,
        errors=tuple(errors),
    )
# END patch_009a_context_bites_validation_adapter


# BEGIN patch_009c_patch_refinement_prompt
def _patch_009c_patch_refinement_prompt(
    objective: str,
    candidate: str,
    feedback: ValidationFeedback,
    prior: tuple[Any, ...],
    number: int,
) -> str:
    validation_text = "\n".join(
        f"- {error}"
        for error in feedback.errors
    ) or "- unspecified validation failure"

    prior_text = "\n".join(
        (
            f"- attempt {artifact.number}: "
            f"{artifact.response[:240]}"
        )
        for artifact in prior
    ) or "- none"

    return (
        f"PATCH REFINEMENT ATTEMPT {number}\n"
        f"\n"
        f"ORIGINAL OBJECTIVE\n"
        f"{objective}\n"
        f"\n"
        f"CURRENT CANDIDATE\n"
        f"{candidate}\n"
        f"\n"
        f"DETERMINISTIC VALIDATION FAILURES\n"
        f"{validation_text}\n"
        f"\n"
        f"PRIOR FAILED ATTEMPTS\n"
        f"{prior_text}\n"
        f"\n"
        f"Repair only the named failures. Preserve everything that "
        f"already passed validation. Do not broaden scope or invent "
        f"repository state. Return exactly one fenced code block "
        f"containing a valid unified diff and no prose outside the "
        f"block. The diff must contain lines beginning with '--- a/' "
        f"and '+++ b/' and at least one hunk header beginning with "
        f"'@@ -'. Emit the patch itself; do not describe it."
    )
# END patch_009c_patch_refinement_prompt


def _patch_008d_semantic_errors(
    draft: str,
    prompt: str,
    repo_root: Path | None = None,
) -> list[str]:
    """Validate that a syntactically valid patch also targets repository reality."""
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    errors: list[str] = []

    diff_text, extraction_errors = _patch_008d_extract_fenced_diff(draft)
    errors.extend(extraction_errors)

    if not diff_text:
        return errors

    source_path, destination_path = _patch_008d_diff_paths(diff_text)

    if not source_path or not destination_path:
        errors.append("the unified diff does not contain readable target paths")
        return errors

    if source_path != destination_path:
        errors.append(
            "this patch mode requires the source and destination paths to match"
        )

    target_path = destination_path.replace("\\", "/").lstrip("./")
    target_parts = Path(target_path).parts

    if (
        Path(target_path).is_absolute()
        or ".." in target_parts
        or target_path.startswith("/")
    ):
        errors.append("the diff target must remain inside the repository")
        return errors

    resolved_root = root.resolve()
    resolved_target = (root / target_path).resolve()

    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        errors.append("the diff target escapes the repository root")
        return errors

    if not resolved_target.is_file():
        errors.append(
            f"the diff target does not exist in the repository: {target_path}"
        )

    requested_paths = _patch_008d_prompt_paths(prompt)

    if requested_paths and target_path not in requested_paths:
        requested = ", ".join(sorted(requested_paths))
        errors.append(
            f"the diff targets {target_path}, but the operator explicitly "
            f"requested: {requested}"
        )

    if _patch_008d_is_comment_only_request(prompt):
        errors.extend(
            _patch_008d_comment_change_errors(
                diff_text=diff_text,
                target_path=target_path,
            )
        )

    return errors
# END patch_008d_semantic_patch_validation


def _patch_008c_contract_violated(draft: str) -> bool:
    text = draft or ""
    has_old_path = re.search(r"(?m)^---\s+a/", text) is not None
    has_new_path = re.search(r"(?m)^\+\+\+\s+b/", text) is not None
    has_hunk = re.search(r"(?m)^@@\s+-\d+", text) is not None
    return not (has_old_path and has_new_path and has_hunk)
# END patch_008c_local_validator


def ask_agent(
    agent_name: str,
    prompt: str,
    max_new_tokens: int = 192,
    inference_target: str | None = None,
) -> dict[str, Any]:
    agent_name = normalize_agent_name(agent_name)
    agent_dir = AGENT_ROOT / agent_name
    if not agent_dir.is_dir():
        return _agent_not_available_payload(agent_name, agent_dir)
    prompt_lower = prompt.lower()
    context_route = classify_agent_request(prompt)

    missing_named_files = find_unresolved_file_mentions(prompt)
    if missing_named_files:
        missing_list = "\n".join(
            f"- {path}" for path in missing_named_files
        )
        missing_response = (
            "Unable to answer from source evidence because these explicitly "
            "named files could not be resolved:\n"
            f"{missing_list}"
        )
        return {
            "ok": False,
            "status": "named_file_not_found",
            "reason": "One or more explicitly named files could not be resolved.",
            "agent": agent_name,
            "context_route": locals().get("context_route", "code_question"),
            "direct_file_context_loaded": False,
            "missing_files": missing_named_files,
            "answer": missing_response,
            "draft": missing_response,
            "response": missing_response,
        }

    output_contract = _load_yaml(agent_dir / "output_contract.yaml")
    runtime = _load_yaml(agent_dir / "runtime.yaml")
    agent_runtime = runtime.get("AgentRuntime", {})
    if not isinstance(agent_runtime, dict):
        agent_runtime = {}
    runtime_model = agent_runtime.get("model", {})
    if not isinstance(runtime_model, dict):
        runtime_model = {}
    runtime_profile = runtime_model.get("profile")
    backend = str(runtime_model.get("backend") or "gguf")
    accelerator = str(runtime_model.get("accelerator") or "cpu")
    inference_route = str(runtime_model.get("inference_route") or "local")
    execution_mode = str(runtime_model.get("execution_mode") or "local_cpu")
    router_runtime = runtime_model.get("router_runtime")
    configured_inference_target = str(
        runtime_model.get("inference_target")
        or inference_route
        or runtime_profile
        or backend
    )
    normalized_backend = backend.strip().lower()
    normalized_router_runtime = str(router_runtime or "").strip().lower()

    uses_routed_runtime = (
        normalized_backend == "llama_server"
        or normalized_router_runtime == "llama_server"
    )
    routed_runtime = normalized_router_runtime or normalized_backend

    normalized_patch_prompt = prompt.lower()
    explicit_unified_diff_request = (
        "unified diff" in normalized_patch_prompt
        and any(
            verb in normalized_patch_prompt
            for verb in ("propose", "produce", "return", "draft", "recommend")
        )
    )
    patch_recommendation_mode = (
        detects_patch_recommendation(prompt)
        or explicit_unified_diff_request
    )
    patch_max_tokens = _configured_max_tokens("patch_recommendation_max_tokens", 512)
    reasoning_max_tokens = _configured_max_tokens("reasoning_max_tokens", 192)

    preliminary_policy = select_inference_policy(
        prompt,
        context_route=context_route,
        requested_max_tokens=max_new_tokens,
        configured_reasoning_tokens=reasoning_max_tokens,
        configured_patch_tokens=patch_max_tokens,
        patch_recommendation_mode=patch_recommendation_mode,
    )

    repository_payload = repository_inspection_payload(agent_name, prompt)
    if repository_payload is not None:
        repository_payload["agent_dir"] = stable_path(agent_dir)
        repository_payload["runtime_identity"] = {
            "backend": backend,
            "accelerator": accelerator,
            "inference_route": inference_route,
            "execution_mode": execution_mode,
        }
        repository_payload["runtime_profile"] = runtime_profile
        repository_payload["inference_target"] = configured_inference_target
        repository_payload["inference_policy"] = preliminary_policy.to_dict()
        return repository_payload

    authoritative_topic = (
        classify_authoritative_state_request(prompt)
        if preliminary_policy.allow_authoritative_state
        else None
    )
    if authoritative_topic is not None:
        policy = select_inference_policy(
            prompt,
            context_route=context_route,
            requested_max_tokens=max_new_tokens,
            configured_reasoning_tokens=reasoning_max_tokens,
            configured_patch_tokens=patch_max_tokens,
            patch_recommendation_mode=patch_recommendation_mode,
            authoritative_topic=authoritative_topic,
        )
        state = authoritative_state(agent_name)
        response = answer_authoritative_state_question(state, authoritative_topic)
        return {
            "ok": True,
            "status": (
                "authoritative_state"
                if state.available
                else "authoritative_state_unavailable"
            ),
            "draft": response,
            "answer": response,
            "response": response,
            "agent": agent_name,
            "agent_dir": stable_path(agent_dir),
            "context_route": "authoritative_state",
            "authoritative_state_topic": authoritative_topic,
            "authoritative_state_available": state.available,
            "authoritative_state": state.to_dict(),
            "response_provenance": "authoritative_state",
            "runtime_identity": state.runtime or {
                "backend": backend,
                "accelerator": accelerator,
                "inference_route": inference_route,
                "execution_mode": execution_mode,
            },
            "inference_policy": policy.to_dict(),
            "thinking_enabled": policy.enable_thinking,
            "runtime_profile": runtime_profile,
            "inference_target": configured_inference_target,
            "memory_results_loaded": 0,
            "memory_retrieval_skipped": True,
            "direct_file_context_loaded": False,
            "workspace_snapshot_loaded": False,
            "output_contract_loaded": False,
        }

    policy = preliminary_policy

    if context_route == "identity":
        identity = agent_runtime.get("identity", {})
        role = identity.get("role")
        description = identity.get("description")

        identity_lines = [f"{agent_name}"]
        if role:
            identity_lines.append(f"Role: {role}")
        if description:
            identity_lines.append(f"Description: {description}")

        return {
            "ok": True,
            "status": "identity_from_runtime",
            "draft": "\n".join(identity_lines),
            "response": "\n".join(identity_lines),
            "agent": agent_name,
            "agent_dir": stable_path(agent_dir),
            "context_route": context_route,
            "runtime_identity": {
                "backend": backend,
                "accelerator": accelerator,
                "inference_route": inference_route,
                "execution_mode": execution_mode,
            },
            "inference_policy": policy.to_dict(),
            "thinking_enabled": policy.enable_thinking,
            "runtime_profile": runtime_profile,
            "inference_target": configured_inference_target,
            "runtime_identity_source": stable_path(
                agent_dir / "runtime.yaml"
            ),
        }

    if inference_target is None:
        inference_target = configured_inference_target
    autonomy = _load_yaml(agent_dir / "autonomy" / "autonomy.yaml")
    short_term = _load_yaml(agent_dir / "memory" / "short_term.yaml")
    state = _load_yaml(agent_dir / "state" / "agent_state.yaml")

    should_retrieve = not (
        exact_response_text(prompt) is not None
        or policy.route == "rewrite"
        or "what is your role" in prompt_lower
        or "who are you" in prompt_lower
        or "what are you" in prompt_lower
    )

    direct_context = build_direct_file_context(prompt)

    workspace_snapshot_context = (
        build_workspace_snapshot_context(agent_dir)
        if context_route == "workspace_status"
        else ""
    )
    use_memory = should_retrieve and should_use_memory(agent_name, prompt, direct_context)

    memory_results = []
    memory_retrieval_error: str | None = None

    vector_memory_enabled = (
        os.environ.get("AGENCY_VECTOR_MEMORY", "").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    memory_retrieval_skipped = not use_memory or not vector_memory_enabled

    if use_memory and vector_memory_enabled:
        try:
            from Agency.Core.agents.tooling.Chroma import retrieve_agent_memory

            memory_results = retrieve_agent_memory(agent_name, prompt)
        except Exception as exc:
            memory_retrieval_error = (
                f"{type(exc).__name__}: {exc}"
            )
            memory_retrieval_skipped = True

    retrieved_memory = build_memory_context(memory_results)
    route_instruction = ""

    if policy.route == "rewrite":
        route_instruction = (
            "Rewrite Mode:\n"
            "- Return only the rewritten sentence.\n"
            "- Do not return JSON, labels, analysis, or next actions.\n"
        )
    elif context_route == "architecture":
        route_instruction = (
            "Architecture Answer Mode:\n"
            "- Answer in no more than 5 bullets.\n"
            "- Do not repeat yourself.\n"
            "- Do not include 'Assistant Output'.\n"
            "- Separate current definition from unresolved or stale next-action notes.\n"
            "- If retrieved memory contains stale next actions, label them as possible stale context.\n"
            "- Do not include next patch recommendations unless the user explicitly asks for next steps.\n"
        )
    elif context_route == "workspace_status":
        route_instruction = (
            "Workspace Status Mode:\n"
            "- Answer from the current workspace snapshot only.\n"
            "- Use short bullets.\n"
            "- Do not discuss stale memory.\n"
        )

    if patch_recommendation_mode:
        route_instruction += (
            "\nPatch formatting requirements:\n"
            "- Return exactly one fenced code block containing a valid unified diff.\n"
            "- The diff must include lines beginning with '--- a/' and '+++ b/'.\n"
            "- The diff must include at least one hunk header beginning with '@@ -'.\n"
            "- Do not substitute a replacement snippet, pseudocode, or prose for the diff.\n"
            "- Keep the proposed change small and reversible.\n"
        )

    combined_memory = "\n\n".join(
        block for block in (
            route_instruction,
            workspace_snapshot_context,
            direct_context,
            retrieved_memory,
        )
        if block
    )

    effective_max_new_tokens = int(policy.max_tokens)

    active_output_contract = (
        {}
        if policy.route in {"exact_response", "rewrite"}
        else output_contract
    )

    system_context = compose_agent_system_context(
        agent_name=agent_name,
        runtime=runtime,
        autonomy=autonomy,
        short_term=short_term,
        state=state,
        retrieved_memory=combined_memory,
        output_contract=active_output_contract,
        patch_recommendation_mode=patch_recommendation_mode,
    )

    if uses_routed_runtime:
        from Agency.Core.runtime.runtime_router import ask as routed_ask

        payload = routed_ask(
            prompt=prompt,
            agent_name=agent_name,
            system_context=system_context,
            max_new_tokens=effective_max_new_tokens,
            runtime=routed_runtime,
            inference_policy=policy.to_dict(),
        )
    else:
        payload = ask_model(
            prompt=prompt,
            system_context=system_context,
            max_new_tokens=effective_max_new_tokens,
            inference_policy=policy,
        )
    # BEGIN patch_009c_context_bites_patch_refinement
    if patch_recommendation_mode:
        initial_patch_draft = (
            payload.get("draft")
            or payload.get("answer")
            or payload.get("response")
            or ""
        )

        (
            initial_patch_draft,
            initial_patch_normalized,
            initial_normalization_errors,
            initial_format_violated,
            initial_semantic_errors,
        ) = _patch_008e_validate_candidate(
            draft=initial_patch_draft,
            prompt=prompt,
        )

        if initial_patch_normalized:
            payload["draft"] = initial_patch_draft
            payload["answer"] = initial_patch_draft
            payload["response"] = initial_patch_draft

        patch_contract_violated = (
            bool(initial_normalization_errors)
            or initial_format_violated
            or bool(initial_semantic_errors)
        )

        payload["patch_contract_violated_initially"] = (
            patch_contract_violated
        )
        payload["patch_normalized_initially"] = (
            initial_patch_normalized
        )
        payload["patch_normalization_errors_initially"] = (
            initial_normalization_errors
        )
        payload["patch_format_violated_initially"] = (
            initial_format_violated
        )
        payload["patch_semantic_errors_initially"] = (
            initial_semantic_errors
        )
        payload["patch_repair_attempted"] = False
        payload["patch_repair_succeeded"] = False
        payload["patch_refinement_attempts"] = 0
        payload["patch_refinement_artifacts"] = []
        payload["patch_refinement_reason"] = ""

        if patch_contract_violated:
            payload["patch_repair_attempted"] = True

            refinement_payloads: list[dict[str, Any]] = []

            def invoke_patch_refinement(
                refinement_prompt: str,
            ) -> str:
                if uses_routed_runtime:
                    refinement_payload = routed_ask(
                        prompt=refinement_prompt,
                        agent_name=agent_name,
                        system_context=system_context,
                        max_new_tokens=effective_max_new_tokens,
                        runtime=routed_runtime,
                        inference_policy=policy.to_dict(),
                    )
                else:
                    refinement_payload = ask_model(
                        prompt=refinement_prompt,
                        system_context=system_context,
                        max_new_tokens=effective_max_new_tokens,
                        inference_policy=policy,
                    )

                refinement_payloads.append(
                    refinement_payload
                )

                return (
                    refinement_payload.get("draft")
                    or refinement_payload.get("answer")
                    or refinement_payload.get("response")
                    or ""
                )

            refinement_result = run_refinement(
                objective=prompt,
                candidate=initial_patch_draft,
                invoke=invoke_patch_refinement,
                validate=lambda candidate: (
                    _context_bites_validation_feedback(
                        draft=candidate,
                        prompt=prompt,
                    )
                ),
                candidate_extractor=lambda artifact: artifact.response,
                prompt_builder=(
                    _patch_009c_patch_refinement_prompt
                ),
            )

            refinement_artifacts = [
                artifact.to_dict()
                for artifact in refinement_result.artifacts
            ]
            final_refinement_payload = (
                refinement_payloads[-1]
                if refinement_payloads
                else {}
            )

            repaired_draft = refinement_result.final_output

            (
                repaired_draft,
                repaired_patch_normalized,
                repaired_normalization_errors,
                repaired_format_violated,
                repaired_semantic_errors,
            ) = _patch_008e_validate_candidate(
                draft=repaired_draft,
                prompt=prompt,
            )

            repaired_contract_violated = (
                bool(repaired_normalization_errors)
                or repaired_format_violated
                or bool(repaired_semantic_errors)
            )

            if (
                refinement_result.status == "ready"
                and not repaired_contract_violated
            ):
                payload = dict(final_refinement_payload)

                payload["draft"] = repaired_draft
                payload["answer"] = repaired_draft
                payload["response"] = repaired_draft

                payload["patch_contract_violated_initially"] = True
                payload["patch_initial_draft"] = initial_patch_draft
                payload["patch_normalized_initially"] = (
                    initial_patch_normalized
                )
                payload["patch_normalization_errors_initially"] = (
                    initial_normalization_errors
                )
                payload["patch_format_violated_initially"] = (
                    initial_format_violated
                )
                payload["patch_semantic_errors_initially"] = (
                    initial_semantic_errors
                )
                payload["patch_repair_attempted"] = True
                payload["patch_repair_succeeded"] = True
                payload["patch_repair_response"] = (
                    final_refinement_payload
                )
                payload["patch_contract_violated_after_repair"] = False
                payload["patch_normalized_after_repair"] = (
                    repaired_patch_normalized
                )
                payload["patch_normalization_errors_after_repair"] = (
                    repaired_normalization_errors
                )
                payload["patch_format_violated_after_repair"] = False
                payload["patch_semantic_errors_after_repair"] = []
                payload["patch_refinement_attempts"] = len(
                    refinement_result.artifacts
                )
                payload["patch_refinement_artifacts"] = (
                    refinement_artifacts
                )
                payload["patch_refinement_reason"] = ""
            else:
                failure = (
                    f"Patch generation failed closed: {agent_name} did not "
                    "produce a repository-grounded unified diff within "
                    "the bounded refinement budget."
                )

                payload["ok"] = False
                payload["status"] = "patch_contract_failed"
                payload["reason"] = failure
                payload["draft"] = failure
                payload["answer"] = failure
                payload["response"] = failure
                payload["patch_initial_draft"] = initial_patch_draft
                payload["patch_repair_response"] = (
                    final_refinement_payload
                )
                payload["patch_contract_violated_after_repair"] = True
                payload["patch_normalized_after_repair"] = (
                    repaired_patch_normalized
                )
                payload["patch_normalization_errors_after_repair"] = (
                    repaired_normalization_errors
                )
                payload["patch_format_violated_after_repair"] = (
                    repaired_format_violated
                )
                payload["patch_semantic_errors_after_repair"] = (
                    repaired_semantic_errors
                )
                payload["patch_repair_succeeded"] = False
                payload["patch_refinement_attempts"] = len(
                    refinement_result.artifacts
                )
                payload["patch_refinement_artifacts"] = (
                    refinement_artifacts
                )
                payload["patch_refinement_reason"] = (
                    refinement_result.reason
                )
    # END patch_009c_context_bites_patch_refinement
    payload["runtime_identity"] = {
        "backend": backend,
        "accelerator": accelerator,
        "inference_route": inference_route,
        "execution_mode": execution_mode,
    }
    payload["runtime_profile"] = runtime_profile
    payload["inference_target"] = inference_target
    payload["patch_recommendation_mode"] = patch_recommendation_mode
    payload["configured_patch_max_tokens"] = patch_max_tokens
    payload["configured_reasoning_max_tokens"] = reasoning_max_tokens
    payload["inference_policy"] = policy.to_dict()
    payload["thinking_enabled"] = policy.enable_thinking
    payload["output_contract_loaded"] = bool(active_output_contract)
    payload["agent_output_contract_loaded"] = bool(output_contract)
    payload["agent"] = agent_name
    payload["agent_dir"] = stable_path(agent_dir)
    payload["inference_target"] = inference_target
    payload["autonomy_loaded"] = bool(autonomy)
    payload["memory_results_loaded"] = len(memory_results)
    payload["memory_retrieval_skipped"] = memory_retrieval_skipped
    payload["direct_file_context_loaded"] = bool(direct_context)
    payload["workspace_snapshot_loaded"] = bool(workspace_snapshot_context)
    payload["context_route"] = context_route
    payload.setdefault("response_provenance", "model_inference")
    return payload

def should_use_memory(agent_name: str, prompt: str, direct_context: str) -> bool:
    context_route = classify_agent_request(prompt)

    if direct_context:
        return False

    if context_route in {"workspace_status", "identity", "rewrite"}:
        return False

    return True

def _print_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="Dashboard model",
        description="Inspect and use the configured Dashboard model runtime.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Report configured model runtime status.")

    ask = sub.add_parser("ask", help="Send a prompt directly to the configured model.")
    ask.add_argument("prompt", nargs="+")
    ask.add_argument("--system-context", default="")
    ask.add_argument("--max-new-tokens", type=int, default=192)

    agent_ask = sub.add_parser("agent-ask", help="Send a prompt through an agent runtime profile.")
    agent_ask.add_argument("agent_name")
    agent_ask.add_argument("prompt", nargs="+")
    agent_ask.add_argument("--max-new-tokens", type=int, default=192)

    parsed = parser.parse_args(args)

    if parsed.command in {None, "status"}:
        _print_payload(status())
        return 0

    if parsed.command == "ask":
        payload = ask_model(
            prompt=" ".join(parsed.prompt),
            system_context=parsed.system_context,
            max_new_tokens=parsed.max_new_tokens,
        )
        _print_payload(payload)
        return 0 if payload.get("ok") else 1

    if parsed.command == "agent-ask":
        payload = ask_agent(
            agent_name=parsed.agent_name,
            prompt=" ".join(parsed.prompt),
            max_new_tokens=parsed.max_new_tokens,
        )
        _print_payload(payload)
        return 0 if payload.get("ok") else 1

    parser.print_help()
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
