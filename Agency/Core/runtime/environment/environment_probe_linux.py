from __future__ import annotations

import getpass
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from Agency.Core.foundation.paths import DASHBOARD_ROOT

RunCommand = Callable[[list[str], float], subprocess.CompletedProcess[str]]


def run_subprocess(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _run(run_command: RunCommand, command: list[str], timeout: float) -> subprocess.CompletedProcess[str] | None:
    try:
        return run_command(command, timeout)
    except Exception:
        return None


def _parse_nvidia(stdout: str) -> dict[str, Any]:
    line = next((row.strip() for row in stdout.splitlines() if row.strip()), "")
    parts = [part.strip() for part in line.split(",")]
    if len(parts) != 5:
        return {
            "available": False,
            "cuda": False,
            "probe_status": "malformed",
            "probe_error": "expected 5 CSV fields from nvidia-smi",
        }
    name, total, used, free, driver = parts
    try:
        total_mib = int(total)
        used_mib = int(used)
        free_mib = int(free)
    except ValueError as exc:
        return {
            "available": False,
            "cuda": False,
            "probe_status": "malformed",
            "probe_error": f"ValueError: {exc}",
        }
    return {
        "available": True,
        "vendor": "NVIDIA",
        "model": name,
        "cuda": True,
        "vram_mib": total_mib,
        "vram_used_mib": used_mib,
        "vram_free_mib": free_mib,
        "cuda_driver_version": driver,
        "probe_status": "detected",
        "probe_error": None,
    }


def _gpu(run_command: RunCommand, timeout: float) -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.used,memory.free,driver_version",
        "--format=csv,noheader,nounits",
    ]
    result = _run(run_command, command, timeout)
    if result is None:
        return {
            "available": False,
            "vendor": None,
            "model": None,
            "cuda": False,
            "vram_mib": None,
            "probe_status": "unavailable",
            "probe_error": "nvidia-smi unavailable",
        }
    if result.returncode != 0:
        return {
            "available": False,
            "vendor": None,
            "model": None,
            "cuda": False,
            "vram_mib": None,
            "probe_status": "unavailable",
            "probe_error": (result.stderr or result.stdout or f"exit {result.returncode}").strip(),
        }
    parsed = _parse_nvidia(result.stdout or "")
    parsed.setdefault("vendor", "NVIDIA")
    parsed.setdefault("model", None)
    parsed.setdefault("vram_mib", None)
    return parsed


def _memory_total_mib() -> int | None:
    meminfo = Path("/proc/meminfo")
    try:
        for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                return int(int(parts[1]) / 1024)
    except Exception:
        return None
    return None


def _process_info(
    run_command: RunCommand,
    process: str,
    timeout: float,
) -> dict[str, Any]:
    result = _run(run_command, ["pgrep", "-af", process], timeout)
    if not result or result.returncode != 0:
        return {
            "running": False,
            "pid": None,
            "command": None,
            "arguments": [],
        }

    line = next(
        (row.strip() for row in (result.stdout or "").splitlines() if row.strip()),
        "",
    )
    if not line:
        return {
            "running": False,
            "pid": None,
            "command": None,
            "arguments": [],
        }

    pid_text, _, command = line.partition(" ")
    try:
        pid = int(pid_text)
    except ValueError:
        pid = None

    try:
        arguments = shlex.split(command)
    except ValueError:
        arguments = command.split()

    return {
        "running": True,
        "pid": pid,
        "command": command or None,
        "arguments": arguments,
    }


def _argument_value(
    arguments: list[str],
    *names: str,
) -> str | None:
    for index, argument in enumerate(arguments):
        for name in names:
            if argument == name and index + 1 < len(arguments):
                return arguments[index + 1]
            prefix = f"{name}="
            if argument.startswith(prefix):
                return argument[len(prefix):]
    return None


def _integer_argument(
    arguments: list[str],
    *names: str,
) -> int | None:
    value = _argument_value(arguments, *names)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _probe_json(url: str, timeout: float) -> tuple[dict[str, Any] | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"{type(exc).__name__}: {exc}"

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        return None, f"JSONDecodeError: {exc}"

    if not isinstance(payload, dict):
        return None, "unexpected_non_object_response"

    return payload, None


def _llama_server(
    run_command: RunCommand,
    timeout: float,
) -> dict[str, Any]:
    process = _process_info(run_command, "llama-server", timeout)
    arguments = list(process.get("arguments") or [])

    host = _argument_value(arguments, "--host") or "127.0.0.1"
    port = _integer_argument(arguments, "--port") or 8081

    probe_host = host
    if probe_host in {"0.0.0.0", "::", "[::]"}:
        probe_host = "127.0.0.1"

    endpoint = f"http://{probe_host}:{port}"
    configured_model = _argument_value(arguments, "--model", "-m")
    context_tokens = _integer_argument(arguments, "--ctx-size", "-c")
    gpu_layers = _integer_argument(
        arguments,
        "--n-gpu-layers",
        "--gpu-layers",
        "-ngl",
    )

    if not process["running"]:
        return {
            "installed": _command_exists(run_command, "llama-server", timeout),
            "running": False,
            "reachable": False,
            "endpoint": endpoint,
            "model": configured_model,
            "context_tokens": context_tokens,
            "gpu_layers": gpu_layers,
            "process": process,
            "probe_status": "not_running",
            "probe_error": None,
        }

    models_payload, probe_error = _probe_json(
        f"{endpoint}/v1/models",
        timeout,
    )

    discovered_model = None
    if models_payload is not None:
        models = models_payload.get("data")
        if isinstance(models, list) and models:
            first = models[0]
            if isinstance(first, dict):
                discovered_model = first.get("id")

    reachable = models_payload is not None

    return {
        "installed": True,
        "running": True,
        "reachable": reachable,
        "endpoint": endpoint,
        "model": discovered_model or configured_model,
        "configured_model": configured_model,
        "context_tokens": context_tokens,
        "gpu_layers": gpu_layers,
        "process": process,
        "probe_status": "ready" if reachable else "unreachable",
        "probe_error": probe_error,
    }


def _command_exists(run_command: RunCommand, command: str, timeout: float) -> bool:
    result = _run(run_command, ["sh", "-lc", f"command -v {command}"], timeout)
    return bool(result and result.returncode == 0 and (result.stdout or "").strip())


def _network_available(run_command: RunCommand, timeout: float) -> bool:
    result = _run(run_command, ["sh", "-lc", "ip route show default >/dev/null 2>&1"], timeout)
    return bool(result and result.returncode == 0)


def _python_environment() -> str | None:
    conda = os.environ.get("CONDA_DEFAULT_ENV")
    if conda:
        return conda
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        return Path(venv).name
    return Path(sys.prefix).name if sys.prefix else None


def probe(*, run_command: RunCommand | None = None, timeout_seconds: float = 2.0, workspace_root: Path | None = None) -> dict[str, Any]:
    runner = run_command or run_subprocess
    root = (workspace_root or DASHBOARD_ROOT).resolve()
    account = getpass.getuser()
    hostname = socket.gethostname()
    return {
        "identity": {
            "operator": {
                "account": account,
                "account_source": "operating_system" if account else "unresolved",
                "display_name": None,
                "display_name_source": "operator",
            },
            "machine": {
                "hostname": hostname,
                "hostname_source": "operating_system" if hostname else "unresolved",
                "operating_system": "linux",
                "architecture": platform.machine() or None,
                "python_executable": sys.executable,
                "python_environment": _python_environment(),
                "workspace": {
                    "name": root.name,
                    "root": str(root),
                },
            },
        },
        "capabilities": {
            "gpu": _gpu(runner, timeout_seconds),
            "cpu": {
                "logical_cores": os.cpu_count(),
            },
            "memory": {
                "total_mib": _memory_total_mib(),
            },
            "runtimes": {
                "llama_server": _llama_server(runner, timeout_seconds),
                "ollama": {
                    "installed": _command_exists(runner, "ollama", timeout_seconds),
                },
                "vllm": {
                    "installed": _command_exists(runner, "vllm", timeout_seconds),
                },
            },
            "network": {
                "available": _network_available(runner, timeout_seconds),
            },
        },
    }