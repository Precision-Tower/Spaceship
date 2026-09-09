from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


def credential_path() -> Path:
    override = os.getenv("GEMINIGO_CREDENTIALS_FILE")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parent / "config" / "credentials.json"


def load_credentials() -> dict[str, Any]:
    path = credential_path()
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "slots": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported_geminigo_credentials_schema")
    slots = payload.get("slots")
    if not isinstance(slots, dict):
        raise ValueError("invalid_geminigo_credentials_slots")
    return payload


def api_key(slot: str) -> str | None:
    env_name = {
        "primary": "GEMINI_API_KEY",
        "reserve": "GEMINI_API_KEY_RESERVE",
    }.get(slot)
    if env_name:
        value = os.getenv(env_name)
        if value:
            return value

    entry = load_credentials().get("slots", {}).get(slot, {})
    if not isinstance(entry, dict):
        return None
    value = entry.get("api_key")
    return str(value).strip() if value else None


def configured_slots() -> list[str]:
    return [slot for slot in ("primary", "reserve") if api_key(slot)]


def public_status() -> dict[str, Any]:
    configured = set(configured_slots())
    return {
        "credential_file_present": credential_path().is_file(),
        "primary_configured": "primary" in configured,
        "reserve_configured": "reserve" in configured,
    }
