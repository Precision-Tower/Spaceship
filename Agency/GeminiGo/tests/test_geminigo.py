from __future__ import annotations

import datetime
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.GeminiGo.bootstrap import BOOTSTRAP_CONTRACT
from Agency.GeminiGo import state
from Agency.GeminiGo.session import needs_rotation, quota_day
from Agency.GeminiGo.worker import run_turn
from Agency.GeminiGo.supervisor import execute_with_failover


class GeminiGoTest(unittest.TestCase):
    def test_bootstrap_preserves_authority_and_stop_contract(self) -> None:
        self.assertIn("Agency Core owns Mission, WorkPacket", BOOTSTRAP_CONTRACT)
        self.assertIn("GEMINIGO_STOP(CLEAN)", BOOTSTRAP_CONTRACT)
        self.assertIn("Reserve credentials are for provider quota", BOOTSTRAP_CONTRACT)

    def test_state_is_reconstructable_and_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(state, "state_root", return_value=Path(tmp)):
                initial = state.load_state("alpha")
                self.assertEqual(0, initial["turn"])
                self.assertIsNone(initial["interaction_id"])
                state.save_state("alpha", {**initial, "turn": 1})
                state.append_event("alpha", "one")
                state.append_event("alpha", "two")
                self.assertEqual(["one", "two"], [x["event"] for x in state.recent_events("alpha")])

    def test_worker_reuses_server_interaction_and_stops_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            def fake(**kwargs):
                calls.append(kwargs)
                return {
                    "ok": True, "status": "response_received", "model": "test-model",
                    "interaction_id": "ix-2" if kwargs["previous_interaction_id"] else "ix-1",
                    "response_text": "continue" if not kwargs["previous_interaction_id"] else "GEMINIGO_STOP(CLEAN)",
                }
            with (
                patch.object(state, "state_root", return_value=Path(tmp)),
                patch("Agency.GeminiGo.worker.load_state", side_effect=state.load_state),
                patch("Agency.GeminiGo.worker.save_state", side_effect=state.save_state),
                patch("Agency.GeminiGo.worker.append_event", side_effect=state.append_event),
                patch("Agency.GeminiGo.worker.execute_with_failover", side_effect=fake),
            ):
                first = run_turn(session_id="alpha", purpose="audit", request="start")
                second = run_turn(session_id="alpha", purpose="audit", request="continue")
                self.assertIsNone(calls[0]["previous_interaction_id"])
                self.assertEqual("ix-1", calls[1]["previous_interaction_id"])
                self.assertEqual("CLEAN", second["stop_reason"])
                self.assertEqual("stopped", state.load_state("alpha")["session_status"])
                self.assertFalse(first["repository_mutation_performed"])

    def test_quota_day_rotation_is_pacific_day(self) -> None:
        before = datetime.datetime(2026, 9, 8, 6, 59, tzinfo=datetime.timezone.utc)
        after = datetime.datetime(2026, 9, 8, 7, 1, tzinfo=datetime.timezone.utc)
        self.assertNotEqual(quota_day(before), quota_day(after))
        self.assertTrue(needs_rotation({"interaction_id": "x", "quota_day": quota_day(before)}, now=after))


    def test_failover_only_for_provider_capacity(self) -> None:
        calls = []
        def fake(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return {
                    "ok": False,
                    "status": "provider_temporarily_unavailable",
                    "error_detail": "429 RESOURCE_EXHAUSTED",
                }
            return {
                "ok": True,
                "status": "response_received",
                "interaction_id": "reserve-1",
                "response_text": "continued",
            }

        with (
            patch("Agency.GeminiGo.supervisor.api_key", side_effect=lambda slot: f"{slot}-key"),
        ):
            result = execute_with_failover(
                call=fake,
                previous_interaction_id="primary-1",
                purpose="work",
                context="checkpoint",
                system_instruction="system",
            )
        self.assertEqual(2, len(calls))
        self.assertEqual("primary-1", calls[0]["previous_interaction_id"])
        self.assertIsNone(calls[1]["previous_interaction_id"])
        self.assertIn("FAILOVER_CHECKPOINT:", calls[1]["context"])
        self.assertIn("primary_failure=quota", calls[1]["context"])
        self.assertIn("checkpoint", calls[1]["context"])
        self.assertEqual("reserve", result["credential_slot"])

    def test_packet_id_changes_with_authored_action(self) -> None:
        from Agency.GeminiGo.dispatch import packet_id_for

        task = {
            "identity": "kernel.driver_discovery",
            "state": "active",
            "summary": "discover kernel",
            "next": "inspect graphics",
            "lane": "kernel",
        }
        changed = dict(task)
        changed["next"] = "inspect battery power thermal"

        self.assertEqual(packet_id_for(task), packet_id_for(dict(task)))
        self.assertNotEqual(packet_id_for(task), packet_id_for(changed))

    def test_action_fingerprint_is_stable_and_changes_with_authored_work(self) -> None:
        from Agency.GeminiGo.dispatch import action_fingerprint
        task = {
            "identity": "agency.example",
            "state": "ready",
            "summary": "Inspect bounded Agency work",
            "next": "Collect evidence",
        }
        self.assertEqual(action_fingerprint(task), action_fingerprint(dict(task)))
        changed = {**task, "next": "Collect different evidence"}
        self.assertNotEqual(action_fingerprint(task), action_fingerprint(changed))


    def test_read_only_assignment_enters_core_workpacket_authority(self) -> None:
        from Agency.GeminiGo.dispatch import build_inspection_packet
        from Agency.Core.work.work_packets.contracts import validate_work_packet

        task = {
            "identity": "agency.example",
            "state": "ready",
            "summary": "Inspect bounded Agency work",
            "next": "Collect evidence",
        }
        packet = build_inspection_packet(task)
        self.assertEqual("Gear", packet.play_owner)
        self.assertEqual(["Agency"], packet.scope["include"])
        self.assertEqual(["Agency/checklist.qps"], packet.steps[0].scope["include"])
        self.assertEqual(1, len(packet.steps))
        self.assertEqual("inspect", packet.steps[0].operation)
        self.assertTrue(packet.steps[0].constraints["read_only"])
        self.assertFalse(packet.constraints["mutation_authorized"])
        self.assertEqual([], validate_work_packet(packet, root=Path.cwd()))


    def test_availability_failure_activates_reserve_with_fresh_checkpoint(self) -> None:
        calls = []
        def fake(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return {
                    "ok": False,
                    "status": "provider_temporarily_unavailable",
                    "error_detail": "503 service unavailable",
                }
            return {
                "ok": True,
                "status": "response_received",
                "interaction_id": "reserve-availability-1",
                "response_text": "continued",
            }

        with patch("Agency.GeminiGo.supervisor.api_key", side_effect=lambda slot: f"{slot}-key"):
            result = execute_with_failover(
                call=fake,
                previous_interaction_id="primary-availability-1",
                purpose="work",
                context="bounded evidence",
                system_instruction="system",
            )
        self.assertEqual(2, len(calls))
        self.assertEqual("primary-availability-1", calls[0]["previous_interaction_id"])
        self.assertIsNone(calls[1]["previous_interaction_id"])
        self.assertIn("FAILOVER_CHECKPOINT:", calls[1]["context"])
        self.assertIn("primary_failure=availability", calls[1]["context"])
        self.assertIn("bounded evidence", calls[1]["context"])
        self.assertEqual("reserve", result["credential_slot"])


    def test_local_eval_records_runtime_block_without_model_call(self) -> None:
        from Agency.GeminiGo import local_eval

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(local_eval, "evaluation_root", return_value=Path(tmp)),
            patch.object(local_eval, "runtime_snapshot", return_value={
                "ok": False,
                "status": "model_unavailable",
                "reason": "configured local GGUF is absent",
                "configured": {},
            }),
        ):
            calls = []
            result = local_eval.evaluate_prompt(
                evaluation_id="blocked-runtime",
                prompt="What is your CE-OS role?",
                expected_capability="identity_and_authority",
                ask_call=lambda *args, **kwargs: calls.append((args, kwargs)),
            )
            self.assertEqual([], calls)
            self.assertEqual("runtime", result["failure_class"])
            self.assertEqual("", result["response"])
            self.assertTrue(Path(result["evidence_path"]).is_file())
            self.assertTrue(result["training_evidence_only"])
            self.assertFalse(result["establishes_architectural_truth"])

    def test_local_eval_captures_response_and_latency_surface(self) -> None:
        from Agency.GeminiGo import local_eval

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(local_eval, "evaluation_root", return_value=Path(tmp)),
            patch.object(local_eval, "runtime_snapshot", return_value={
                "ok": True,
                "status": "healthy",
                "reason": "",
                "configured": {"profile": "test"},
                "observed": {"ok": True, "status": "healthy"},
            }),
        ):
            result = local_eval.evaluate_prompt(
                evaluation_id="healthy-runtime",
                prompt="Name the authority boundary.",
                expected_capability="authority_boundary",
                ask_call=lambda *args, **kwargs: {
                    "ok": True,
                    "status": "completed",
                    "response": "Core owns mutation authority.",
                },
            )
            self.assertEqual("Core owns mutation authority.", result["response"])
            self.assertIsNone(result["failure_class"])
            self.assertGreaterEqual(result["latency_ms"], 0)
            self.assertTrue(Path(result["evidence_path"]).is_file())


    def test_daemon_cycle_dispatches_authored_work_then_calls_worker(self) -> None:
        from Agency.GeminiGo import daemon

        task = {
            "identity": "agency.synthetic",
            "state": "ready",
            "summary": "Synthetic bounded task",
            "next": "Inspect evidence",
        }
        initial = {
            **state.initial_state("cycle"),
            "last_wake_quota_day": "old-day",
        }
        saved = []
        worker_calls = []
        with (
            patch.object(daemon, "load_state", return_value=initial),
            patch.object(daemon, "save_state", side_effect=lambda sid, payload: saved.append(dict(payload))),
            patch.object(daemon, "append_event"),
            patch.object(daemon, "repository_fingerprint", return_value={"agency": "one"}),
            patch.object(daemon, "select_assignment", return_value=task),
            patch.object(daemon, "dispatch_read_only_assignment", return_value={
                "ok": True,
                "stage": "dispatch",
                "packet_id": "wp-1",
                "editor_result_status": "completed",
                "editor_result_path": "Agency/result.json",
                "repository_mutation_performed": False,
            }),
            patch.object(daemon, "run_turn", side_effect=lambda **kwargs: worker_calls.append(kwargs) or {
                "stop_reason": "CLEAN",
            }),
        ):
            result = daemon.run_cycle(session_id="cycle")

        self.assertEqual("worker_turn", result["action"])
        self.assertEqual("agency.synthetic", result["assignment"])
        self.assertEqual(1, len(worker_calls))
        self.assertEqual("wp-1", worker_calls[0]["work_packet_id"])
        self.assertIn("REPOSITORY_MUTATION_PERFORMED: false", worker_calls[0]["evidence"])

    def test_daemon_repeated_action_stops_without_dispatch_or_api(self) -> None:
        from Agency.GeminiGo import daemon
        from Agency.GeminiGo.dispatch import action_fingerprint

        task = {
            "identity": "agency.synthetic",
            "state": "ready",
            "summary": "Synthetic bounded task",
            "next": "Inspect evidence",
        }
        current = {
            **state.initial_state("repeat"),
            "last_wake_quota_day": "old-day",
            "last_action_fingerprint": action_fingerprint(task),
        }
        dispatch_calls = []
        worker_calls = []
        with (
            patch.object(daemon, "load_state", return_value=current),
            patch.object(daemon, "save_state"),
            patch.object(daemon, "append_event"),
            patch.object(daemon, "repository_fingerprint", return_value={"agency": "same"}),
            patch.object(daemon, "select_assignment", return_value=task),
            patch.object(daemon, "dispatch_read_only_assignment", side_effect=lambda x: dispatch_calls.append(x)),
            patch.object(daemon, "run_turn", side_effect=lambda **kwargs: worker_calls.append(kwargs)),
        ):
            result = daemon.run_cycle(session_id="repeat")

        self.assertEqual("repeated_action_fingerprint", result["reason"])
        self.assertEqual([], dispatch_calls)
        self.assertEqual([], worker_calls)


    def test_no_eligible_work_runs_final_audit_once_then_sleeps_clean(self) -> None:
        from Agency.GeminiGo import daemon

        fingerprint = {"agency": "final"}
        initial = {
            **state.initial_state("final-audit"),
            "last_wake_quota_day": "old-day",
        }
        saved = []
        audit_calls = []
        with (
            patch.object(daemon, "load_state", return_value=initial),
            patch.object(daemon, "save_state", side_effect=lambda sid, payload: saved.append(dict(payload))),
            patch.object(daemon, "append_event"),
            patch.object(daemon, "repository_fingerprint", return_value=fingerprint),
            patch.object(daemon, "select_assignment", return_value=None),
            patch.object(daemon, "run_final_audit", side_effect=lambda: audit_calls.append(True) or {
                "ok": True,
                "status": "clean",
                "returncode": 0,
                "stdout": "",
                "stderr": "",
            }),
        ):
            result = daemon.run_cycle(session_id="final-audit")

        self.assertEqual("sleep", result["action"])
        self.assertEqual("final_audit_clean", result["reason"])
        self.assertEqual([True], audit_calls)
        self.assertEqual(fingerprint, saved[-1]["last_final_audit_fingerprint"])
        self.assertEqual("final_audit_clean", saved[-1]["sleep_reason"])

    def test_matching_final_audit_fingerprint_does_not_rerun_audit(self) -> None:
        from Agency.GeminiGo import daemon

        fingerprint = {"agency": "final"}
        current = {
            **state.initial_state("final-audit-repeat"),
            "last_wake_quota_day": "old-day",
            "last_final_audit_fingerprint": fingerprint,
        }
        audit_calls = []
        with (
            patch.object(daemon, "load_state", return_value=current),
            patch.object(daemon, "save_state"),
            patch.object(daemon, "append_event"),
            patch.object(daemon, "repository_fingerprint", return_value=fingerprint),
            patch.object(daemon, "select_assignment", return_value=None),
            patch.object(daemon, "run_final_audit", side_effect=lambda: audit_calls.append(True)),
        ):
            result = daemon.run_cycle(session_id="final-audit-repeat")

        self.assertEqual("sleep", result["action"])
        self.assertEqual("final_audit_already_recorded", result["reason"])
        self.assertEqual([], audit_calls)


    def test_non_capacity_failure_does_not_activate_reserve(self) -> None:
        calls = []
        def fake(**kwargs):
            calls.append(kwargs)
            return {"ok": False, "status": "error", "error_detail": "invalid request"}

        with patch("Agency.GeminiGo.supervisor.api_key", side_effect=lambda slot: f"{slot}-key"):
            result = execute_with_failover(
                call=fake,
                previous_interaction_id="primary-1",
                purpose="work",
                context="checkpoint",
                system_instruction="system",
            )
        self.assertEqual(1, len(calls))
        self.assertEqual("primary", result["credential_slot"])


if __name__ == "__main__":
    unittest.main()

class GeminiGoOperatorStatusTest(unittest.TestCase):
    def test_status_reports_slots_without_exposing_credentials(self) -> None:
        from Agency.GeminiGo import status
        events = [
            {
                "event": "provider_attempt",
                "timestamp": "2026-09-08T21:00:00Z",
                "credential_slot": "primary",
                "ok": False,
                "status": "provider_temporarily_unavailable",
                "failure_class": "quota",
                "reason": "429 RESOURCE_EXHAUSTED",
            },
            {
                "event": "provider_attempt",
                "timestamp": "2026-09-08T21:00:01Z",
                "credential_slot": "reserve",
                "ok": True,
                "status": "response_received",
                "interaction_id": "reserve-1",
            },
        ]
        with (
            patch.object(status, "load_state", return_value={
                "session_status": "provider_wait",
                "stop_reason": None,
                "sleep_reason": None,
                "work_packet_id": "packet-1",
                "last_purpose": "kernel.driver_discovery",
                "updated_at": "2026-09-08T21:00:01Z",
            }),
            patch.object(status, "recent_events", return_value=events),
            patch.object(status, "public_status", return_value={
                "credential_file_present": True,
                "primary_configured": True,
                "reserve_configured": True,
            }),
            patch.object(status, "select_assignment", return_value={"identity": "kernel.driver_discovery"}),
            patch.object(status, "_service_status", return_value="RUNNING"),
        ):
            data = status.snapshot()
        self.assertEqual("QUOTA_EXHAUSTED", data["thing_1"]["provider_status"])
        self.assertEqual("AVAILABLE", data["thing_2"]["provider_status"])
        self.assertEqual("kernel.driver_discovery", data["assignment"])
        self.assertNotIn("api_key", str(data).lower())

class GeminiGoProviderHealthTest(unittest.TestCase):
    def test_supervisor_journals_primary_and_reserve_provider_attempts(self) -> None:
        from Agency.GeminiGo.supervisor import execute_with_failover
        events = []
        calls = []

        def fake(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return {
                    "ok": False,
                    "status": "provider_temporarily_unavailable",
                    "error_detail": "429 RESOURCE_EXHAUSTED",
                }
            return {
                "ok": True,
                "status": "response_received",
                "interaction_id": "reserve-health-1",
                "response_text": "continued",
            }

        with (
            patch("Agency.GeminiGo.supervisor.api_key", side_effect=lambda slot: f"{slot}-secret"),
            patch("Agency.GeminiGo.supervisor.append_event", side_effect=lambda sid, event, **fields: events.append((sid, event, fields))),
        ):
            result = execute_with_failover(
                call=fake,
                previous_interaction_id="primary-health-1",
                purpose="kernel.driver_discovery",
                context="bounded",
                system_instruction="system",
                session_id="health",
            )

        self.assertEqual("reserve", result["credential_slot"])
        self.assertEqual(["primary", "reserve"], [x[2]["credential_slot"] for x in events])
        self.assertEqual("quota", events[0][2]["failure_class"])
        self.assertTrue(events[1][2]["ok"])
        self.assertNotIn("secret", str(events).lower())

    def test_provider_failure_classes_cover_operator_health(self) -> None:
        from Agency.GeminiGo.provider import classify_failure
        self.assertEqual("quota", classify_failure({"ok": False, "error_detail": "429 RESOURCE_EXHAUSTED"}))
        self.assertEqual("auth", classify_failure({"ok": False, "error_detail": "401 API key invalid"}))
        self.assertEqual("network", classify_failure({"ok": False, "error_detail": "network connection failed"}))
        self.assertEqual("availability", classify_failure({"ok": False, "status": "provider_temporarily_unavailable", "error_detail": "503"}))
