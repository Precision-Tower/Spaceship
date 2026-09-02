from __future__ import annotations

import importlib
import platform
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.foundation.paths import (
    DASHBOARD_ROOT,
    ENVIRONMENT_MANIFEST_PATH as DEFAULT_ENVIRONMENT_MANIFEST_PATH,
    stable_path,
)

RUNTIME_ROOT = Path(__file__).resolve().parent
ENVIRONMENT_MANIFEST_PATH = DEFAULT_ENVIRONMENT_MANIFEST_PATH
ENVIRONMENT_MANIFEST_SCHEMA_VERSION = 1
ENVIRONMENT_MANIFEST_AUTHORITY = "environment_identity_runtime_capability_authority"


@dataclass(frozen=True)
class ResolvedRuntime:
    backend: str
    accelerator: str
    inference_route: str
    execution_mode: str
    selection_reason: list[str]
    router_runtime: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EnvironmentManifest:
    schema_version: int
    authority: str
    created_at: str
    updated_at: str
    identity: dict[str, Any]
    capabilities: dict[str, Any]
    resolved_runtime: ResolvedRuntime
    source: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["resolved_runtime"] = self.resolved_runtime.to_dict()
        return {"EnvironmentManifest": payload}


InputFunc = Callable[[str], str]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def environment_manifest_path(path: Path | None = None) -> Path:
    return path or ENVIRONMENT_MANIFEST_PATH


def _platform_key(platform_name: str | None = None) -> str:
    raw = (platform_name or platform.system()).lower()
    if raw.startswith("linux"):
        return "linux"
    if raw.startswith("win"):
        return "windows"
    if raw in {"darwin", "mac", "macos"}:
        return "macos"
    return "linux"


def _adapter_module(platform_name: str | None = None):
    key = _platform_key(platform_name)
    return importlib.import_module(f"Agency.Core.runtime.environment.environment_probe_{key}")


def _as_bool(value: Any) -> bool:
    return bool(value)


def _runtime_ready(value: Any) -> bool:
    if not isinstance(value, dict):
        return bool(value)

    if "running" in value:
        return bool(value.get("running"))

    if "reachable" in value:
        return bool(value.get("reachable"))

    return bool(value.get("installed"))


def _get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def resolve_runtime_from_capabilities(
    capabilities: dict[str, Any],
) -> ResolvedRuntime:
    gpu_available = _as_bool(_get(capabilities, "gpu", "available"))
    cuda_available = _as_bool(_get(capabilities, "gpu", "cuda"))
    llama_server = _runtime_ready(
        _get(capabilities, "runtimes", "llama_server")
    )
    ollama = _runtime_ready(
        _get(capabilities, "runtimes", "ollama")
    )
    vllm = _runtime_ready(
        _get(capabilities, "runtimes", "vllm")
    )

    if llama_server and cuda_available:
        return ResolvedRuntime(
            backend="llama_server",
            accelerator="cuda",
            inference_route="local",
            execution_mode="local_gpu",
            selection_reason=["CUDA available", "llama-server running"],
            router_runtime="llama_server",
        )

    if llama_server:
        return ResolvedRuntime(
            backend="llama_server",
            accelerator="cpu",
            inference_route="local",
            execution_mode="local_cpu",
            selection_reason=["llama-server running", "CUDA unavailable"],
            router_runtime="llama_server",
        )

    if vllm and cuda_available:
        return ResolvedRuntime(
            backend="vllm",
            accelerator="cuda",
            inference_route="local",
            execution_mode="local_gpu",
            selection_reason=["CUDA available", "vLLM runtime detected"],
        )

    if ollama:
        return ResolvedRuntime(
            backend="ollama",
            accelerator="gpu" if gpu_available else "cpu",
            inference_route="local",
            execution_mode="local_gpu" if gpu_available else "local_cpu",
            selection_reason=["Ollama runtime detected"],
        )

    return ResolvedRuntime(
        backend="gguf",
        accelerator="cpu",
        inference_route="local",
        execution_mode="local_cpu",
        selection_reason=["No model server detected", "using local GGUF fallback contract"],
    )


def complete_operator_identity(
    identity: dict[str, Any],
    *,
    interactive: bool,
    input_func: InputFunc = input,
) -> dict[str, Any]:
    if not interactive:
        return identity

    operator = dict(identity.get("operator") or {})
    account = str(operator.get("account") or "").strip()
    if account:
        answer = input_func(f"Detected account: {account}\nUse this as your operator identity? [Y/n] ").strip().lower()
        if answer in {"n", "no"}:
            account = input_func("What should CE-OS call you?\nAccount: ").strip()
            operator["account_source"] = "operator"
    else:
        account = input_func("What should CE-OS call you?\nAccount: ").strip()
        operator["account_source"] = "operator" if account else "unresolved"
    operator["account"] = account or None

    if not operator.get("display_name"):
        display = input_func("Display name (optional): ").strip()
        if display:
            operator["display_name"] = display
            operator["display_name_source"] = "operator"

    identity = dict(identity)
    identity["operator"] = operator
    return identity


def discover_environment(
    *,
    platform_name: str | None = None,
    run_command: Any = None,
    timeout_seconds: float = 2.0,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    adapter = _adapter_module(platform_name)
    return adapter.probe(
        run_command=run_command,
        timeout_seconds=timeout_seconds,
        workspace_root=workspace_root or DASHBOARD_ROOT,
    )


def build_environment_manifest(
    discovered: dict[str, Any],
    *,
    existing: EnvironmentManifest | None = None,
    interactive: bool = False,
    input_func: InputFunc = input,
    platform_name: str | None = None,
) -> EnvironmentManifest:
    timestamp = _now()
    created_at = existing.created_at if existing is not None else timestamp
    identity = complete_operator_identity(
        dict(discovered.get("identity") or {}),
        interactive=interactive,
        input_func=input_func,
    )
    capabilities = dict(discovered.get("capabilities") or {})
    resolved = resolve_runtime_from_capabilities(capabilities)
    return EnvironmentManifest(
        schema_version=ENVIRONMENT_MANIFEST_SCHEMA_VERSION,
        authority=ENVIRONMENT_MANIFEST_AUTHORITY,
        created_at=created_at,
        updated_at=timestamp,
        identity=identity,
        capabilities=capabilities,
        resolved_runtime=resolved,
        source={
            "platform_adapter": _platform_key(platform_name),
            "workspace": stable_path(DASHBOARD_ROOT),
        },
    )


def load_environment_manifest(path: Path | None = None) -> EnvironmentManifest:
    manifest_path = environment_manifest_path(path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    root = data.get("EnvironmentManifest") if isinstance(data, dict) else {}
    if not isinstance(root, dict):
        raise ValueError(f"invalid_environment_manifest: {manifest_path}")
    runtime_data = root.get("resolved_runtime") or {}
    if not isinstance(runtime_data, dict):
        runtime_data = {}
    return EnvironmentManifest(
        schema_version=int(root.get("schema_version") or ENVIRONMENT_MANIFEST_SCHEMA_VERSION),
        authority=str(root.get("authority") or ENVIRONMENT_MANIFEST_AUTHORITY),
        created_at=str(root.get("created_at") or ""),
        updated_at=str(root.get("updated_at") or ""),
        identity=dict(root.get("identity") or {}),
        capabilities=dict(root.get("capabilities") or {}),
        resolved_runtime=ResolvedRuntime(
            backend=str(runtime_data.get("backend") or "gguf"),
            accelerator=str(runtime_data.get("accelerator") or "cpu"),
            inference_route=str(runtime_data.get("inference_route") or "local"),
            execution_mode=str(runtime_data.get("execution_mode") or "local_cpu"),
            selection_reason=list(runtime_data.get("selection_reason") or []),
            router_runtime=runtime_data.get("router_runtime"),
        ),
        source=dict(root.get("source") or {}),
    )


def save_environment_manifest(manifest: EnvironmentManifest, path: Path | None = None) -> Path:
    manifest_path = environment_manifest_path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(manifest.to_dict(), sort_keys=False),
        encoding="utf-8",
    )
    return manifest_path


def bootstrap_environment_manifest(
    *,
    path: Path | None = None,
    platform_name: str | None = None,
    run_command: Any = None,
    timeout_seconds: float = 2.0,
    interactive: bool = False,
    input_func: InputFunc = input,
) -> EnvironmentManifest:
    discovered = discover_environment(
        platform_name=platform_name,
        run_command=run_command,
        timeout_seconds=timeout_seconds,
    )
    manifest = build_environment_manifest(
        discovered,
        interactive=interactive,
        input_func=input_func,
        platform_name=platform_name,
    )
    save_environment_manifest(manifest, path)
    return manifest


def load_or_create_environment_manifest(
    *,
    path: Path | None = None,
    platform_name: str | None = None,
    run_command: Any = None,
    timeout_seconds: float = 2.0,
    interactive: bool = False,
    input_func: InputFunc = input,
) -> EnvironmentManifest:
    manifest_path = environment_manifest_path(path)
    if manifest_path.exists():
        return load_environment_manifest(manifest_path)
    return bootstrap_environment_manifest(
        path=manifest_path,
        platform_name=platform_name,
        run_command=run_command,
        timeout_seconds=timeout_seconds,
        interactive=interactive,
        input_func=input_func,
    )


def refresh_volatile_capabilities(
    manifest: EnvironmentManifest,
    *,
    platform_name: str | None = None,
    run_command: Any = None,
    timeout_seconds: float = 2.0,
) -> EnvironmentManifest:
    discovered = discover_environment(
        platform_name=platform_name,
        run_command=run_command,
        timeout_seconds=timeout_seconds,
    )
    refreshed = build_environment_manifest(
        discovered,
        existing=manifest,
        interactive=False,
        platform_name=platform_name,
    )
    return refreshed


def environment_payload_for_ui(path: Path | None = None) -> dict[str, Any]:
    manifest = load_or_create_environment_manifest(path=path, interactive=False)
    return manifest.to_dict()["EnvironmentManifest"]

def normalize_runtime_endpoint(value: Any) -> str | None:
    if value is None:
        return None

    endpoint = str(value).strip().rstrip("/")
    return endpoint or None


def runtime_configuration_drift(
    configured: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    comparable_fields = (
        "endpoint",
        "model",
        "context_tokens",
        "gpu_layers",
    )

    differences: dict[str, dict[str, Any]] = {}

    for field in comparable_fields:
        configured_value = configured.get(field)
        observed_value = observed.get(field)

        if field == "endpoint":
            configured_value = normalize_runtime_endpoint(
                configured_value
            )
            observed_value = normalize_runtime_endpoint(
                observed_value
            )

        if configured_value is None or observed_value is None:
            continue

        if configured_value != observed_value:
            differences[field] = {
                "configured": configured_value,
                "observed": observed_value,
            }

    return {
        "detected": bool(differences),
        "fields": differences,
    }

