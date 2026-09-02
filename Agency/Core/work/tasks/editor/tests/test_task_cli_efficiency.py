import argparse
import dataclasses
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Agency.Core.work.tasks.editor import execution
from Agency.Core.work.tasks.editor import persistence


class TaskPersistenceEfficiencyTests(unittest.TestCase):
    def test_latest_task_id_uses_task_creation_record_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            older = root / "older-task"
            newer = root / "newer-task"
            older.mkdir()
            newer.mkdir()

            older_task = older / "task.json"
            newer_task = newer / "task.json"

            older_task.write_text('{"task_id": "older-task"}\n', encoding="utf-8")
            newer_task.write_text('{"task_id": "newer-task"}\n', encoding="utf-8")

            os.utime(older_task, ns=(1_000_000_000, 1_000_000_000))
            os.utime(newer_task, ns=(2_000_000_000, 2_000_000_000))

            with patch.object(persistence, "EDITOR_TASKS_ROOT", root):
                self.assertEqual("newer-task", persistence.latest_task_id())

    def test_latest_task_id_rejects_empty_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                persistence,
                "EDITOR_TASKS_ROOT",
                Path(tmp),
            ):
                with self.assertRaises(FileNotFoundError):
                    persistence.latest_task_id()


class TaskCliEfficiencyTests(unittest.TestCase):
    def test_submit_accepts_positional_task_path(self) -> None:
        result = SimpleNamespace(status="completed")

        with (
            patch.object(
                execution,
                "submit_task_file",
                return_value=result,
            ) as submit,
            patch.object(
                execution,
                "result_payload",
                return_value={"status": "completed"},
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = execution.main(["submit", "task.yaml"])

        self.assertEqual(0, code)
        submit.assert_called_once_with("task.yaml")

    def test_submit_preserves_task_option_compatibility(self) -> None:
        result = SimpleNamespace(status="completed")

        with (
            patch.object(
                execution,
                "submit_task_file",
                return_value=result,
            ) as submit,
            patch.object(
                execution,
                "result_payload",
                return_value={"status": "completed"},
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = execution.main(["submit", "--task", "task.yaml"])

        self.assertEqual(0, code)
        submit.assert_called_once_with("task.yaml")

    def test_show_without_id_uses_latest_task(self) -> None:
        output = io.StringIO()

        with (
            patch.object(
                persistence,
                "latest_task_id",
                return_value="latest-task",
            ) as latest,
            patch.object(
                persistence,
                "load_task",
                return_value={"task_id": "latest-task"},
            ) as load,
            contextlib.redirect_stdout(output),
        ):
            code = execution.main(["show"])

        self.assertEqual(0, code)
        latest.assert_called_once_with()
        load.assert_called_once_with("latest-task")
        self.assertEqual(
            "latest-task",
            json.loads(output.getvalue())["task_id"],
        )

    def test_result_without_id_uses_latest_task(self) -> None:
        output = io.StringIO()

        with (
            patch.object(
                persistence,
                "latest_task_id",
                return_value="latest-task",
            ) as latest,
            patch.object(
                execution,
                "_load_result_payload",
                return_value={
                    "task_id": "latest-task",
                    "status": "completed",
                },
            ) as load,
            contextlib.redirect_stdout(output),
        ):
            code = execution.main(["result"])

        self.assertEqual(0, code)
        latest.assert_called_once_with()
        load.assert_called_once_with("latest-task")
        self.assertEqual(
            "completed",
            json.loads(output.getvalue())["status"],
        )

    def test_inspect_defaults_issued_by_to_gear(self) -> None:
        captured = {}
        result = SimpleNamespace(status="completed")

        def make_task(args):
            captured["issued_by"] = args.issued_by
            return object()

        with (
            patch.object(
                execution,
                "_make_inspect_task",
                side_effect=make_task,
            ),
            patch.object(
                execution,
                "execute_editor_task",
                return_value=result,
            ),
            patch.object(
                execution,
                "result_payload",
                return_value={"status": "completed"},
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            code = execution.main([
                "inspect",
                "--scope",
                "Agency/Core",
                "--text",
                "run_mission_command",
            ])

        self.assertEqual(0, code)
        self.assertEqual("Gear", captured["issued_by"])


if __name__ == "__main__":
    unittest.main()


class _InspectNamespace(argparse.Namespace):
    """Namespace that mirrors optional argparse fields defaulting to None."""

    def __getattr__(self, name):
        return None


class MultiTargetInspectionCliTests(unittest.TestCase):
    def test_make_inspect_task_emits_ordered_unique_symbols(self) -> None:
        args = _InspectNamespace(
            symbol=[
                "first_symbol",
                "second_symbol",
                "first_symbol",
                "  ",
            ],
            text=None,
            operation=None,
            editor="Editor",
            issued_by="Gear",
            task_id="editor-inspect-multi-symbol",
            scope=[],
        )

        task = execution._make_inspect_task(args)
        payload = dataclasses.asdict(task)

        request = payload.get("request", payload)
        repository_request = request["repository_context"]

        self.assertEqual(
            repository_request["symbols"],
            ["first_symbol", "second_symbol"],
        )
        self.assertNotIn("symbol", repository_request)

    def test_make_inspect_task_preserves_legacy_string_symbol(self) -> None:
        args = _InspectNamespace(
            symbol="legacy_symbol",
            text=None,
            operation=None,
            editor="Editor",
            issued_by="Gear",
            task_id="editor-inspect-legacy-symbol",
            scope=[],
        )

        task = execution._make_inspect_task(args)
        payload = dataclasses.asdict(task)

        request = payload.get("request", payload)
        repository_request = request["repository_context"]

        self.assertEqual(
            repository_request["symbols"],
            ["legacy_symbol"],
        )
