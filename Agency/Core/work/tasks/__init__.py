"""Primitive bounded work execution.

Tasks are the smallest executable units in the Agency work hierarchy.
Concrete task engines are grouped beneath this package.
"""

from Agency.Core.work.tasks.editor import (
    EditorResult,
    EditorTask,
    PatchAuthorization,
    editor_task_from_mapping,
    execute_editor_task,
    load_task_file,
    submit_task_file,
    validate_editor_task,
)

__all__ = [
    "EditorResult",
    "EditorTask",
    "PatchAuthorization",
    "editor_task_from_mapping",
    "execute_editor_task",
    "load_task_file",
    "submit_task_file",
    "validate_editor_task",
]
