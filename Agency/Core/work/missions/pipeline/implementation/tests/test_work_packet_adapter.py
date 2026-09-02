from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from Agency.Core.work.tasks.editor import contracts as editor_contracts
from Agency.Core.work.tasks.editor import execution as editor_execution
from Agency.Core.work.tasks.editor import persistence as editor_persistence
from Agency.Core.work.missions.pipeline.implementation import execution as impl_execution
from Agency.Core.work.missions.pipeline.implementation import work_packet_adapter as adapter
from Agency.Core.work.missions import mission_runtime
from Agency.Core.foundation.paths import stable_path
from Agency.Core.work.work_packets import contracts as packet_contracts
from Agency.Core.work.work_packets import execution as packet_execution
from Agency.Core.work.work_packets import persistence as packet_persistence


class TestWorkPacketAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name).resolve()
        
        # Init git repo for git operations in editor
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)

        self.target = self.repo / "Agency" / "Core" / "runtime" / "target.txt"
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text("alpha\nbeta\n", encoding="utf-8")
        subprocess.run(["git", "add", "Agency/Core/runtime/target.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.repo, check=True)

        self.editor_tasks = (
            self.repo
            / "Agency"
            / "Core"
            / "editor"
            / "tasks"
        )

        self._orig_editor_tasks_root = editor_persistence.EDITOR_TASKS_ROOT
        self._orig_editor_root = editor_execution.DASHBOARD_ROOT
        self._orig_editor_contracts = editor_contracts.DASHBOARD_ROOT
        self._orig_packet_exec = packet_execution.DASHBOARD_ROOT
        self._orig_packet_pers_root = packet_persistence.WORK_PACKETS_ROOT

        editor_execution.DASHBOARD_ROOT = self.repo
        editor_persistence.EDITOR_TASKS_ROOT = self.editor_tasks
        editor_contracts.DASHBOARD_ROOT = self.repo
        packet_execution.DASHBOARD_ROOT = self.repo
        packet_persistence.WORK_PACKETS_ROOT = self.repo / "Agency" / "Core" / "missions" / "work_packets" / "active"

        self.mission_dir = self.repo / "Agency" / "Core" / "missions" / "active" / "mission-101"
        self.mission_dir.mkdir(parents=True, exist_ok=True)
        self._write_mission_files()

    def _get_deps(self) -> impl_execution.ImplementationExecutionDependencies:
        missions_root = (
            self.repo
            / "Agency"
            / "Core"
            / "missions"
            / "active"
        )
        deps = mission_runtime._implementation_execution_dependencies(
            root=missions_root,
        )
        return replace(
            deps,
            DASHBOARD_ROOT=self.repo,
            MISSIONS_ROOT=missions_root,
            _stable=lambda path: stable_path(path, self.repo),
        )

    def tearDown(self) -> None:
        editor_execution.DASHBOARD_ROOT = self._orig_editor_root
        editor_persistence.EDITOR_TASKS_ROOT = self._orig_editor_tasks_root
        editor_contracts.DASHBOARD_ROOT = self._orig_editor_contracts
        packet_execution.DASHBOARD_ROOT = self._orig_packet_exec
        packet_persistence.WORK_PACKETS_ROOT = self._orig_packet_pers_root
        if "AGENCY_MOCK_IMPLEMENTATION_RESPONSE" in os.environ:
            del os.environ["AGENCY_MOCK_IMPLEMENTATION_RESPONSE"]
        self.tmp.cleanup()

    def _write_mission_files(
        self,
        *,
        review_decision: str = "approved",
        implementation_authorized: bool = True,
        verification_cmd: list[str] | None = None,
    ) -> None:
        (self.mission_dir / "intent.json").write_text(
            json.dumps({"schema_version": 1, "intent": "Fix target file", "created_by": "Gear"}),
            encoding="utf-8",
        )
        (self.mission_dir / "state.json").write_text(
            json.dumps({"schema_version": 1, "status": "approved", "implementation_authorized": True, "next_action": {}}),
            encoding="utf-8",
        )
        (self.mission_dir / "plan").mkdir(parents=True, exist_ok=True)
        (self.mission_dir / "plan" / "plan.json").write_text(
            json.dumps({"schema_version": 1, "execution_order": ["unit-001"]}),
            encoding="utf-8",
        )
        (self.mission_dir / "proposal").mkdir(parents=True, exist_ok=True)
        (self.mission_dir / "proposal" / "proposal.json").write_text(
            json.dumps({
                "schema_version": 1,
                "authority": "implementation_proposal",
                "execution_order": ["unit-001"],
                "implementation_units": [
                    {
                        "id": "unit-001",
                        "objective": "Update target file",
                        "allowed_paths": ["Agency/Core/runtime/target.txt"],
                        "expected_files": ["Agency/Core/runtime/target.txt"],
                        "changes": [
                            {
                                "path": "Agency/Core/runtime/target.txt",
                                "operation": "modify",
                                "reason": "Fix bug",
                            }
                        ],
                        "verification": verification_cmd or ["git status --short"],
                    }
                ],
            }),
            encoding="utf-8",
        )
        (self.mission_dir / "review").mkdir(parents=True, exist_ok=True)
        (self.mission_dir / "review" / "decision.json").write_text(
            json.dumps({
                "schema_version": 1,
                "authority": "operator_review",
                "decision": review_decision,
                "implementation_authorized": implementation_authorized,
                "reviewed_by": "Gear",
            }),
            encoding="utf-8",
        )

    def test_1_adapter_builds_work_packet_and_id(self) -> None:
        packet_id = adapter.mission_unit_packet_id("mission-101", "unit-001")
        self.assertEqual("wp-mission-101-unit-001", packet_id)

        patch_path = self.mission_dir / "test.patch"
        patch_path.write_text("--- a/Agency/Core/runtime/target.txt\n+++ b/Agency/Core/runtime/target.txt\n", encoding="utf-8")

        unit = {
            "id": "unit-001",
            "objective": "Update target",
            "allowed_paths": ["Agency/Core/runtime/target.txt"],
        }
        packet = adapter.build_mission_unit_work_packet(
            mission_id="mission-101",
            unit=unit,
            proposal_path=self.mission_dir / "proposal" / "proposal.json",
            review_path=self.mission_dir / "review" / "decision.json",
            patch_path=patch_path,
            baseline_hashes={"Agency/Core/runtime/target.txt": "dummy"},
            play_owner="Gear",
        )

        self.assertEqual("wp-mission-101-unit-001", packet.packet_id)
        self.assertEqual(1, packet.schema_version)
        self.assertEqual("Gear", packet.play_owner)
        self.assertEqual("Gear", packet.ball_holder)
        self.assertEqual("Gear", packet.next_decision_owner)

        errors = packet_contracts.validate_work_packet(packet, root=self.repo)
        self.assertEqual([], errors)

    def test_2_packet_steps_dependency_order(self) -> None:
        patch_path = self.mission_dir / "test.patch"
        patch_path.write_text("patch", encoding="utf-8")
        unit = {"id": "unit-001", "allowed_paths": ["Agency/Core/runtime/target.txt"]}

        packet = adapter.build_mission_unit_work_packet(
            mission_id="mission-101",
            unit=unit,
            proposal_path=self.mission_dir / "proposal" / "proposal.json",
            review_path=self.mission_dir / "review" / "decision.json",
            patch_path=patch_path,
            baseline_hashes={},
            play_owner="Gear",
        )

        self.assertEqual(2, len(packet.steps))
        apply_step, verify_step = packet.steps[0], packet.steps[1]

        self.assertEqual("apply-patch", apply_step.step_id)
        self.assertEqual("apply_patch", apply_step.operation)
        self.assertEqual([], apply_step.depends_on)

        self.assertEqual("verify", verify_step.step_id)
        self.assertEqual("verify", verify_step.operation)
        self.assertEqual(["apply-patch"], verify_step.depends_on)

    def test_3_mission_implementation_uses_editor_execution(self) -> None:
        mock_response = json.dumps({
            "unit_id": "unit-001",
            "summary": "Updated target",
            "file_changes": [
                {
                    "path": "Agency/Core/runtime/target.txt",
                    "operation": "modify",
                    "new_content": "gamma\nbeta\n",
                }
            ],
            "verification_commands": ["git status --short"],
            "rollback_notes": [],
        })
        os.environ["AGENCY_MOCK_IMPLEMENTATION_RESPONSE"] = mock_response

        deps = self._get_deps()
        rc = impl_execution.run_mission_implement(deps, "101")
        self.assertEqual(0, rc)

        packet_dir = packet_persistence.packet_dir("wp-mission-101-unit-001")
        self.assertTrue((packet_dir / "packet.json").exists())
        self.assertTrue((packet_dir / "results").exists())

    def test_4_missing_review_approval_blocks_authorization(self) -> None:
        self._write_mission_files(review_decision="rejected", implementation_authorized=False)
        mock_response = json.dumps({
            "unit_id": "unit-001",
            "summary": "Updated target",
            "file_changes": [
                {
                    "path": "Agency/Core/runtime/target.txt",
                    "operation": "modify",
                    "new_content": "gamma\nbeta\n",
                }
            ],
        })
        os.environ["AGENCY_MOCK_IMPLEMENTATION_RESPONSE"] = mock_response

        deps = self._get_deps()
        rc = impl_execution.run_mission_implement(deps, "101")
        self.assertNotEqual(0, rc)
        self.assertEqual("alpha\nbeta\n", self.target.read_text(encoding="utf-8"))

    def test_5_baseline_hash_mismatch_blocks_mutation(self) -> None:
        patch_path = self.mission_dir / "test.patch"
        patch_path.write_text("patch", encoding="utf-8")
        review = {"authority": "operator_review", "decision": "approved", "implementation_authorized": True, "reviewed_by": "Gear"}

        auth = adapter.build_patch_authorization_from_review(
            review=review,
            packet_id="wp-mission-101-unit-001",
            apply_step_id="apply-patch",
            patch_path=patch_path,
            baseline_hashes={"Agency/Core/runtime/target.txt": "wronghash"},
            allowed_paths=["Agency/Core/runtime/target.txt"],
            play_owner="Gear",
        )
        packet_persistence.save_authorization("wp-mission-101-unit-001", auth.authorization_id, auth.to_dict())

        errors = editor_execution._validate_patch_authorization(
            editor_contracts.EditorTask(
                task_id="t-1",
                schema_version=1,
                issued_by="Gear",
                editor="Editor",
                play_owner="Gear",
                ball_holder="Editor",
                next_decision_owner="Gear",
                objective="Apply patch",
                operation="apply_patch",
                scope={"include": ["Agency/Core/runtime/target.txt"], "exclude": []},
            ),
            auth,
            patch_path,
            "+++ b/Agency/Core/runtime/target.txt\n",
        )
        self.assertIn("baseline_hash_mismatch:Agency/Core/runtime/target.txt", errors)

    def test_6_successful_apply_and_verify(self) -> None:
        mock_response = json.dumps({
            "unit_id": "unit-001",
            "summary": "Updated target",
            "file_changes": [
                {
                    "path": "Agency/Core/runtime/target.txt",
                    "operation": "modify",
                    "new_content": "gamma\nbeta\n",
                }
            ],
            "verification_commands": ["git status --short"],
        })
        os.environ["AGENCY_MOCK_IMPLEMENTATION_RESPONSE"] = mock_response

        deps = self._get_deps()
        rc = impl_execution.run_mission_implement(deps, "101")
        self.assertEqual(0, rc)

        self.assertEqual("gamma\nbeta\n", self.target.read_text(encoding="utf-8"))

        result_json_path = self.mission_dir / "implementation" / "units" / "unit-001" / "result.json"
        self.assertTrue(result_json_path.exists())
        res_data = json.loads(result_json_path.read_text(encoding="utf-8"))

        self.assertEqual("wp-mission-101-unit-001", res_data["work_packet_id"])
        self.assertEqual(2, len(res_data["editor_task_ids"]))
        self.assertTrue(res_data["work_packet_path"])
        self.assertEqual(2, len(res_data["editor_result_paths"]))
        self.assertEqual("auth-wp-mission-101-unit-001-apply-patch", res_data["authorization_id"])

    def test_7_failed_verification_leaves_unit_failed(self) -> None:
        self._write_mission_files(verification_cmd=["invalid_command_that_should_fail"])
        mock_response = json.dumps({
            "unit_id": "unit-001",
            "summary": "Updated target",
            "file_changes": [
                {
                    "path": "Agency/Core/runtime/target.txt",
                    "operation": "modify",
                    "new_content": "gamma\nbeta\n",
                }
            ],
            "verification_commands": ["invalid_command_that_should_fail"],
        })
        os.environ["AGENCY_MOCK_IMPLEMENTATION_RESPONSE"] = mock_response

        deps = self._get_deps()
        rc = impl_execution.run_mission_implement(deps, "101")
        self.assertNotEqual(0, rc)

        status_path = self.mission_dir / "implementation" / "units" / "unit-001" / "status.json"
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual("failed", status_data["status"])

    def test_8_dry_run_reports_plan_no_mutation(self) -> None:
        deps = self._get_deps()
        rc = impl_execution.run_mission_implement(deps, "101", dry_run=True)
        self.assertEqual(0, rc)

        self.assertEqual("alpha\nbeta\n", self.target.read_text(encoding="utf-8"))
        packet_dir = packet_persistence.packet_dir("wp-mission-101-unit-001")
        self.assertFalse(packet_dir.exists())

    def test_9_resume_and_idempotency(self) -> None:
        mock_response = json.dumps({
            "unit_id": "unit-001",
            "summary": "Updated target",
            "file_changes": [
                {
                    "path": "Agency/Core/runtime/target.txt",
                    "operation": "modify",
                    "new_content": "gamma\nbeta\n",
                }
            ],
        })
        os.environ["AGENCY_MOCK_IMPLEMENTATION_RESPONSE"] = mock_response

        deps = self._get_deps()
        rc1 = impl_execution.run_mission_implement(deps, "101")
        self.assertEqual(0, rc1)

        rc2 = impl_execution.run_mission_implement(deps, "101")
        self.assertEqual(0, rc2)


if __name__ == "__main__":
    unittest.main()