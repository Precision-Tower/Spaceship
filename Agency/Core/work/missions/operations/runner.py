#!/usr/bin/env python3
"""Small dispatcher for bounded task packets."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from Agency.Core.work.missions.operations.handlers.godot_playground import (
    BLOCKED_FILES,
    execute_task_011,
    execute_task_012,
    execute_task_013,
)

from Agency.Core.work.missions.operations.handlers.records import execute_freeze_summary, execute_result_inventory
from Agency.Core.work.missions.operations.handlers.retrieval import VECTOR_RETRIEVAL_TASK_IDS, execute_vector_retrieval_task
from Agency.Core.work.missions.operations.io import ACTIVE_DIR, ROOT, get_result_path, load_yaml, write_yaml

TASK_ID_HANDLERS = {
    **{task_id: execute_vector_retrieval_task for task_id in VECTOR_RETRIEVAL_TASK_IDS},
    "task_009_result_packet_inventory": execute_result_inventory,
    "task_010_level5_freeze_6_10": execute_freeze_summary,
    "task_011_godot_playground_sandbox": execute_task_011,
    "task_012_godot_playground_interaction_test": execute_task_012,
    "task_013_godot_playground_spawn_test": execute_task_013,
}

COMMAND_HANDLERS = {
    "godot_playground_sandbox_build": execute_task_011,
    "godot_playground_interaction_build": execute_task_012,
    "godot_playground_spawn_build": execute_task_013,
}


def load_task_packet(packet_path: str | Path) -> dict:
    packet_path = resolve_packet_path(packet_path)
    return load_yaml(packet_path)


def resolve_packet_path(packet_path: str | Path) -> Path:
    packet_path = Path(packet_path)

    if packet_path.is_absolute():
        return packet_path
    if (ACTIVE_DIR / packet_path).exists():
        return ACTIVE_DIR / packet_path
    if (ROOT / packet_path).exists():
        return ROOT / packet_path

    raise FileNotFoundError(f"Task packet not found: {packet_path}")


def unwrap_task_packet(raw_packet: dict) -> dict:
    return raw_packet.get("TaskPacket", raw_packet)


def dispatch(task_packet: dict) -> dict:
    command = task_packet.get("command", "")
    task_id = task_packet.get("id", "")
    handler = COMMAND_HANDLERS.get(command) or TASK_ID_HANDLERS.get(task_id)

    if handler is None:
        return {
            "status": "fail",
            "reason": f"unsupported_task_id: {task_id or 'unknown'}",
            "stdout": "",
            "stderr": "",
            "returncode": 1,
        }

    return handler(task_packet)


def execute_task(packet_path: str | Path) -> dict:
    task_packet = unwrap_task_packet(load_task_packet(packet_path))
    execution = dispatch(task_packet)
    return build_result_packet(task_packet, execution)


def build_result_packet(task_packet: dict, execution: dict) -> dict:
    task_id = task_packet.get("id", "unknown")
    mode = task_packet.get("mode", "unknown")
    goal = task_packet.get("goal", "")
    command = task_packet.get("command", goal)

    if task_id == "task_013_godot_playground_spawn_test":
        return playground_result(
            task_id=task_id,
            status=execution["status"],
            mode=mode,
            command=command,
            files_written=execution.get("files_written", []),
            claims_blocked=[
                "generated_spawn_behavior_equals_validation",
                "godot_render_equals_truth",
                "playground_success_equals_runtime_readiness",
                "display_equals_evidence",
            ],
            returncode=execution.get("returncode", 1),
        )

    if task_id == "task_012_godot_playground_interaction_test":
        return playground_result(
            task_id=task_id,
            status=execution["status"],
            mode=mode,
            command=command,
            files_written=execution.get("files_written", []),
            claims_blocked=[
                "generated_interaction_equals_validation",
                "godot_render_equals_truth",
                "playground_success_equals_runtime_readiness",
                "display_equals_evidence",
            ],
            returncode=execution.get("returncode", 1),
        )

    claims_blocked = [
        "retrieval_equals_truth",
        "retrieval_equals_validation",
        "snippet_equals_source_authority",
    ]
    if task_id == "task_009_result_packet_inventory":
        claims_blocked.append("result_inventory_equals_validation")
    if task_id == "task_010_level5_freeze_6_10":
        claims_blocked.append("freeze_summary_equals_canon")

    return {
        "TaskResult": {
            "task_id": task_id,
            "status": execution["status"],
            "mode": mode,
            "command": goal,
            "authority": authority_for_task(task_id),
            "mutation": "none",
            "stdout": execution.get("stdout", ""),
            "stderr": execution.get("stderr", ""),
            "returncode": execution.get("returncode", 1),
            "claims_blocked": claims_blocked,
        }
    }


def playground_result(
    task_id: str,
    status: str,
    mode: str,
    command: str,
    files_written: list[str],
    claims_blocked: list[str],
    returncode: int,
) -> dict:
    return {
        "TaskResult": {
            "task_id": task_id,
            "status": status,
            "mode": mode,
            "command": command,
            "authority": "sandbox_write_only_not_runtime_authority",
            "mutation": "playground_sandbox_only",
            "sandbox_root": "UI/godot/playground",
            "files_written": files_written,
            "files_blocked": BLOCKED_FILES,
            "claims_blocked": claims_blocked,
            "returncode": returncode,
        }
    }


def authority_for_task(task_id: str) -> str:
    if "retrieval" in task_id or task_id == "task_009_result_packet_inventory":
        return "retrieval_only_not_source_authority"
    return "proposal_only_not_source_authority"


def run_and_save(packet_path: str | Path) -> int:
    try:
        result_packet = execute_task(packet_path)
        task_id = result_packet["TaskResult"]["task_id"]
        result_path = get_result_path(task_id)

        write_yaml(result_path, result_packet)

        print(f"TASK_EXECUTED: {task_id}")
        print(f"RESULT_WRITTEN: {result_path}")
        print(f"STATUS: {result_packet['TaskResult']['status']}")
        return 0
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERR: missing task packet path", file=sys.stderr)
        print("usage: python tasks/runner.py <packet_path>", file=sys.stderr)
        raise SystemExit(2)

    raise SystemExit(run_and_save(sys.argv[1]))
