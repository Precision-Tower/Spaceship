from __future__ import annotations

import re
from pathlib import Path
from typing import Any


TASK_HEADER_RE = re.compile(
    r"(?m)^(?P<label>task_\d+):\s*\(\s*$"
)
IDENTITY_RE = re.compile(
    r'(?m)^identity-\s*"(?P<identity>[^"]+)";'
)

KERNEL_IDENTITY = "kernel.driver_discovery"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def checklist_path() -> Path:
    return repo_root() / "Agency" / "checklist.qps"


def kernel_checklist_path() -> Path:
    return repo_root() / "qps" / "checklist.qps"


def _task_blocks(text: str):
    headers = list(TASK_HEADER_RE.finditer(text))

    for index, header in enumerate(headers):
        block_start = header.end()
        block_end = (
            headers[index + 1].start()
            if index + 1 < len(headers)
            else len(text)
        )
        yield header.group("label"), text[block_start:block_end]


def _top_level_field(
    body: str,
    field: str,
) -> str:
    pattern = re.compile(
        rf'(?m)^{re.escape(field)}-\s*"([^"]*)";'
    )
    match = pattern.search(body)
    return match.group(1) if match else ""


def _tasks_from(
    path: Path,
    *,
    lane: str,
) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    tasks: list[dict[str, Any]] = []

    for _label, body in _task_blocks(text):
        identity_match = IDENTITY_RE.search(body)
        if identity_match is None:
            continue

        identity = identity_match.group("identity")
        state = _top_level_field(
            body,
            "state",
        ).lower()

        if state not in {"ready", "active"}:
            continue

        if lane == "kernel" and identity != KERNEL_IDENTITY:
            continue

        tasks.append({
            "identity": identity,
            "state": state,
            "summary": _top_level_field(body, "summary"),
            "next": _top_level_field(body, "next"),
            "lane": lane,
        })

    return tasks


def actionable_tasks() -> list[dict[str, Any]]:
    # Operator-authorized kernel lane takes priority over ordinary
    # Agency work while kernel.driver_discovery remains actionable.
    return (
        _tasks_from(
            kernel_checklist_path(),
            lane="kernel",
        )
        + _tasks_from(
            checklist_path(),
            lane="agency",
        )
    )


def select_assignment(
    *,
    exclude_identity: str = "agency.geminigo_daily_agency",
) -> dict[str, Any] | None:
    for task in actionable_tasks():
        if task["identity"] != exclude_identity:
            return task
    return None


def assignment_paths(
    task: dict[str, Any],
) -> list[str]:
    if task.get("lane") == "kernel":
        return [
            "qps/checklist.qps",
            "qps/_index.qps",
            "qps/kernel/_index.qps",
        ]

    return ["Agency/checklist.qps"]


def bounded_evidence(task: dict[str, Any]) -> str:
    if task.get("lane") == "kernel":
        scope = (
            "qps/checklist.qps, qps/_index.qps, "
            "qps/kernel/_index.qps, qps/kernel/"
        )
        priority = (
            "PRIORITY: resource state first; begin with the "
            "read-only battery/power/thermal service contract. "
            "Then Mali/GPU, then EdgeTPU.\n"
        )
    else:
        scope = "Agency/"
        priority = ""

    return (
        f'TASK: {task["identity"]}\n'
        f'LANE: {task.get("lane", "agency")}\n'
        f'STATE: {task["state"]}\n'
        f'SUMMARY: {task["summary"]}\n'
        f'NEXT: {task["next"]}\n'
        f'SCOPE: {scope}\n'
        + priority
        + 'Return analysis and the smallest next evidence-producing action. '
        'Discovery is read-only. Do not perform repository mutation, '
        'hardware mutation, allocation, rendering, inference, streaming, '
        'or speculative ioctl/Binder calls.'
    )
