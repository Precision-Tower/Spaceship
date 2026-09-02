"""Repository-local path helpers for CE-OS Phase 1."""

from __future__ import annotations

import os
from pathlib import Path

TERMUX_ROOT = Path(__file__).resolve().parents[2]
CEOS_ROOT = Path(__file__).resolve().parents[4]


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw:
        return Path(raw).expanduser()
    return default


def state_file() -> Path:
    return _path_from_env("CE_OS_STATE_FILE", CEOS_ROOT / "state" / "runtime" / "state.json")


def platform_manifest_file() -> Path:
    return _path_from_env("CE_OS_PLATFORM_MANIFEST", TERMUX_ROOT / "config" / "approved-platform.json")


def platform_state_file() -> Path:
    return _path_from_env("CE_OS_PLATFORM_STATE_FILE", CEOS_ROOT / "state" / "platform-state.env")
