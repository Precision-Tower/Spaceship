from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.work.missions import mission_runtime as mr


class MissionRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "missions"
        self.root.mkdir(parents=True)
        self.blocker = patch.object(
            mr,
            "agency_blocks_dependent_operations",
            return_value=[],
        )
        self.blocker.start()
        self.addCleanup(self.blocker.stop)

    def create(self, intent: str = "Inspect shared mission runtime") -> dict:
        return mr.create_mission(
            intent,
            ["UI/Main"],
            root=self.root,
            required_context_files=[mr.DASHBOARD_ROOT / "run.py"],
        )

    def test_create_mission_provisions_runtime_artifacts(self) -> None:
        refresh_calls = []

        payload = mr.create_mission(
            "Inspect shared mission runtime",
            ["UI/Main"],
            root=self.root,
            required_context_files=[mr.DASHBOARD_ROOT / "run.py"],
            refresh_pinboard=lambda **kwargs: refresh_calls.append(kwargs),
        )

        mission_dir = self.root / "mission-1"
        self.assertEqual("mission_created", payload["status"])
        self.assertTrue((mission_dir / "intent.json").exists())
        self.assertTrue((mission_dir / "state.json").exists())
        self.assertTrue((mission_dir / "inspect" / "manifest.json").exists())
        self.assertTrue((mission_dir / "inspect" / "coverage.json").exists())
        self.assertTrue((mission_dir / "review" / "operator_notes.md").exists())
        events = sorted((mission_dir / "events").glob("*.json"))
        self.assertEqual(1, len(events))
        event = json.loads(events[0].read_text(encoding="utf-8"))
        self.assertEqual("created", event["event_type"])
        self.assertEqual("Inspect shared mission runtime", refresh_calls[0]["mission"])

    def test_status_accepts_numeric_mission_reference(self) -> None:
        self.create()

        payload = mr.mission_status("1", root=self.root)

        self.assertTrue(payload["ok"])
        self.assertEqual("mission_status", payload["status"])
        self.assertEqual("mission-1", payload["mission_id"])
        self.assertEqual("created", payload["phase"])
        self.assertEqual("ready_for_inspection", payload["current_status"])

    def test_list_and_show_reconstruct_created_missions(self) -> None:
        first = self.create("First runtime mission")
        second = self.create("Second runtime mission")

        rows = mr.list_missions(root=self.root)
        shown = mr.show_mission("1", root=self.root)

        self.assertEqual("mission-1", first["mission_id"])
        self.assertEqual("mission-2", second["mission_id"])
        self.assertEqual(["mission-2", "mission-1"], [row["mission_id"] for row in rows])
        self.assertEqual("First runtime mission", shown["intent"])
        self.assertEqual("created", shown["phase"])
        self.assertEqual("ready_for_inspection", shown["status"])
        self.assertEqual(1, shown["events"]["count"])


    def test_inspect_mission_records_pass_through_shared_runtime(self) -> None:
        self.create("Inspect mission lifecycle")
        refresh_calls = []

        payload = mr.inspect_mission(
            "1",
            root=self.root,
            refresh_pinboard=lambda **kwargs: refresh_calls.append(kwargs),
        )

        mission_dir = self.root / "mission-1"
        self.assertTrue(payload["ok"])
        self.assertIn(payload["status"], {"inspection_pass_recorded", "inspection_complete"})
        self.assertEqual("mission-1", payload["mission_id"])
        self.assertEqual(1, payload["pass"])
        self.assertTrue((mission_dir / "inspect" / "pass_001.json").exists())
        self.assertTrue((mission_dir / "inspect" / "pass_001.md").exists())
        state = json.loads((mission_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(1, state["inspection_passes"])
        self.assertEqual(payload["inspection_complete"], state["inspection_complete"])
        events = sorted((mission_dir / "events").glob("*.json"))
        self.assertEqual(2, len(events))
        event = json.loads(events[-1].read_text(encoding="utf-8"))
        self.assertEqual("inspected", event["event_type"])
        self.assertEqual("Inspect mission lifecycle", refresh_calls[0]["mission"])


    def test_remaining_phase_entrypoints_share_structured_errors(self) -> None:
        self.create("Remaining phase adapters")

        checks = [
            (lambda: mr.plan_mission("1", root=self.root), "planning_not_ready"),
            (lambda: mr.resourcefulness_mission("1", root=self.root), "resourcefulness_plan_required"),
            (lambda: mr.propose_mission("1", root=self.root), "plan_required"),
            (lambda: mr.review_mission("1", approve=True, root=self.root), "proposal_required"),
            (lambda: mr.implement_mission("1", root=self.root), "proposal_required"),
            (lambda: mr.verify_mission("1", root=self.root), "proposal_required"),
        ]
        for operation, expected_status in checks:
            with self.subTest(status=expected_status):
                with self.assertRaises(mr.MissionOperationError) as ctx:
                    operation()
                self.assertEqual(expected_status, ctx.exception.payload["status"])

        resume = mr.resume_mission("1", root=self.root)
        self.assertEqual("mission-1", resume["mission_id"])

    def test_missing_mission_errors_are_structured(self) -> None:
        with self.assertRaises(mr.MissionOperationError) as ctx:
            mr.mission_status("missing", root=self.root)

        self.assertEqual(2, ctx.exception.return_code)
        self.assertEqual("mission_status_failed", ctx.exception.payload["status"])
        self.assertIn("mission not found", ctx.exception.payload["reason"])

    def test_exact_inference_map_file_is_an_allowed_scope(self) -> None:
        target = mr.DASHBOARD_ROOT / "Agency/Core/runtime/_inference_map.md"

        if not target.exists():
            self.skipTest("repository inference map is unavailable")

        scopes = mr.validate_engineering_scopes(
            ["Agency/Core/runtime/_inference_map.md"]
        )

        self.assertEqual(1, len(scopes))
        self.assertEqual(
            "Agency/Core/runtime/_inference_map.md",
            scopes[0]["relative"],
        )
        self.assertEqual(
            "Agency/Core/runtime/_inference_map.md",
            scopes[0]["allowed_root"],
        )

    def test_invalid_scope_fails_before_creating_directory(self) -> None:
        with self.assertRaises(mr.MissionOperationError) as ctx:
            mr.create_mission("Invalid", ["Agency/Core"], root=self.root)

        self.assertEqual(2, ctx.exception.return_code)
        self.assertEqual("invalid_scope", ctx.exception.payload["status"])
        self.assertEqual([], list(self.root.iterdir()))


if __name__ == "__main__":
    unittest.main()
