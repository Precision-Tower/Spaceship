from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from Agency.GeminiGo.assignment import select_assignment
from Agency.GeminiGo.credentials import public_status
from Agency.GeminiGo.state import load_state, recent_events


DEFAULT_SESSION = "daily"


def _service_status() -> str:
    prefix = subprocess.run(
        ["sh", "-lc", 'printf %s "$PREFIX"'],
        text=True, capture_output=True, check=False,
    ).stdout.strip()
    if not prefix:
        return "UNKNOWN"
    service = Path(prefix) / "var/service/ce-os-geminigo"
    if not service.exists():
        return "NOT_INSTALLED"
    result = subprocess.run(
        ["sv", "status", str(service)],
        text=True, capture_output=True, check=False,
    )
    text = (result.stdout or result.stderr).strip()
    if text.startswith("run:"):
        return "RUNNING"
    if text.startswith("down:"):
        return "DOWN"
    return "UNKNOWN"


def _failure_status(event: dict[str, Any]) -> str:
    status = str(event.get("status") or "").upper()
    detail = str(event.get("error_detail") or event.get("reason") or "").upper()
    text = status + " " + detail
    failure = str(event.get("failure_class") or "").lower()
    if failure == "quota" or "429" in text or "RESOURCE_EXHAUSTED" in text or "QUOTA" in text:
        return "QUOTA_EXHAUSTED"
    if "RATE" in text and "LIMIT" in text:
        return "RATE_LIMITED"
    if failure == "auth" or "401" in text or "403" in text or "AUTH" in text or "CREDENTIAL" in text:
        return "AUTH_FAILED"
    if failure == "network":
        return "NETWORK_FAILED"
    if "NETWORK" in text or "CONNECTION" in text or "DNS" in text:
        return "NETWORK_FAILED"
    if "UNAVAILABLE" in text or "503" in text:
        return "PROVIDER_UNAVAILABLE"
    return "UNKNOWN"


def _slot_status(slot: str, events: list[dict[str, Any]], configured: bool) -> dict[str, Any]:
    attempts = [
        event for event in events
        if event.get("event") == "provider_attempt"
        and event.get("credential_slot") == slot
    ]
    if not configured:
        provider = "UNCONFIGURED"
    elif not attempts:
        provider = "UNKNOWN"
    elif attempts[-1].get("ok"):
        provider = "AVAILABLE"
    else:
        provider = _failure_status(attempts[-1])
    successes = [event for event in attempts if event.get("ok")]
    return {
        "credential_slot": slot,
        "configured": configured,
        "provider_status": provider,
        "last_attempt": attempts[-1].get("timestamp") if attempts else None,
        "last_success": successes[-1].get("timestamp") if successes else None,
        "last_failure_class": (
            attempts[-1].get("failure_class")
            if attempts and not attempts[-1].get("ok")
            else None
        ),
        "interaction_id": attempts[-1].get("interaction_id") if attempts else None,
        "retry_after": attempts[-1].get("retry_after") if attempts else None,
        "eligible": configured,
    }


def snapshot(session_id: str = DEFAULT_SESSION) -> dict[str, Any]:
    state = load_state(session_id)
    events = recent_events(session_id, limit=200)
    credentials = public_status()
    assignment = select_assignment()
    thing1 = _slot_status("primary", events, bool(credentials["primary_configured"]))
    thing2 = _slot_status("reserve", events, bool(credentials["reserve_configured"]))
    session_status = str(state.get("session_status") or "unknown").upper()
    worker = {
        "WORKING": "WORKING",
        "READY": "READY",
        "PROVIDER_WAIT": "PROVIDER_WAIT",
        "STOPPED": "STOPPED",
        "IDLE": "IDLE",
    }.get(session_status, "UNKNOWN")
    return {
        "service": _service_status(),
        "assignment": assignment.get("identity") if assignment else None,
        "worker": worker,
        "stop_reason": state.get("stop_reason"),
        "sleep_reason": state.get("sleep_reason"),
        "work_packet_id": state.get("work_packet_id"),
        "last_purpose": state.get("last_purpose"),
        "last_updated": state.get("updated_at"),
        "thing_1": thing1,
        "thing_2": thing2,
    }


def _render_slot(label: str, data: dict[str, Any]) -> list[str]:
    return [
        label,
        f"provider: {data['provider_status']}",
        f"configured: {str(data['configured']).lower()}",
        f"last_success: {data['last_success'] or 'never'}",
        f"last_attempt: {data['last_attempt'] or 'never'}",
        f"failure: {data['last_failure_class'] or 'none'}",
        f"interaction: {data['interaction_id'] or 'none'}",
    ]


def render(data: dict[str, Any]) -> str:
    lines = [
        "GeminiGo",
        f"service: {data['service']}",
        f"assignment: {data['assignment'] or 'none'}",
        f"worker: {data['worker']}",
        f"stop_reason: {data['stop_reason'] or 'none'}",
        f"work_packet: {data['work_packet_id'] or 'none'}",
        "",
    ]
    lines += _render_slot("Thing 1", data["thing_1"])
    lines += [""] + _render_slot("Thing 2", data["thing_2"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m Agency.GeminiGo.status")
    parser.add_argument("--session", default=DEFAULT_SESSION)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = snapshot(args.session)
    print(json.dumps(data, indent=2) if args.json else render(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
