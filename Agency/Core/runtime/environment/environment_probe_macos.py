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
    result = _run(run_command, ["sysctl", "-n", "hw.memsize"], timeout)
    if not result or result.returncode != 0:
        return None
    try:
        return int(int((result.stdout or "").strip()) / 1024 / 1024)
    except ValueError:
        return None


def _command_exists(run_command: RunCommand, command: str, timeout: float) -> bool:
    result = _run(run_command, ["sh", "-lc", f"command -v {command}"], timeout)
    return bool(result and result.returncode == 0 and (result.stdout or "").strip())


def _process_running(run_command: RunCommand, name: str, timeout: float) -> bool:
    result = _run(run_command, ["pgrep", "-af", name], timeout)
    return bool(result and result.returncode == 0 and (result.stdout or "").strip())


def _gpu() -> dict[str, Any]:
    return {
        "available": False,
        "vendor": None,
        "model": None,
        "cuda": False,
        "vram_mib": None,
        "probe_status": "not_supported",
        "probe_error": None,
    }


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
                "operating_system": "macos",
                "architecture": platform.machine() or None,
                "python_executable": sys.executable,
                "python_environment": _python_environment(),
                "workspace": {"name": root.name, "root": str(root)},
            },
        },
        "capabilities": {
            "gpu": _gpu(),
            "cpu": {"logical_cores": os.cpu_count()},
            "memory": {"total_mib": _memory_total_mib(runner, timeout_seconds)},
            "runtimes": {
                "llama_server": _process_running(runner, "llama-server", timeout_seconds),
                "ollama": _command_exists(runner, "ollama", timeout_seconds),
                "vllm": _command_exists(runner, "vllm", timeout_seconds),
            },
            "network": {"available": _command_exists(runner, "route", timeout_seconds)},
        },
    }