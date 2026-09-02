from __future__ import annotations

import datetime
import importlib.util
import os
from typing import Any


def _timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _genai_client() -> tuple[Any | None, str | None]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, "GEMINI_API_KEY not configured"
    if importlib.util.find_spec("google.genai") is None:
        return None, "google.genai package unavailable"
    try:
        from google import genai  # type: ignore
    except Exception as exc:
        return None, f"google.genai import failed: {exc}"
    try:
        return genai.Client(api_key=api_key), None
    except Exception as exc:
        return None, f"Gemini client creation failed: {exc}"


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def list_available_models() -> list[str]:
    client, _reason = _genai_client()
    if client is None:
        return []
    try:
        return [m.name for m in client.models.list()]
    except Exception:
        return []


def request_analysis(purpose: str, context: str) -> dict[str, Any]:
    prompt = (
        f"PURPOSE: {purpose}\n"
        f"CONTEXT: {context}\n"
        "BOUNDARY: Consultant-only analysis. Mutation prohibited. No shell execution.\n"
        "INSTRUCTION: Return observations, risks, unresolved questions, and a proposal-only next step."
    )
    client, reason = _genai_client()
    if client is None:
        return {
            "ok": False,
            "status": "unavailable_or_unconfigured",
            "reason": reason,
            "model": get_model_name(),
            "prompt_summary": purpose,
            "authority": "candidate_only_no_mutation",
            "mutation_allowed": False,
            "timestamp": _timestamp(),
        }
    model_name = get_model_name()
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        try:
            text_payload = response.text
        except ValueError:
            text_payload = "[REDACTED: response blocked or unavailable]"
        return {
            "ok": True,
            "status": "response_received",
            "model": model_name,
            "prompt_summary": purpose,
            "response_text": text_payload,
            "authority": "candidate_only_no_mutation",
            "mutation_allowed": False,
            "timestamp": _timestamp(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "error",
            "error_detail": str(exc),
            "model": model_name,
            "prompt_summary": purpose,
            "authority": "candidate_only_no_mutation",
            "mutation_allowed": False,
            "timestamp": _timestamp(),
        }
