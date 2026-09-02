from __future__ import annotations

from Agency.Core.foundation.paths import (
    AGENCY_ROOT,
    CORE_ROOT,
    DASHBOARD_ROOT,
    DASHBOARD_UI_ROOT,
    MAIN_UI_ROOT,
    RUN_PY,
    SOURCE_UI_ROOT,
    SPACESHIP_ROOT,
    UI_ROOT,
    WORKSPACE_ROOT,
    PathResolver,
    ensure_spaceship_on_pythonpath,
    scan_files,
)

SPACESHIP_UI_ROOT = UI_ROOT
SPACESHIP_SHARED_ROOT = CORE_ROOT
PYTHONPATH_HINT = f"Dashboard root should be importable: {DASHBOARD_ROOT}"


class SharedBridgeError(RuntimeError):
    pass


def resolve_spaceship_root():
    return DASHBOARD_ROOT


__all__ = [
    "AGENCY_ROOT",
    "CORE_ROOT",
    "DASHBOARD_ROOT",
    "DASHBOARD_UI_ROOT",
    "MAIN_UI_ROOT",
    "RUN_PY",
    "SOURCE_UI_ROOT",
    "SPACESHIP_ROOT",
    "SPACESHIP_UI_ROOT",
    "SPACESHIP_SHARED_ROOT",
    "UI_ROOT",
    "WORKSPACE_ROOT",
    "PathResolver",
    "SharedBridgeError",
    "PYTHONPATH_HINT",
    "ensure_spaceship_on_pythonpath",
    "resolve_spaceship_root",
    "scan_files",
]
