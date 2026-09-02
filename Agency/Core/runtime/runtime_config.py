from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Agency.Core.foundation.paths import MODEL_SERVER_LOG_PATH, MODEL_SERVER_PID_PATH

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = DASHBOARD_ROOT.parent
RUNTIME_ROOT = Path(__file__).resolve().parent
RUNTIME_PROFILES = RUNTIME_ROOT / "runtime_profiles.yaml"
LEGACY_PROFILES = RUNTIME_ROOT / "profiles.yaml"
RUNTIME_PROFILES_ENV = "AGENCY_RUNTIME_PROFILES"
MODEL_FILENAME = "Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf"
DEFAULT_MODEL_PATH_KEY = "qwen_1_5b_gguf"
DEFAULT_SERVER_PATH = Path("/home/spaztic/Core/tools/llama.cpp-cuda/build/bin/llama-server")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8081
DEFAULT_CONTEXT_TOKENS = 2048
DEFAULT_GPU_LAYERS = 99


@dataclass(frozen=True)
class ModelServerConfig:
    server_path: Path
    model_path: Path
    host: str
    port: int
    ctx_size: int
    gpu_layers: int
    pid_path: Path
    log_path: Path
    runtime_profiles_path: Path
    profile_name: str
    model_path_source: str
    context_source: str
    gpu_layers_source: str
    server_path_source: str

    @property
    def endpoint(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def chat_endpoint(self) -> str:
        return f"{self.endpoint}/v1/chat/completions"


def runtime_profiles_path() -> Path:
    configured = os.environ.get(RUNTIME_PROFILES_ENV)
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else (DASHBOARD_ROOT / path).resolve()
    return RUNTIME_PROFILES


def profile_paths(path: Path | None = None) -> tuple[Path, ...]:
    primary = path or runtime_profiles_path()
    return (primary, LEGACY_PROFILES) if primary != LEGACY_PROFILES else (primary,)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def active_profile(path: Path | None = None) -> tuple[dict[str, Any], str, Path]:
    for candidate in profile_paths(path):
        root = _load_yaml(candidate).get("RuntimeProfiles") or {}
        if not isinstance(root, dict):
            continue
        active_name = str(root.get("active_profile") or "").strip()
        profiles = root.get("profiles") or {}
        if not active_name or not isinstance(profiles, dict):
            continue
        profile = profiles.get(active_name) or {}
        if isinstance(profile, dict):
            return profile, active_name, candidate
    return {}, "", profile_paths(path)[0]


def active_model_execution(path: Path | None = None) -> dict[str, Any]:
    profile, _name, _source_path = active_profile(path)
    model_execution = profile.get("model_execution") or {}
    return model_execution if isinstance(model_execution, dict) else {}


def configured_max_tokens(key: str, fallback: int, path: Path | None = None) -> int:
    value = active_model_execution(path).get(key)
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _configured_path_candidates(value: str) -> list[Path]:
    configured = Path(value).expanduser()
    if configured.is_absolute():
        return [configured]
    return [
        DASHBOARD_ROOT / configured,
        WORKSPACE_ROOT / configured,
        WORKSPACE_ROOT / "Spaceship" / configured,
    ]


def fallback_model_candidates() -> list[Path]:
    return [
        WORKSPACE_ROOT / "Spaceship" / "local" / MODEL_FILENAME,
        DASHBOARD_ROOT / "local" / MODEL_FILENAME,
    ]


def configured_model_path_value(path: Path | None = None, *, key: str = DEFAULT_MODEL_PATH_KEY) -> str | None:
    profile, _name, _source_path = active_profile(path)
    paths = profile.get("paths") or {}
    if not isinstance(paths, dict):
        return None
    value = paths.get(key)
    return str(value) if value else None


def resolve_model_path(path: Path | None = None, *, key: str = DEFAULT_MODEL_PATH_KEY) -> tuple[Path, str, list[Path]]:
    checked: list[Path] = []
    configured = configured_model_path_value(path, key=key)
    if configured:
        candidates = _configured_path_candidates(configured)
        checked.extend(candidates)
        for candidate in candidates:
            if candidate.is_file():
                return candidate, "configured", checked

    fallbacks = fallback_model_candidates()
    checked.extend(fallbacks)
    for candidate in fallbacks:
        if candidate.is_file():
            return candidate, "fallback", checked

    missing_target = checked[0] if checked else fallbacks[0]
    return missing_target, "missing", checked or fallbacks


def _int_setting(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _path_setting(value: Any, fallback: Path) -> tuple[Path, str]:
    if value:
        raw = Path(str(value)).expanduser()
        if raw.is_absolute():
            return raw, "configured"
        return (DASHBOARD_ROOT / raw).resolve(), "configured"
    return fallback, "fallback"


def load_model_server_config(path: Path | None = None) -> ModelServerConfig:
    profile, profile_name, source_path = active_profile(path)
    model_execution = profile.get("model_execution") or {}
    if not isinstance(model_execution, dict):
        model_execution = {}
    model_server = profile.get("model_server") or {}
    if not isinstance(model_server, dict):
        model_server = {}

    model_key = str(model_server.get("model_path_key") or DEFAULT_MODEL_PATH_KEY)
    if model_server.get("model_path"):
        model_path, model_path_source = _path_setting(model_server.get("model_path"), fallback_model_candidates()[0])
        checked = _configured_path_candidates(str(model_server.get("model_path")))
        if not model_path.is_file():
            fallback, fallback_source, checked = resolve_model_path(source_path, key=model_key)
            model_path = fallback
            model_path_source = fallback_source
    else:
        model_path, model_path_source, checked = resolve_model_path(source_path, key=model_key)
    del checked

    context_value = model_server.get("context_tokens", model_execution.get("recommended_context_tokens"))
    context_source = "model_server.context_tokens" if model_server.get("context_tokens") is not None else "model_execution.recommended_context_tokens"
    if context_value is None:
        context_source = "fallback"
    ctx_size = _int_setting(context_value, DEFAULT_CONTEXT_TOKENS)

    gpu_value = model_server.get("gpu_layers", model_server.get("n_gpu_layers"))
    gpu_source = "model_server.gpu_layers" if gpu_value is not None else "fallback"
    gpu_layers = _int_setting(gpu_value, DEFAULT_GPU_LAYERS)

    server_path, server_path_source = _path_setting(model_server.get("server_path"), DEFAULT_SERVER_PATH)
    host = str(model_server.get("host") or DEFAULT_HOST)
    port = _int_setting(model_server.get("port"), DEFAULT_PORT)
    pid_path, _pid_source = _path_setting(model_server.get("pid_path"), MODEL_SERVER_PID_PATH)
    log_path, _log_source = _path_setting(model_server.get("log_path"), MODEL_SERVER_LOG_PATH)

    return ModelServerConfig(
        server_path=server_path,
        model_path=model_path,
        host=host,
        port=port,
        ctx_size=ctx_size,
        gpu_layers=gpu_layers,
        pid_path=pid_path,
        log_path=log_path,
        runtime_profiles_path=source_path,
        profile_name=profile_name,
        model_path_source=model_path_source,
        context_source=context_source,
        gpu_layers_source=gpu_source,
        server_path_source=server_path_source,
    )


def effective_model_context_tokens(path: Path | None = None) -> int:
    return load_model_server_config(path).ctx_size
