from __future__ import annotations

import datetime
import os
import time
from typing import Any


PACIFIC_TZ = "America/Los_Angeles"


def _pacific_date(now: datetime.datetime) -> str:
    # Android/Termux may not ship Python tzdata. The host libc timezone
    # database is authoritative when available, so use TZ/tzset without
    # introducing a Python package dependency.
    if not hasattr(time, "tzset"):
        raise RuntimeError("geminigo_pacific_timezone_unavailable")

    previous = os.environ.get("TZ")
    try:
        os.environ["TZ"] = PACIFIC_TZ
        time.tzset()
        seconds = now.timestamp()
        local = time.localtime(seconds)
        return f"{local.tm_year:04d}-{local.tm_mon:02d}-{local.tm_mday:02d}"
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


def quota_day(now: datetime.datetime | None = None) -> str:
    current = now or datetime.datetime.now(datetime.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=datetime.timezone.utc)
    return _pacific_date(current)


def needs_rotation(state: dict[str, Any], *, now: datetime.datetime | None = None) -> bool:
    interaction_id = state.get("interaction_id")
    if not interaction_id:
        return False
    return state.get("quota_day") != quota_day(now)


def clear_interaction(state: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        **state,
        "interaction_id": None,
        "quota_day": None,
        "session_status": "rotated",
        "rotation_reason": reason,
    }
