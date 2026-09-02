from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from Agency.Core.work.missions.operations.io import ROOT

VECTOR_RETRIEVAL_TASK_IDS = {
    "task_006_vector_retrieval_smoke_test",
    "task_007_vector_retrieval_yaml_query",
    "task_008_vector_retrieval_godot_query",
}


def run_command(command: list[str], cwd: Path = ROOT) -> dict:
    start = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - start

    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
        "elapsed_seconds": round(elapsed, 3),
    }


def execute_vector_retrieval_task(task_packet: dict) -> dict:
    query = task_packet.get("query", "")

    if not query:
        return {
            "status": "fail",
            "reason": "missing_query",
            "stdout": "",
            "stderr": "No query specified in task packet",
            "returncode": 2,
        }

    execution = run_command([
        sys.executable,
        str(TOOLS_DIR / "query_vector_memory.py"),
        query,
    ])

    return {
        "status": "pass" if execution["returncode"] == 0 else "fail",
        "stdout": execution["stdout"],
        "stderr": execution["stderr"],
        "returncode": execution["returncode"],
        "elapsed_seconds": execution["elapsed_seconds"],
    }
