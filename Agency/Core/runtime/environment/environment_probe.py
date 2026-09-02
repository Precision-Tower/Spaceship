from __future__ import annotations

from pathlib import Path
from typing import Any

from .environment import (
    EnvironmentManifest,
    ResolvedRuntime,
    bootstrap_environment_manifest,
    discover_environment,
    environment_manifest_path,
    environment_payload_for_ui,
    load_environment_manifest,
    load_or_create_environment_manifest,
    refresh_volatile_capabilities,
    resolve_runtime_from_capabilities,
)


def probe_runtime_environment(
    *,
    run_command: Any = None,
    timeout_seconds: float = 2.0,
    platform_name: str | None = None,
    manifest_path: Path | None = None,
) -> EnvironmentManifest:
    return bootstrap_environment_manifest(
        path=manifest_path,
        platform_name=platform_name,
        run_command=run_command,
        timeout_seconds=timeout_seconds,
        interactive=False,
    )