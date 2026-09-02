from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.work.tasks.editor import contracts, execution, persistence
from Agency.Core.repository.context import builder


class EditorHandoffTests(unittest.TestCase):
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
        self.work = self.agency_root / "Agents" / "Editor" / "work" / "EditorTasks"
        self.inspections = self.agency_root / "Agents" / "Editor" / "work" / "Inspections"
        (self.runtime / "state.py").write_text(
            """def authoritative_state():
    return 'state'

def caller():
    return authoritative_state()
""",
            encoding="utf-8",
        )
        (self.runtime / "target.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        self.patches = [
            patch.object(contracts, "DASHBOARD_ROOT", self.repo),
            patch.object(execution, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "AGENCY_ROOT", self.agency_root),
            patch.object(builder, "WORK_INSPECTIONS_ROOT", self.inspections),
            patch.object(persistence, "EDITOR_TASKS_ROOT", self.work),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def task(self, **overrides):
        values = {
            "task_id": "editor-task-001",
            "schema_version": 1,
            "issued_by": "Gear",
            "editor": "Editor",
            "play_owner": "Gear",
            "ball_holder": "Editor",
            "next_decision_owner": "Gear",
            "objective": "Find the definition of authoritative_state.",
            "operation": "inspect",
            "scope": {"include": ["Agency/Core/runtime"], "exclude": []},
            "request": {"repository_context": {"operations": ["symbol_definition", "references"], "symbol": "authoritative_state"}},
            "constraints": {"read_only": True, "mutation_authorized": False},
            "evidence_requirements": ["repository_relative_path", "line_range", "excerpt"],
            "created_at": "2026-07-26T00:00:00Z",
        }
        values.update(overrides)
        return contracts.editor_task_from_mapping(values)

    def proposal_task(self, task_id="proposal-artifact"):
        return self.task(
            task_id=task_id,
            operation="propose_patch",
            request={
                "repository_context": {"operations": ["text_search"], "text": "alpha", "paths": ["Agency/Core/runtime/target.txt"]},
                "change_intent": 'replace "alpha" with "gamma" in Agency/Core/runtime/target.txt',
            },
        )

    def create_proposal_and_authorization(self):
        proposal = execution.execute_editor_task(self.proposal_task())
        patch_path = self.work / "proposal-artifact" / "proposed.patch"
        proposal_sha = hashlib.sha256(patch_path.read_bytes()).hexdigest()
        target = self.runtime / "target.txt"
        auth = contracts.PatchAuthorization(
            authorization_id="auth-001",
            work_packet_id="wp-test",
            step_id="proposal-step",
            editor_task_id=proposal.task_id,
            proposal_sha256=proposal_sha,
            baseline_hashes={"Agency/Core/runtime/target.txt": hashlib.sha256(target.read_bytes()).hexdigest()},
            authorized_by="Gear",
            play_owner="Gear",
            authorized_editor="Editor",
            allowed_paths=["Agency/Core/runtime/target.txt"],
            allowed_operations=["apply_patch"],
            created_at="2026-07-26T00:00:00Z",
            expires_at="2999-01-01T00:00:00Z",
            proposal_path="Agency/Agents/Editor/work/EditorTasks/proposal-artifact/proposed.patch",
        )
        auth_path = self.repo / "Agency" / "Agents" / "Editor" / "work" / "auth.json"
        persistence.atomic_json(auth_path, auth.to_dict())
        return proposal, patch_path, auth, auth_path

    def test_valid_tasks_and_contract_rejections(self) -> None:
        self.assertEqual([], contracts.validate_editor_task(self.task(), root=self.repo))
        self.assertEqual([], contracts.validate_editor_task(self.proposal_task(), root=self.repo))
        legacy_errors = contracts.validate_editor_task(self.task(editor="Cali", ball_holder="Cali"), root=self.repo)
        self.assertIn("editor_must_be_Editor_for_current_adapter", legacy_errors)
        self.assertTrue(contracts.validate_editor_task(self.task(play_owner="", next_decision_owner=""), root=self.repo))
        self.assertTrue(contracts.validate_editor_task(self.task(next_decision_owner="Seth"), root=self.repo))
        self.assertTrue(contracts.validate_editor_task(self.task(ball_holder="Gear"), root=self.repo))
        self.assertTrue(contracts.validate_editor_task(self.task(operation="apply_patch"), root=self.repo))
        self.assertTrue(contracts.validate_editor_task(self.task(scope={"include": ["/etc"], "exclude": []}), root=self.repo))

    def test_inspect_result_returns_ball_and_evidence(self) -> None:
        result = execution.execute_editor_task(self.task())

        self.assertEqual("completed", result.status)
        self.assertEqual("Gear", result.play_owner)
        self.assertEqual("Gear", result.ball_holder)
        self.assertEqual("Gear", result.next_decision_owner)
        self.assertTrue(result.throw_completed)
        self.assertFalse(result.commit_performed)
        self.assertFalse(result.acceptance_claimed)
        symbols = result.evidence_bundle["symbols"]
        self.assertTrue(any(item["qualified_name"] == "authoritative_state" for item in symbols))

    def test_negative_symbol_lookup_returns_negative_evidence(self) -> None:
        result = execution.execute_editor_task(self.task(
            task_id="negative-symbol",
            request={"repository_context": {"operations": ["symbol_definition"], "symbol": "definitely_not_a_real_symbol_7f91"}},
        ))
        self.assertEqual("completed", result.status)
        self.assertEqual("not_found_within_scope", result.evidence_bundle["negative_results"][0]["result"])
        self.assertEqual("Gear", result.ball_holder)

    def test_propose_patch_creates_artifact_without_source_mutation(self) -> None:
        target = self.runtime / "target.txt"
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        result = execution.execute_editor_task(self.proposal_task())
        after = hashlib.sha256(target.read_bytes()).hexdigest()

        self.assertEqual("completed", result.status)
        self.assertEqual(before, after)
        self.assertEqual([], result.repository_mutations)
        self.assertTrue((self.work / "proposal-artifact" / "proposed.patch").exists())
        self.assertTrue(result.patch_artifacts)
        self.assertIsNotNone(result.proposal_sha256)

    def test_malformed_change_intent_returns_guidance_without_artifacts(self) -> None:
        target = self.runtime / "target.txt"
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        cases = {
            "malformed-intent": "please change alpha to gamma",
            "ambiguous-intent": "make the runtime target better",
        }
        for task_id, change_intent in cases.items():
            with self.subTest(task_id=task_id):
                result = execution.execute_editor_task(self.task(
                    task_id=task_id,
                    operation="propose_patch",
                    request={
                        "repository_context": {"operations": ["text_search"], "text": "alpha", "paths": ["Agency/Core/runtime/target.txt"]},
                        "change_intent": change_intent,
                    },
                ))

                after = hashlib.sha256(target.read_bytes()).hexdigest()
                self.assertEqual("blocked", result.status)
                self.assertEqual(before, after)
                self.assertEqual([], result.repository_mutations)
                self.assertEqual([], result.patch_artifacts)
                self.assertIsNone(result.proposal_sha256)
                self.assertFalse((self.work / task_id / "proposed.patch").exists())
                unresolved = result.unresolveds[0]
                self.assertEqual("change_intent_must_match_replace_quoted_text_with_quoted_text_in_path", unresolved["reason"])
                self.assertEqual("Invalid change_intent.", unresolved["message"])
                self.assertIn('replace "<old>" with "<new>" in <repository path>', unresolved["guidance"])
                self.assertEqual('replace "<old text>" with "<new text>" in <repository path>', unresolved["expected_format"])
                self.assertEqual('replace "alpha" with "gamma" in Agency/Core/runtime/target.txt', unresolved["example"])

    def test_authorization_failures_reject_apply_patch(self) -> None:
        _proposal, patch_path, auth, auth_path = self.create_proposal_and_authorization()
        cases = [
            ("missing-auth", None, None),
            ("modified-proposal", {**auth.to_dict(), "proposal_sha256": "bad"}, auth_path),
            ("baseline-drift", {**auth.to_dict(), "baseline_hashes": {"Agency/Core/runtime/target.txt": "bad"}}, auth_path),
            ("unauthorized-path", {**auth.to_dict(), "allowed_paths": ["Agency/Core/runtime/other.txt"]}, auth_path),
            ("expired", {**auth.to_dict(), "expires_at": "2000-01-01T00:00:00Z"}, auth_path),
            ("legacy-cali-authorization", {**auth.to_dict(), "authorized_editor": "Cali"}, auth_path),
        ]
        for task_id, auth_data, path in cases:
            request = {"proposal_patch_path": "Agency/Agents/Editor/work/EditorTasks/proposal-artifact/proposed.patch"}
            if auth_data is not None:
                persistence.atomic_json(path, auth_data)
                request["authorization_path"] = "Agency/Agents/Editor/work/auth.json"
            result = execution.execute_editor_task(self.task(
                task_id=task_id,
                operation="apply_patch",
                request=request,
                constraints={"read_only": False, "mutation_authorized": True},
            ))
            self.assertEqual("rejected", result.status, task_id)
            self.assertEqual("Gear", result.ball_holder)
        self.assertTrue(patch_path.exists())

    def test_authorized_patch_applies_once_and_verification_runs(self) -> None:
        _proposal, _patch_path, _auth, _auth_path = self.create_proposal_and_authorization()
        target = self.runtime / "target.txt"
        before = target.read_text(encoding="utf-8")
        result = execution.execute_editor_task(self.task(
            task_id="apply-authorized",
            operation="apply_patch",
            request={
                "proposal_patch_path": "Agency/Agents/Editor/work/EditorTasks/proposal-artifact/proposed.patch",
                "authorization_path": "Agency/Agents/Editor/work/auth.json",
            },
            constraints={"read_only": False, "mutation_authorized": True},
        ))

        self.assertEqual("completed", result.status)
        self.assertIn("gamma", target.read_text(encoding="utf-8"))
        self.assertNotEqual(before, target.read_text(encoding="utf-8"))
        self.assertTrue(result.repository_mutations)
        self.assertFalse(result.commit_performed)
        self.assertFalse(result.acceptance_claimed)
        self.assertEqual("Gear", result.ball_holder)

        reused = execution.execute_editor_task(self.task(
            task_id="apply-reuse",
            operation="apply_patch",
            request={
                "proposal_patch_path": "Agency/Agents/Editor/work/EditorTasks/proposal-artifact/proposed.patch",
                "authorization_path": "Agency/Agents/Editor/work/auth.json",
            },
            constraints={"read_only": False, "mutation_authorized": True},
        ))
        self.assertEqual("rejected", reused.status)
        self.assertIn("authorization_already_used", reused.errors[0]["details"])

        verify = execution.execute_editor_task(self.task(
            task_id="verify",
            operation="verify",
            request={"verification": {"commands": ["git diff --check", "git status --short"]}},
            constraints={"read_only": True, "mutation_authorized": False},
        ))
        self.assertEqual("completed", verify.status)
        self.assertTrue(verify.verification_results)
        self.assertFalse(verify.acceptance_claimed)

    def test_persistence_round_trip_and_cli_submit(self) -> None:
        task = self.task(task_id="persisted")
        first = execution.execute_editor_task(task)
        duplicate = execution.execute_editor_task(task)
        self.assertEqual("completed", first.status)
        self.assertEqual("rejected", duplicate.status)
        self.assertEqual("persisted", persistence.load_task("persisted")["task_id"])
        self.assertIn("task_returned", (self.work / "persisted" / "events.jsonl").read_text(encoding="utf-8"))

        task_path = self.root / "editor-task.yaml"
        task_path.write_text(
            """schema_version: 1
task_id: editor-authoritative-state-001
issued_by: Gear
editor: Editor
play_owner: Gear
ball_holder: Editor
next_decision_owner: Gear
objective: Find the definition of authoritative_state.
operation: inspect
scope:
  include:
    - Agency/Core/runtime
  exclude: []
request:
  repository_context:
    operations:
      - symbol_definition
    symbol: authoritative_state
constraints:
  read_only: true
  mutation_authorized: false
evidence_requirements:
  - repository_relative_path
  - line_range
  - excerpt
""",
            encoding="utf-8",
        )
        result = execution.submit_task_file(task_path)
        payload = execution.result_payload(result)
        self.assertEqual("completed", payload["status"])
        self.assertEqual("Gear", payload["ball_holder"])
        self.assertTrue(payload["evidence_loaded"])


if __name__ == "__main__":
    unittest.main()
