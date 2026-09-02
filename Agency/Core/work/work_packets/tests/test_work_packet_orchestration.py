from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.work.tasks.editor import contracts as editor_contracts
from Agency.Core.work.tasks.editor import execution as editor_execution
from Agency.Core.work.tasks.editor import persistence as editor_persistence
from Agency.Core.repository.context import builder
from Agency.Core.work.work_packets import contracts, execution, persistence


class WorkPacketOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        self.agency_root = self.repo / "Agency"
        self.runtime = self.agency_root / "Core" / "runtime"
        self.runtime.mkdir(parents=True)
        (self.runtime / "authoritative_state.py").write_text(
            """from __future__ import annotations

def authoritative_state():
    return 'state'
""",
            encoding="utf-8",
        )
        self.work_packets = self.agency_root / "Agents" / "Editor" / "work" / "WorkPackets"
        self.editor_tasks = self.agency_root / "Agents" / "Editor" / "work" / "EditorTasks"
        self.inspections = self.agency_root / "Agents" / "Editor" / "work" / "Inspections"
        self.patches = [
            patch.object(editor_contracts, "DASHBOARD_ROOT", self.repo),
            patch.object(editor_execution, "DASHBOARD_ROOT", self.repo),
            patch.object(execution, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "AGENCY_ROOT", self.agency_root),
            patch.object(builder, "WORK_INSPECTIONS_ROOT", self.inspections),
            patch.object(editor_persistence, "EDITOR_TASKS_ROOT", self.editor_tasks),
            patch.object(persistence, "WORK_PACKETS_ROOT", self.work_packets),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def packet_data(self, **overrides):
        data = {
            "packet_id": "wp-editor-handoff-001",
            "schema_version": 1,
            "title": "Inspect, propose, apply, and verify bounded runtime change",
            "objective": "Demonstrate Gear-controlled multi-step Editor workflow.",
            "created_by": "Gear",
            "play_owner": "Gear",
            "ball_holder": "Gear",
            "next_decision_owner": "Gear",
            "status": "draft",
            "scope": {"include": ["Agency/Core/runtime"], "exclude": []},
            "constraints": {"mutation_authorized": False},
            "acceptance_criteria": [
                "authoritative_state definition is located with evidence",
                "patch proposal is produced before authorization",
                "authorized patch is applied without commit or acceptance",
            ],
            "steps": [
                {
                    "step_id": "inspect-authoritative-state",
                    "sequence": 1,
                    "title": "Inspect authoritative_state",
                    "objective": "Find the definition of authoritative_state.",
                    "operation": "inspect",
                    "status": "pending",
                    "depends_on": [],
                    "evidence_requirements": ["repository_relative_path", "line_range", "excerpt"],
                },
                {
                    "step_id": "propose-bounded-change",
                    "sequence": 2,
                    "title": "Propose a bounded change",
                    "objective": "Produce a non-applied patch using an explicitly supported deterministic replacement intent.",
                    "operation": "propose_patch",
                    "status": "pending",
                    "depends_on": ["inspect-authoritative-state"],
                    "request": {
                        "repository_context": {"operations": ["text_search"], "text": "from __future__ import annotations"},
                        "change_intent": 'replace "from __future__ import annotations" with "from __future__ import generator_stop" in Agency/Core/runtime/authoritative_state.py',
                    },
                    "evidence_requirements": ["supporting_evidence", "proposed_patch", "source_unchanged_proof"],
                },
                {
                    "step_id": "apply-authorized-change",
                    "sequence": 3,
                    "title": "Apply authorized patch",
                    "objective": "Apply the authorized patch artifact.",
                    "operation": "apply_patch",
                    "status": "pending",
                    "depends_on": ["propose-bounded-change"],
                    "evidence_requirements": ["patch_authorization", "baseline_hashes"],
                },
                {
                    "step_id": "verify-authorized-change",
                    "sequence": 4,
                    "title": "Verify bounded change",
                    "objective": "Run approved verification evidence collection.",
                    "operation": "verify",
                    "status": "pending",
                    "depends_on": ["apply-authorized-change"],
                    "request": {"verification": {"commands": ["git diff --check", "git status --short"]}},
                    "evidence_requirements": ["verification_results"],
                },
            ],
            "unresolveds": [],
            "contradictions": [],
            "created_at": "2026-07-26T00:00:00Z",
            "updated_at": "2026-07-26T00:00:00Z",
        }
        data.update(overrides)
        return data

    def packet(self, **overrides):
        return contracts.packet_from_mapping(self.packet_data(**overrides))

    def write_packet(self, data=None) -> Path:
        path = self.root / "packet.yaml"
        import yaml

        path.write_text(yaml.safe_dump(data or self.packet_data(), sort_keys=False), encoding="utf-8")
        return path

    def create_packet(self):
        payload = execution.create_packet_from_file(self.write_packet())
        self.assertTrue(payload["ok"], payload)
        return payload

    def select_dispatch(self, step_id: str):
        self.assertTrue(execution.select_step("wp-editor-handoff-001", step_id, "Gear")["ok"])
        payload = execution.dispatch_step("wp-editor-handoff-001", step_id, "Gear")
        self.assertTrue(payload["ok"], payload)
        return payload

    def test_valid_packet_contract_and_rejections(self) -> None:
        self.assertEqual([], contracts.validate_work_packet(self.packet(), root=self.repo))
        base_steps = self.packet_data()["steps"]
        cases = [
            self.packet(play_owner="", ball_holder="", next_decision_owner=""),
            self.packet(next_decision_owner="Seth"),
            self.packet(steps=[base_steps[0], base_steps[0]]),
            self.packet(steps=[base_steps[0], {**base_steps[1], "sequence": 1}]),
            self.packet(steps=[{**base_steps[0], "depends_on": ["missing"]}]),
            self.packet(steps=[{**base_steps[0], "depends_on": ["propose-bounded-change"]}, {**base_steps[1], "depends_on": ["inspect-authoritative-state"]}]),
            self.packet(steps=[{**base_steps[0], "scope": {"include": ["Agency/Core/work/tasks/editor"], "exclude": []}}]),
            self.packet(steps=[{**base_steps[0], "operation": "commit"}]),
            self.packet(steps=[]),
        ]
        for item in cases:
            self.assertTrue(contracts.validate_work_packet(item, root=self.repo))

    def test_selection_is_explicit_and_does_not_invoke_editor(self) -> None:
        self.create_packet()
        with patch.object(execution, "execute_editor_task") as mocked:
            payload = execution.select_step("wp-editor-handoff-001", "inspect-authoritative-state", "Gear")
        self.assertTrue(payload["ok"], payload)
        self.assertEqual("active", payload["status"])
        self.assertEqual("Gear", payload["ball_holder"])
        mocked.assert_not_called()
        events = (self.work_packets / "wp-editor-handoff-001" / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn("packet_activated", events)
        self.assertIn("step_selected", events)

    def test_dispatch_transfers_and_returns_ball(self) -> None:
        self.create_packet()
        payload = self.select_dispatch("inspect-authoritative-state")
        packet = payload["packet"]
        step1 = [item for item in packet["steps"] if item["step_id"] == "inspect-authoritative-state"][0]
        step2 = [item for item in packet["steps"] if item["step_id"] == "propose-bounded-change"][0]

        self.assertEqual("active", payload["status"])
        self.assertEqual("Gear", payload["play_owner"])
        self.assertEqual("Gear", payload["ball_holder"])
        self.assertEqual("Gear", payload["next_decision_owner"])
        self.assertEqual("completed", step1["status"])
        self.assertEqual("pending", step2["status"])
        self.assertTrue(payload["no_next_step_selected"])
        task_ref = json.loads((self.work_packets / "wp-editor-handoff-001" / "tasks" / f"{payload['editor_task_id']}.json").read_text(encoding="utf-8"))
        self.assertEqual("Editor", task_ref["task"]["editor"])
        self.assertEqual("Editor", task_ref["task"]["ball_holder"])
        events = (self.work_packets / "wp-editor-handoff-001" / "events.jsonl").read_text(encoding="utf-8")
        for name in ("ball_thrown", "ball_received", "ball_returned", "ball_received_back"):
            self.assertIn(name, events)
        self.assertIn('"to_holder": "Editor"', events)
        self.assertIn('"by": "Editor"', events)
        self.assertIn('"from_holder": "Editor"', events)
        throw_paths = list((self.work_packets / "wp-editor-handoff-001" / "throws").glob("*.json"))
        self.assertTrue(throw_paths)
        throw_record = json.loads(throw_paths[0].read_text(encoding="utf-8"))
        self.assertEqual("Editor", throw_record["to"])

    def test_unmet_dependency_and_second_selection_are_rejected(self) -> None:
        self.create_packet()
        self.assertFalse(execution.select_step("wp-editor-handoff-001", "propose-bounded-change", "Gear")["ok"])
        self.assertTrue(execution.select_step("wp-editor-handoff-001", "inspect-authoritative-state", "Gear")["ok"])
        second = execution.select_step("wp-editor-handoff-001", "propose-bounded-change", "Gear")
        self.assertFalse(second["ok"])

    def test_blocked_result_returns_ball_and_blocks_packet(self) -> None:
        data = self.packet_data(steps=[{
            **self.packet_data()["steps"][0],
            "operation": "propose_patch",
            "request": {
                "repository_context": {"operations": ["text_search"], "text": "missing evidence"},
                "change_intent": 'replace "x" with "y" in Agency/Core/runtime/authoritative_state.py',
            },
        }])
        self.assertTrue(execution.create_packet_from_file(self.write_packet(data))["ok"])
        payload = self.select_dispatch("inspect-authoritative-state")
        self.assertEqual("blocked", payload["status"])
        self.assertEqual("Gear", payload["ball_holder"])

    def test_authorize_apply_verify_flow(self) -> None:
        self.create_packet()
        target = self.runtime / "authoritative_state.py"
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        self.select_dispatch("inspect-authoritative-state")
        self.select_dispatch("propose-bounded-change")
        auth_payload = execution.authorize_patch("wp-editor-handoff-001", "propose-bounded-change", "Gear")
        self.assertTrue(auth_payload["ok"], auth_payload)
        self.assertEqual("Gear", auth_payload["play_owner"])
        self.assertEqual("Gear", auth_payload["ball_holder"])
        self.assertEqual("Editor", auth_payload["authorization"]["authorized_editor"])
        apply_payload = self.select_dispatch("apply-authorized-change")
        after_apply = hashlib.sha256(target.read_bytes()).hexdigest()
        self.assertNotEqual(before, after_apply)
        self.assertEqual("Gear", apply_payload["ball_holder"])
        apply_step = [item for item in apply_payload["packet"]["steps"] if item["step_id"] == "apply-authorized-change"][0]
        self.assertTrue(apply_step["result_summary"]["repository_mutation_performed"])
        self.assertFalse(apply_step["result_summary"]["commit_performed"])
        self.assertFalse(apply_step["result_summary"]["acceptance_claimed"])
        verify_payload = self.select_dispatch("verify-authorized-change")
        self.assertEqual("completed", verify_payload["status"])
        verify_step = [item for item in verify_payload["packet"]["steps"] if item["step_id"] == "verify-authorized-change"][0]
        self.assertEqual("completed", verify_step["status"])
        self.assertFalse(verify_step["result_summary"]["acceptance_claimed"])

    def test_authorization_baseline_drift_blocks_apply(self) -> None:
        self.create_packet()
        self.select_dispatch("inspect-authoritative-state")
        self.select_dispatch("propose-bounded-change")
        auth_payload = execution.authorize_patch("wp-editor-handoff-001", "propose-bounded-change", "Gear")
        self.assertTrue(auth_payload["ok"])
        self.assertEqual("Editor", auth_payload["authorization"]["authorized_editor"])
        (self.runtime / "authoritative_state.py").write_text("drift\n", encoding="utf-8")
        execution.select_step("wp-editor-handoff-001", "apply-authorized-change", "Gear")
        payload = execution.dispatch_step("wp-editor-handoff-001", "apply-authorized-change", "Gear")
        self.assertEqual("blocked", payload["status"])
        self.assertEqual("rejected", payload["packet"]["steps"][2]["status"])
        self.assertEqual("Gear", payload["ball_holder"])

    def test_round_trip_and_completion_not_acceptance(self) -> None:
        path = self.write_packet()
        self.assertTrue(execution.create_packet_from_file(path)["ok"])
        for step_id in ("inspect-authoritative-state", "propose-bounded-change"):
            self.assertTrue(execution.select_step("wp-editor-handoff-001", step_id, "Gear")["ok"])
            self.assertTrue(execution.dispatch_step("wp-editor-handoff-001", step_id, "Gear")["ok"])
        self.assertTrue(execution.authorize_patch("wp-editor-handoff-001", "propose-bounded-change", "Gear")["ok"])
        for step_id in ("apply-authorized-change", "verify-authorized-change"):
            self.assertTrue(execution.select_step("wp-editor-handoff-001", step_id, "Gear")["ok"])
            self.assertTrue(execution.dispatch_step("wp-editor-handoff-001", step_id, "Gear")["ok"])
        result = execution.packet_result("wp-editor-handoff-001")
        self.assertTrue(result["operational_completion_is_not_acceptance"])
        self.assertFalse(result["accepted"])
        self.assertFalse(result["validated"])
        self.assertFalse(result["committed"])


if __name__ == "__main__":
    unittest.main()
