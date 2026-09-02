from __future__ import annotations

import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

mf = importlib.import_module("Agency.Core.work.missions.mission_factory")
ms = importlib.import_module("Agency.Core.work.missions.mission_spec")
run_py = importlib.import_module("run")


class MissionSystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "Agency" / "Core" / "runtime" / "state" / "missions"
        self.root.mkdir(parents=True)
        self.patcher = patch.object(mf, "MISSIONS_ROOT", self.root)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self.tmp.cleanup()

    def build_spec(self, mission_id: str = "mission-1", **overrides):
        values = {
            "mission_id": mission_id,
            "title": "Review repository",
            "owner": "Editor",
            "objective": "Review repository",
            "created_at": "2026-07-23T00:00:00Z",
            "inputs": ("Agency/Core",),
            "context": {"repository": "Dashboard"},
            "constraints": ("read_only",),
            "resources": ("filesystem", "python"),
            "tasks": ("inspect:Inspect scope", "report:Report findings"),
        }
        values.update(overrides)
        return ms.build_mission_spec(**values)

    def test_mission_spec_validation_rules(self) -> None:
        spec = self.build_spec(
            owner="",
            objective="",
            initial_state="invented",
            resources=("filesystem", "filesystem", "OpenAI"),
            tasks=("dup:First", "dup:Second", "bad:Bad:invented"),
        )

        errors = ms.validate_mission_spec(spec)

        self.assertIn("identity.owner is required", errors)
        self.assertIn("objective is required", errors)
        self.assertIn("invalid lifecycle state: invented", errors)
        self.assertIn("duplicate resource: filesystem", errors)
        self.assertIn("resource must be an abstract capability token: OpenAI", errors)
        self.assertIn("duplicate task.task_id: dup", errors)
        self.assertIn("invalid task status for bad: invented", errors)

    def test_validation_occurs_before_filesystem_mutation(self) -> None:
        spec = self.build_spec(resources=("Gemini",))

        with patch.object(mf, "write_if_missing", side_effect=AssertionError("write called")):
            with self.assertRaises(ms.MissionSpecValidationError) as ctx:
                mf.create_mission_from_spec(spec)

        self.assertIn("resource must be an abstract capability token: Gemini", ctx.exception.errors)
        self.assertEqual([], list(self.root.iterdir()))

    def test_creation_paths_converge_into_identical_mission_spec(self) -> None:
        mission_id = "mission-17"
        created_at = "2026-07-23T12:00:00Z"
        parser = mf.build_parser()
        legacy = mf.spec_from_create_args(parser.parse_args([
            "create", "Review repository",
            "--owner", "Editor",
            "--resource", "filesystem",
        ]), mission_id=mission_id, created_at=created_at, root=self.root)
        declarative = mf.spec_from_create_args(parser.parse_args([
            "create",
            "--title", "Review repository",
            "--owner", "Editor",
            "--objective", "Review repository",
            "--resource", "filesystem",
            "--non-interactive",
        ]), mission_id=mission_id, created_at=created_at, root=self.root)
        responses = iter([
            "Review repository",
            "Editor",
            "",
            "",
            "",
            "",
            "filesystem",
            "",
            "",
            "y",
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            interactive = mf.collect_interactive_mission_spec(
                mission_id=mission_id,
                created_at=created_at,
                input_func=lambda _prompt: next(responses),
                root=self.root,
            )

        self.assertEqual(legacy.to_dict(), declarative.to_dict())
        self.assertEqual(declarative.to_dict(), interactive.to_dict())

    def test_create_mission_provisions_required_records(self) -> None:
        result = mf.create_mission_from_spec(self.build_spec())
        mission_dir = self.root / "mission-1"

        self.assertEqual("created", result["status"])
        self.assertTrue((mission_dir / "mission.json").exists())
        self.assertTrue((mission_dir / "state.json").exists())
        self.assertTrue((mission_dir / "history.jsonl").exists())
        self.assertTrue((mission_dir / "outputs" / ".keep").exists())
        mission = json.loads((mission_dir / "mission.json").read_text(encoding="utf-8"))
        state = json.loads((mission_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual("Review repository", mission["MissionSpec"]["objective"])
        self.assertEqual("planned", state["MissionState"]["state"])
        self.assertEqual("Editor", state["MissionState"]["owner"])

    def test_lifecycle_transitions_and_completion_are_recorded(self) -> None:
        mf.create_mission_from_spec(self.build_spec())

        running = mf.transition_mission_state("mission-1", "running", reason="work started")
        completed = mf.transition_mission_state(
            "mission-1",
            "completed",
            reason="objective satisfied",
            summary="Reviewed repository",
            produced_artifacts=["report.md"],
        )
        inspected = mf.inspect_mission("mission-1")

        self.assertEqual("planned", running["from_state"])
        self.assertEqual("running", running["to_state"])
        self.assertEqual("completed", completed["to_state"])
        self.assertEqual("completed", inspected["state"])
        self.assertEqual("Reviewed repository", inspected["completion"]["summary"])
        self.assertEqual(["report.md"], inspected["completion"]["produced_artifacts"])
        self.assertGreaterEqual(inspected["history_events"], 3)

    def test_completion_requires_summary(self) -> None:
        mf.create_mission_from_spec(self.build_spec())

        with self.assertRaises(ms.MissionSpecValidationError) as ctx:
            mf.transition_mission_state("mission-1", "completed", reason="done")

        self.assertIn("completion summary is required", ctx.exception.errors)

    def test_parent_child_relationship_creation(self) -> None:
        parent = self.build_spec("mission-1", title="Parent", objective="Coordinate work")
        child = self.build_spec("mission-2", title="Child", objective="Do delegated work", parent_mission_id="mission-1")

        mf.create_mission_from_spec(parent)
        mf.create_mission_from_spec(child)
        parent_inspection = mf.inspect_mission("mission-1")
        child_inspection = mf.inspect_mission("mission-2")

        self.assertEqual(["mission-2"], parent_inspection["relationships"]["child_mission_ids"])
        self.assertEqual("mission-1", child_inspection["relationships"]["parent_mission_id"])

    def test_inspection_output_reconstructs_current_state(self) -> None:
        mf.create_mission_from_spec(self.build_spec(tasks=("inspect:Inspect", "report:Report:blocked")))
        inspected = mf.inspect_mission("mission-1")

        self.assertEqual("found", inspected["status"])
        self.assertEqual("planned", inspected["state"])
        self.assertEqual("Editor", inspected["owner"])
        self.assertEqual("Review repository", inspected["objective"])
        self.assertEqual(["inspect"], inspected["pending_tasks"])
        self.assertEqual([], inspected["outputs"])
        self.assertIsNone(inspected["failure"])

    def test_backward_compatible_cli_entry(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = run_py.run_mission_command([
                "create",
                "Review repository",
                "--owner", "Editor",
                "--non-interactive",
            ])

        self.assertEqual(0, code)
        self.assertTrue((self.root / "mission-1" / "mission.json").exists())
        self.assertIn("MISSION_CREATED", output.getvalue())
        state = json.loads((self.root / "mission-1" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual("Review repository", state["MissionState"]["objective"])

    def test_declarative_cli_entry_and_inspection(self) -> None:
        output: list[str] = []
        code = mf.main([
            "create",
            "--title", "Inspect runtime",
            "--owner", "Editor",
            "--objective", "Inspect runtime",
            "--resource", "filesystem",
            "--constraint", "read_only",
            "--task", "inspect:Inspect runtime",
            "--non-interactive",
            "--raw",
        ], output_func=output.append)
        result = json.loads("\n".join(output))
        inspected = mf.inspect_mission(result["mission_id"])

        self.assertEqual(0, code)
        self.assertEqual("mission-1", result["mission_id"])
        self.assertEqual("Inspect runtime", inspected["objective"])
        self.assertEqual(["inspect"], inspected["pending_tasks"])

    def test_noninteractive_missing_required_values_fails_without_prompt(self) -> None:
        output: list[str] = []
        code = mf.main(
            ["create", "--title", "No owner", "--non-interactive"],
            input_func=lambda _prompt: self.fail("non-interactive mode prompted unexpectedly"),
            output_func=output.append,
        )

        self.assertEqual(1, code)
        rendered = "\n".join(output)
        self.assertIn("MISSION_FAILED", rendered)
        self.assertIn("identity.owner is required", rendered)
        self.assertEqual([], list(self.root.iterdir()))


if __name__ == "__main__":
    unittest.main()
