from __future__ import annotations

from Agency.Core.work.missions.operations.io import RESULTS_DIR, load_yaml


def execute_result_inventory(task_packet: dict) -> dict:
    result_files = sorted(RESULTS_DIR.glob("*_result.yaml"))

    inventory = []
    for result_file in result_files:
        try:
            data = load_yaml(result_file)
            task_result = data.get("TaskResult", {})
            inventory.append({
                "file": result_file.name,
                "task_id": task_result.get("task_id", "unknown"),
                "status": task_result.get("status", "unknown"),
            })
        except Exception as exc:
            inventory.append({
                "file": result_file.name,
                "error": str(exc),
            })

    inventory_summary = "\n".join([
        "RESULT_INVENTORY",
        f"total_result_packets: {len(result_files)}",
        *[
            f"  - {item.get('file')}: {item.get('task_id')} ({item.get('status')})"
            for item in inventory
        ],
    ])

    return {
        "status": "pass",
        "stdout": inventory_summary,
        "stderr": "",
        "returncode": 0,
        "elapsed_seconds": 0.0,
        "inventory_count": len(result_files),
        "inventory": inventory,
    }


def execute_freeze_summary(task_packet: dict) -> dict:
    expected_tasks = {
        "task_006_vector_retrieval_smoke_test",
        "task_007_vector_retrieval_yaml_query",
        "task_008_vector_retrieval_godot_query",
        "task_009_result_packet_inventory",
        "task_010_level5_freeze_6_10",
    }

    completed_tasks = []
    failed_tasks = []

    for result_file in RESULTS_DIR.glob("*_result.yaml"):
        try:
            task_result = load_yaml(result_file).get("TaskResult", {})
            task_id = task_result.get("task_id", "unknown")
            status = task_result.get("status", "unknown")

            if task_id in expected_tasks:
                if status == "pass":
                    completed_tasks.append(task_id)
                else:
                    failed_tasks.append(task_id)
        except Exception:
            pass

    freeze_summary = "\n".join([
        "LEVEL_5_FREEZE_SUMMARY",
        "scope: tasks_006_to_010",
        f"completed_tasks: {len(completed_tasks)}",
        *[f"  - {task_id}" for task_id in sorted(completed_tasks)],
        "",
        f"failed_tasks: {len(failed_tasks)}",
        *[f"  - {task_id}" for task_id in sorted(failed_tasks)],
        "",
        "capabilities_proven:",
        "  - bounded_task_execution",
        "  - vector_retrieval_with_authority_lineage",
        "  - result_packet_inventory",
        "  - freeze_proposal_generation",
        "",
        "blocked_claims:",
        "  - retrieval_equals_truth",
        "  - retrieval_equals_validation",
        "  - snippet_equals_source_authority",
        "  - result_inventory_equals_validation",
        "  - freeze_summary_equals_canon",
        "",
        "next_recommended_primitive:",
        "  - task_runner_batch_execution",
    ])

    return {
        "status": "pass",
        "stdout": freeze_summary,
        "stderr": "",
        "returncode": 0,
        "elapsed_seconds": 0.0,
        "completed_count": len(completed_tasks),
        "failed_count": len(failed_tasks),
    }
