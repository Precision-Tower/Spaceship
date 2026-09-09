from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from Agency.Core.runtime.llama_server_client import ask, status
from Agency.Core.runtime.runtime_config import load_model_server_config


EVAL_SCHEMA_VERSION = 1
DEFAULT_POLICY = {
    # Pixel CPU inference is intentionally bounded; larger hosts retain their
    # own runtime/profile budgets outside this evaluation harness.
    "max_tokens": 20,
    "temperature": 0.0,
    "enable_thinking": False,
    "reasoning_effort": "none",
    "completion_validation": (),
    "allow_authoritative_state": False,
    "output_contract": "evaluation_evidence",
    "reason": "bounded GeminiGo local-model evaluation",
    "requires_model": True,
    "route": "local",
}


def evaluation_root() -> Path:
    return Path.home() / ".ce-os" / "geminigo" / "local-model-evaluations"


def runtime_snapshot(
    *,
    status_call: Callable[[], dict[str, Any]] = status,
) -> dict[str, Any]:
    cfg = load_model_server_config()
    configured = {
        "profile": cfg.profile_name,
        "endpoint": cfg.endpoint,
        "model_path": str(cfg.model_path),
        "model_file_exists": cfg.model_path.is_file(),
        "server_path": str(cfg.server_path),
        "server_file_exists": cfg.server_path.is_file(),
    }
    if not configured["model_file_exists"]:
        return {
            "ok": False,
            "status": "model_unavailable",
            "reason": "configured local GGUF is absent",
            "configured": configured,
        }
    if not configured["server_file_exists"]:
        return {
            "ok": False,
            "status": "server_unavailable",
            "reason": "configured llama-server executable is absent",
            "configured": configured,
        }
    observed = status_call()
    return {
        "ok": bool(observed.get("ok")),
        "status": observed.get("status"),
        "reason": observed.get("reason", ""),
        "configured": configured,
        "observed": observed,
    }


def evaluate_prompt(
    *,
    evaluation_id: str,
    prompt: str,
    expected_capability: str,
    agent: str = "Editor",
    ask_call: Callable[..., dict[str, Any]] = ask,
    status_call: Callable[[], dict[str, Any]] = status,
    persist: bool = True,
) -> dict[str, Any]:
    token = "".join(
        ch for ch in evaluation_id.strip()
        if ch.isalnum() or ch in "._-"
    )
    if not token:
        raise ValueError("local_eval_id_required")
    if not prompt.strip():
        raise ValueError("local_eval_prompt_required")

    runtime = runtime_snapshot(status_call=status_call)
    record: dict[str, Any] = {
        "schema_version": EVAL_SCHEMA_VERSION,
        "evaluation_id": token,
        "agent": agent,
        "prompt": prompt,
        "expected_capability": expected_capability,
        "runtime": runtime,
        "inference_policy": dict(DEFAULT_POLICY),
        "response": "",
        "latency_ms": 0,
        "model_status": runtime.get("status"),
        "failure_class": None,
        "evaluator_findings": [],
        "training_evidence_only": True,
        "establishes_architectural_truth": False,
    }

    if not runtime.get("ok"):
        record["failure_class"] = "runtime"
        record["evaluator_findings"] = [
            "Local model conversation was not attempted because the selected runtime is unavailable."
        ]
    else:
        started = time.monotonic()
        result = ask_call(
            prompt,
            agent=agent,
            system_context=(
                "You are the resident CE-OS Agency model under evaluation. "
                "Answer only from the supplied question and your available context. "
                "Do not claim repository mutation or authority you do not possess."
            ),
            inference_policy=DEFAULT_POLICY,
        )
        record["latency_ms"] = max(0, int((time.monotonic() - started) * 1000))
        record["model_status"] = result.get("status")
        record["response"] = str(
            result.get("response")
            or result.get("answer")
            or result.get("draft")
            or ""
        )
        if not result.get("ok"):
            record["failure_class"] = "model_or_runtime"
            record["evaluator_findings"] = [
                str(result.get("reason") or "local model request failed")
            ]
        elif not record["response"].strip():
            record["failure_class"] = "model_behavior"
            record["evaluator_findings"] = ["Local model returned no visible response."]
        else:
            record["evaluator_findings"] = [
                "Response captured for external Gemini/CE-OS evaluation."
            ]

    if persist:
        root = evaluation_root() / token
        root.mkdir(parents=True, exist_ok=True)
        target = root / "evaluation.json"
        target.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        record["evidence_path"] = str(target)

    return record
