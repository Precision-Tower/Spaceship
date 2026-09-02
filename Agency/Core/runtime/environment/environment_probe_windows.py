from __future__ import annotations

import getpass
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from Agency.Core.foundation.paths import DASHBOARD_ROOT

RunCommand = Callable[[list[str], float], subprocess.CompletedProcess[str]]


def run_subprocess(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


def _run(run_command: RunCommand, command: list[str], timeout: float) -> subprocess.CompletedProcess[str] | None:
    try:
        return run_command(command, timeout)
    except Exception:
        return None


def _python_environment() -> str | None:
    conda = os.environ.get("CONDA_DEFAULT_ENV")
    if conda:
        return conda
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        return Path(venv).name
    return Path(sys.prefix).name if sys.prefix else None


def _memory_total_mib(run_command: RunCommand, timeout: float) -> int | None:
    result = _run(run_command, ["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"], timeout)
    if not result or result.returncode != 0:
        return None
    for line in (result.stdout or "").splitlines():
        if line.startswith("TotalPhysicalMemory="):
            try:
                return int(int(line.split("=", 1)[1]) / 1024 / 1024)
            except ValueError:
                return None
    return None


def _gpu(run_command: RunCommand, timeout: float) -> dict[str, Any]:
    result = _run(run_command, [
        "nvidia-smi",
        "--query-gpu=name,memory.total,memory.used,memory.free,driver_version",
        "--format=csv,noheader,nounits",
    ], timeout)
    if not result or result.returncode != 0:
        return {
            "available": False,
            "vendor": None,
            "model": None,
            "cuda": False,
            "vram_mib": None,
            "probe_status": "unavailable",
            "probe_error": None if not result else (result.stderr or result.stdout or f"exit {result.returncode}").strip(),
        }
    parts = [part.strip() for part in next((row for row in result.stdout.splitlines() if row.strip()), "").split(",")]
    if len(parts) != 5:
        return {"available": False, "vendor": None, "model": None, "cuda": False, "vram_mib": None, "probe_status": "malformed", "probe_error": "expected 5 CSV fields from nvidia-smi"}
    try:
        return {
            "available": True,
            "vendor": "NVIDIA",
            "model": parts[0],
            "cuda": True,
            "vram_mib": int(parts[1]),
            "vram_used_mib": int(parts[2]),
            "vram_free_mib": int(parts[3]),
            "cuda_driver_version": parts[4],
            "probe_status": "detected",
            "probe_error": None,
        }
    except ValueError as exc:
        return {"available": False, "vendor": None, "model": None, "cuda": False, "vram_mib": None, "probe_status": "malformed", "probe_error": f"ValueError: {exc}"}


def _command_exists(run_command: RunCommand, command: str, timeout: float) -> bool:
    result = _run(run_command, ["where", command], timeout)
    return bool(result and result.returncode == 0 and (result.stdout or "").strip())


def _process_running(run_command: RunCommand, name: str, timeout: float) -> bool:
    result = _run(run_command, ["tasklist", "/FI", f"IMAGENAME eq {name}.exe"], timeout)
    return bool(result and result.returncode == 0 and name.lower() in (result.stdout or "").lower())


def probe(*, run_command: RunCommand | None = None, timeout_seconds: float = 2.0, workspace_root: Path | None = None) -> dict[str, Any]:
    runner = run_command or run_subprocess
    root = (workspace_root or DASHBOARD_ROOT).resolve()
    account = getpass.getuser()
    hostname = socket.gethostname()
    return {
        "identity": {
            "operator": {"account": account, "account_source": "operating_system" if account else "unresolved", "display_name": None, "display_name_source": "operator"},
            "machine": {
                "hostname": hostname,
                "hostname_source": "operating_system" if hostname else "unresolved",
                "operating_system": "windows",
                "architecture": platform.machine() or None,
                "python_executable": sys.executable,
                "python_environment": _python_environment(),
                "workspace": {"name": root.name, "root": str(root)},
            },
        },
        "capabilities": {
            "gpu": _gpu(runner, timeout_seconds),
            "cpu": {"logical_cores": os.cpu_count()},
            "memory": {"total_mib": _memory_total_mib(runner, timeout_seconds)},
            "runtimes": {
                "llama_server": _process_running(runner, "llama-server", timeout_seconds),
                "ollama": _command_exists(runner, "ollama", timeout_seconds),
                "vllm": _command_exists(runner, "vllm", timeout_seconds),
            },
            "network": {"available": _command_exists(runner, "ping", timeout_seconds)},
        },
    }