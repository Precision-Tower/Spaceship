"""Shared agent-name normalization for engineering capabilities."""
from __future__ import annotations

import re


AGENT_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")


def normalize_agent_name(raw: str) -> str:
    cleaned = AGENT_NAME_RE.sub("", raw.strip())
    if not cleaned:
        raise ValueError("agent_name_empty")
    return cleaned[:1].upper() + cleaned[1:]
