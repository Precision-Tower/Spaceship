from __future__ import annotations

import datetime
import importlib.util
import os
from typing import Any


DEFAULT_MODEL = "gemini-3.7-flash"


def model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def _client(api_key: str | None = None) -> tuple[Any | None, str | None]:
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return None, "Gemini credential not configured"
    if importlib.util.find_spec("google.genai") is None:
        return None, "google.genai package unavailable"
    try:
        from google import genai
        return genai.Client(api_key=key), None
    except Exception as exc:
        return None, f"Gemini client creation failed: {exc}"


def available_models(*, api_key: str | None = None) -> list[str]:
    client, _ = _client(api_key)
    if client is None:
        return []
    try:
        return [item.name for item in client.models.list()]
    except Exception:
        return []


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)

    chunks: list[str] = []

    outputs = getattr(response, "outputs", None)
    if outputs:
        for output in outputs:
            value = getattr(output, "text", None)
            if value:
                chunks.append(str(value))

    steps = getattr(response, "steps", None)
    if steps:
        for step in steps:
            content = getattr(step, "content", None)
            if not content:
                continue
            for item in content:
                value = getattr(item, "text", None)
                if value:
                    chunks.append(str(value))

    return "\n".join(chunks)


def classify_failure(result: dict[str, Any]) -> str | None:
    if result.get("ok"):
        return None
    text = str(result.get("error_detail") or result.get("reason") or "").upper()
    if any(marker in text for marker in ("429", "RESOURCE_EXHAUSTED", "QUOTA")):
        return "quota"
    if any(marker in text for marker in ("401", "403", "UNAUTHENTICATED", "PERMISSION_DENIED", "API KEY")):
        return "auth"
    if any(marker in text for marker in ("NETWORK", "CONNECTION", "DNS")):
        return "network"
    if result.get("status") == "provider_temporarily_unavailable":
        return "availability"
    return "error"


def request_worker_turn(
    *,
    purpose: str,
    context: str,
    previous_interaction_id: str | None = None,
    system_instruction: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    client, reason = _client(api_key)
    if client is None:
        return {
            "ok": False,
            "status": "unavailable_or_unconfigured",
            "reason": reason,
            "model": model_name(),
            "authority": "geminigo_model_draft_not_truth",
            "mutation_allowed": False,
        }

    body: dict[str, Any] = {
        "model": model_name(),
        "input": f"PURPOSE: {purpose}\n\n{context}",
        "store": True,
        "generation_config": {"thinking_config": {"thinking_level": "MEDIUM"}},
    }
    if previous_interaction_id:
        body["previous_interaction_id"] = previous_interaction_id
    if system_instruction:
        body["system_instruction"] = system_instruction

    try:
        response = client.interactions.create(**body)
        return {
            "ok": True,
            "status": "response_received",
            "model": model_name(),
            "interaction_id": getattr(response, "id", None),
            "response_text": _response_text(response),
            "authority": "geminigo_model_draft_not_truth",
            "mutation_allowed": False,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    except Exception as exc:
        text = str(exc)
        upper = text.upper()
        transient = any(marker in upper for marker in (
            "429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE",
            "CONNECTION RESET", "TIMED OUT", "TIMEOUT",
        ))
        return {
            "ok": False,
            "status": "provider_temporarily_unavailable" if transient else "error",
            "error_detail": text,
            "model": model_name(),
            "interaction_id": previous_interaction_id,
            "authority": "geminigo_model_draft_not_truth",
            "mutation_allowed": False,
        }
