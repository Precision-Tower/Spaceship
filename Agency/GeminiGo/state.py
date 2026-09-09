from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_SCHEMA_VERSION = 2


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def state_root() -> Path:
    return Path.home() / ".ce-os" / "geminigo"


def session_dir(session_id: str) -> Path:
    token = "".join(ch for ch in str(session_id).strip() if ch.isalnum() or ch in "._-")
    if not token:
        raise ValueError("geminigo_session_id_required")
    return state_root() / token


def state_path(session_id: str) -> Path:
    return session_dir(session_id) / "state.json"


def journal_path(session_id: str) -> Path:
    return session_dir(session_id) / "journal.jsonl"


def initial_state(session_id: str) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "session_id": session_id,
        "turn": 0,
        "mission_id": None,
        "work_packet_id": None,
        "last_purpose": None,
        "last_response": None,
        "interaction_id": None,
        "quota_day": None,
        "session_status": "idle",
        "stop_reason": None,
        "last_action_fingerprint": None,
        "repeated_action_count": 0,
        "updated_at": _now(),
        "authority": "geminigo_continuity_not_core_work_authority",
    }


def load_state(session_id: str) -> dict[str, Any]:
    path = state_path(session_id)
    if not path.exists():
        return initial_state(session_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version == 1:
        data = {
            **data,
            "schema_version": STATE_SCHEMA_VERSION,
            "interaction_id": None,
            "quota_day": None,
            "session_status": "idle",
            "stop_reason": None,
        }
    elif version != STATE_SCHEMA_VERSION:
        raise ValueError("unsupported_geminigo_state_schema")
    if data.get("session_id") != session_id:
        raise ValueError("geminigo_state_session_mismatch")
    return data


def save_state(session_id: str, payload: dict[str, Any]) -> Path:
    path = state_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    data["schema_version"] = STATE_SCHEMA_VERSION
    data["session_id"] = session_id
    data["updated_at"] = _now()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def append_event(session_id: str, event: str, **fields: Any) -> Path:
    path = journal_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": _now(),
        "session_id": session_id,
        "event": event,
        **fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def recent_events(session_id: str, *, limit: int = 12) -> list[dict[str, Any]]:
    path = journal_path(session_id)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines[-max(1, limit):]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events
