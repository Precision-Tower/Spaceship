from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Agency.Core.work.tasks.editor.contracts import EditorResult, EditorTask, now_utc
from Agency.Core.repository.git_authority.persistence_guard import guard_ceos_persistence
from Agency.Core.foundation.paths import EDITOR_TASKS_ROOT, stable_path




def editor_tasks_root() -> Path:
    return EDITOR_TASKS_ROOT


def task_dir(task_id: str) -> Path:
    return editor_tasks_root() / task_id


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    guard_ceos_persistence(payload, record_name=stable_path(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def append_event(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": now_utc(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def persist_task(task: EditorTask, root: Path | None = None) -> Path:
    directory = (root or task_dir(task.task_id))
    atomic_json(directory / "task.json", task.to_dict())
    return directory


def persist_result(result: EditorResult, root: Path | None = None) -> Path:
    directory = root or task_dir(result.task_id)
    atomic_json(directory / "result.json", result.to_dict())
    return directory


def load_task(task_id: str) -> dict[str, Any]:
    return json.loads((task_dir(task_id) / "task.json").read_text(encoding="utf-8"))


def load_result(task_id: str) -> dict[str, Any]:
    return json.loads((task_dir(task_id) / "result.json").read_text(encoding="utf-8"))


def latest_task_id() -> str:
    """Return the most recently created persisted Editor task ID."""
    root = editor_tasks_root()
    if not root.exists():
        raise FileNotFoundError(f"no Editor tasks found under {stable_path(root)}")

    candidates: list[tuple[int, str]] = []
    for directory in root.iterdir():
        task_path = directory / "task.json"
        if directory.is_dir() and task_path.is_file():
            candidates.append((task_path.stat().st_mtime_ns, directory.name))

    if not candidates:
        raise FileNotFoundError(f"no Editor tasks found under {stable_path(root)}")

    return max(candidates)[1]


def stable_task_path(task_id: str) -> str:
    return stable_path(task_dir(task_id))
