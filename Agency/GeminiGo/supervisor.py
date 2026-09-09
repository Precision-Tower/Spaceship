from __future__ import annotations

import time
from typing import Any, Callable

from Agency.GeminiGo.credentials import api_key
from Agency.GeminiGo.provider import classify_failure, request_worker_turn
from Agency.GeminiGo.state import append_event


TERMINAL_MODEL_REASONS = {"CLEAN", "COMPLETE", "BLOCKED", "STALLED"}


def execute_with_failover(
    *,
    call: Callable[..., dict[str, Any]] = request_worker_turn,
    previous_interaction_id: str | None,
    purpose: str,
    context: str,
    system_instruction: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    primary = api_key("primary")
    if not primary:
        return {
            "ok": False,
            "status": "unconfigured",
            "credential_slot": None,
            "reason": "GeminiGo primary credential not configured",
        }

    first = call(
        purpose=purpose,
        context=context,
        previous_interaction_id=previous_interaction_id,
        system_instruction=system_instruction,
        api_key=primary,
    )
    first["credential_slot"] = "primary"
    failure = classify_failure(first)
    if session_id:
        append_event(
            session_id, "provider_attempt",
            credential_slot="primary",
            ok=bool(first.get("ok")),
            status=first.get("status"),
            failure_class=failure,
            interaction_id=first.get("interaction_id"),
            retry_after=first.get("retry_after"),
        )
    if failure not in {"quota", "availability"}:
        return first

    reserve = api_key("reserve")
    if not reserve:
        first["stop_reason"] = "QUOTA" if failure == "quota" else None
        return first

    # Interactions are credential/project scoped. Reserve starts a fresh
    # Interaction from a compact CE-OS checkpoint, never primary's ID.
    checkpoint = (
        "FAILOVER_CHECKPOINT:\n"
        f"primary_failure={failure}\n"
        f"primary_status={str(first.get('status') or '')[:160]}\n"
        f"primary_detail={str(first.get('error_detail') or first.get('reason') or '')[:480]}\n"
        "Resume the same bounded request from CE-OS evidence below.\n"
        + context[-8000:]
    )
    second = call(
        purpose=purpose,
        context=checkpoint,
        previous_interaction_id=None,
        system_instruction=system_instruction,
        api_key=reserve,
    )
    second["credential_slot"] = "reserve"
    second["failover_from"] = "primary"
    if session_id:
        append_event(
            session_id, "provider_attempt",
            credential_slot="reserve",
            ok=bool(second.get("ok")),
            status=second.get("status"),
            failure_class=classify_failure(second),
            interaction_id=second.get("interaction_id"),
            retry_after=second.get("retry_after"),
        )
    return second


def sleep_until_wake(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)
