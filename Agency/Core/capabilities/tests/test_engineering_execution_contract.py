from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.agents.tooling import agent_actions


class EngineeringExecutionContractTest(unittest.TestCase):
    def test_create_file_writes_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)
            target = dashboard_root / "scratch" / "created.txt"

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "stable_path",
                side_effect=lambda path: (
                    Path(path)
                    .resolve()
                    .relative_to(dashboard_root.resolve())
                    .as_posix()
                ),
            ):
                result = agent_actions._write_file_action(
                    {
                        "type": "create_file",
                        "path": "scratch/created.txt",
                        "content": "hello",
                        "overwrite": False,
                    }
                )

            self.assertEqual("hello", target.read_text(encoding="utf-8"))
            self.assertEqual(
                {
                    "type": "create_file",
                    "status": "applied",
                    "path": "scratch/created.txt",
                    "bytes_written": 5,
                },
                result,
            )

    def test_create_file_rejects_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)
            target = dashboard_root / "scratch" / "existing.txt"
            target.parent.mkdir(parents=True)
            target.write_text("original", encoding="utf-8")

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "stable_path",
                side_effect=lambda path: (
                    Path(path)
                    .resolve()
                    .relative_to(dashboard_root.resolve())
                    .as_posix()
                ),
            ):
                with self.assertRaisesRegex(
                    FileExistsError,
                    r"target_exists: scratch/existing\.txt",
                ):
                    agent_actions._write_file_action(
                        {
                            "type": "create_file",
                            "path": "scratch/existing.txt",
                            "content": "replacement",
                            "overwrite": False,
                        }
                    )

            self.assertEqual(
                "original",
                target.read_text(encoding="utf-8"),
            )

    def test_write_file_overwrites_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)
            target = dashboard_root / "scratch" / "existing.txt"
            target.parent.mkdir(parents=True)
            target.write_text("original", encoding="utf-8")

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "stable_path",
                side_effect=lambda path: (
                    Path(path)
                    .resolve()
                    .relative_to(dashboard_root.resolve())
                    .as_posix()
                ),
            ):
                result = agent_actions._apply_action(
                    {
                        "type": "write_file",
                        "path": "scratch/existing.txt",
                        "content": "replacement",
                        "overwrite": True,
                    }
                )

            self.assertEqual(
                "replacement",
                target.read_text(encoding="utf-8"),
            )
            self.assertEqual("write_file", result["type"])
            self.assertEqual("applied", result["status"])
            self.assertEqual("scratch/existing.txt", result["path"])
            self.assertEqual(11, result["bytes_written"])

    def test_patch_action_checks_before_applying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)
            diff_path = dashboard_root / "scratch" / "change.diff"
            diff_path.parent.mkdir(parents=True)

            diff_text = (
                "--- a/scratch/example.txt\n"
                "+++ b/scratch/example.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            )
            diff_path.write_text(diff_text, encoding="utf-8")

            completed = [
                subprocess.CompletedProcess(
                    args=["git", "apply", "--check", "-"],
                    returncode=0,
                    stdout="",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["git", "apply", "--verbose", "-"],
                    returncode=0,
                    stdout="Checking patch scratch/example.txt...\n"
                    "Applied patch scratch/example.txt cleanly.\n",
                    stderr="",
                ),
            ]

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "stable_path",
                side_effect=lambda path: (
                    Path(path)
                    .resolve()
                    .relative_to(dashboard_root.resolve())
                    .as_posix()
                ),
            ), patch.object(
                agent_actions,
                "_git_apply_base",
                return_value=(
                    dashboard_root,
                    ["git", "apply"],
                ),
            ), patch.object(
                agent_actions.subprocess,
                "run",
                side_effect=completed,
            ) as run:
                result = agent_actions._patch_action(
                    {
                        "type": "apply_patch",
                        "diff_path": "scratch/change.diff",
                    }
                )

            self.assertEqual(
                {
                    "type": "apply_patch",
                    "status": "applied",
                    "diff": "scratch/change.diff",
                },
                result,
            )

            self.assertEqual(2, run.call_count)

            check_call = run.call_args_list[0]
            apply_call = run.call_args_list[1]

            self.assertEqual(
                ["git", "apply", "--check", "-"],
                check_call.args[0],
            )
            self.assertEqual(
                ["git", "apply", "--verbose", "-"],
                apply_call.args[0],
            )
            self.assertEqual(diff_text, check_call.kwargs["input"])
            self.assertEqual(diff_text, apply_call.kwargs["input"])

    def test_patch_check_failure_prevents_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dashboard_root = Path(tmp)

            with patch.object(
                agent_actions,
                "DASHBOARD_ROOT",
                dashboard_root,
            ), patch.object(
                agent_actions,
                "_validate_diff_paths",
            ), patch.object(
                agent_actions,
                "_git_apply_base",
                return_value=(
                    dashboard_root,
                    ["git", "apply"],
                ),
            ), patch.object(
                agent_actions.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    args=["git", "apply", "--check", "-"],
                    returncode=1,
                    stdout="",
                    stderr="corrupt patch",
                ),
            ) as run:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "patch_check_failed: corrupt patch",
                ):
                    agent_actions._patch_action(
                        {
                            "type": "apply_patch",
                            "diff": (
                                "--- a/example.txt\n"
                                "+++ b/example.txt\n"
                            ),
                        }
                    )

            self.assertEqual(1, run.call_count)

    def test_rejects_unsupported_action_type(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "unsupported_action_type: detonate_repository",
        ):
            agent_actions._apply_action(
                {"type": "detonate_repository"}
            )


if __name__ == "__main__":
    unittest.main()
