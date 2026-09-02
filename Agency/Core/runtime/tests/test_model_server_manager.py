from __future__ import annotations

import os
import signal
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Agency.Core.runtime import model_server_manager as manager
from Agency.Core.runtime.runtime_config import ModelServerConfig


class ModelServerManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.server = self.root / "llama-server"
        self.server.write_text("#!/bin/sh\n", encoding="utf-8")
        self.server.chmod(0o755)
        self.model = self.root / "model.gguf"
        self.model.write_bytes(b"gguf")
        self.cfg = ModelServerConfig(
            server_path=self.server,
            model_path=self.model,
            host="127.0.0.1",
            port=8081,
            ctx_size=2048,
            gpu_layers=99,
            pid_path=self.root / "llama-server.pid",
            log_path=self.root / "llama-server.log",
            runtime_profiles_path=self.root / "runtime_profiles.yaml",
            profile_name="test",
            model_path_source="test",
            context_source="test",
            gpu_layers_source="test",
            server_path_source="test",
        )

    def exact_cmdline(self, pid: int) -> list[str]:
        return [
            str(self.server),
            "--model",
            str(self.model),
            "--host",
            self.cfg.host,
            "--port",
            str(self.cfg.port),
            "--ctx-size",
            str(self.cfg.ctx_size),
            "--n-gpu-layers",
            str(self.cfg.gpu_layers),
        ]

    def stale_cmdline(self, pid: int) -> list[str]:
        return [
            str(self.server),
            "--model",
            str(self.root / "old-model.gguf"),
            "--host",
            self.cfg.host,
            "--port",
            str(self.cfg.port),
            "--ctx-size",
            "1024",
            "--n-gpu-layers",
            "1",
        ]

    def test_start_prevents_duplicate_managed_process(self) -> None:
        ready = {"status": "ready", "pid": 42, "listeners": [], "configured": True}
        with patch.object(manager, "status_payload", return_value=ready),              patch.object(manager.subprocess, "Popen") as popen:
            payload, code = manager.start_server(self.cfg)

        self.assertEqual(0, code)
        self.assertEqual("already ready; duplicate start prevented", payload["reason"])
        popen.assert_not_called()
        self.assertEqual("42", self.cfg.pid_path.read_text(encoding="utf-8").strip())

    def test_status_detects_pid_file_configuration_mismatch(self) -> None:
        self.cfg.pid_path.write_text("123\n", encoding="utf-8")
        with patch.object(manager, "process_exists", return_value=True),              patch.object(manager, "cmdline", side_effect=self.stale_cmdline),              patch.object(manager, "managed_pids", return_value=[]),              patch.object(manager, "listeners", return_value=[{"address": "127.0.0.1", "port": 8081}]),              patch.object(manager, "health", return_value=(True, "healthy", {"status": "ok"})),              patch.object(manager, "_environment_payload", return_value={}):
            payload = manager.status_payload(self.cfg)

        self.assertEqual("configuration_drift", payload["status"])
        self.assertEqual(123, payload["stale_managed_pid"])
        self.assertTrue(payload["configuration_drift_detected"])
        self.assertIn("model", payload["configuration_drift"])
        self.assertIn("context", payload["configuration_drift"])
        self.assertIn("gpu_layers", payload["configuration_drift"])

    def test_stop_allows_pid_file_owned_stale_process(self) -> None:
        self.cfg.pid_path.write_text("123\n", encoding="utf-8")
        with patch.object(manager, "process_exists", return_value=True),              patch.object(manager, "cmdline", side_effect=self.stale_cmdline),              patch.object(manager, "managed_pids", return_value=[]),              patch.object(manager, "listeners", side_effect=[[{"address": "127.0.0.1", "port": 8081}], [], []]),              patch.object(manager, "health", return_value=(False, "not healthy", None)),              patch.object(manager, "wait_exit", return_value=True),              patch.object(manager.os, "kill") as kill,              patch.object(manager, "_environment_payload", return_value={}):
            payload, code = manager.stop_server(self.cfg)

        self.assertEqual(0, code)
        self.assertEqual("stopped stale managed process", payload["reason"])
        kill.assert_called_once_with(123, signal.SIGTERM)
        self.assertFalse(self.cfg.pid_path.exists())

    def test_stop_refuses_unrelated_process(self) -> None:
        self.cfg.pid_path.write_text("123\n", encoding="utf-8")
        with patch.object(manager, "process_exists", return_value=True),              patch.object(manager, "cmdline", return_value=["/bin/sleep", "999"]),              patch.object(manager, "managed_pids", return_value=[]),              patch.object(manager, "listeners", return_value=[{"address": "127.0.0.1", "port": 8081}]),              patch.object(manager, "health", return_value=(True, "healthy", {"status": "ok"})),              patch.object(manager.os, "kill") as kill,              patch.object(manager, "_environment_payload", return_value={}):
            payload, code = manager.stop_server(self.cfg)

        self.assertEqual(1, code)
        self.assertEqual("error", payload["status"])
        self.assertIn("unrelated", payload["reason"])
        kill.assert_not_called()

    def test_reconcile_reports_ready_without_spawning_duplicate(self) -> None:
        with patch.object(manager, "status_payload", return_value={"status": "ready", "pid": 42}),              patch.object(manager, "start_server") as start:
            payload, code = manager.reconcile_server(self.cfg)

        self.assertEqual(0, code)
        self.assertEqual("already reconciled", payload["reason"])
        start.assert_not_called()

    def test_start_recovers_stale_pid_file(self) -> None:
        self.cfg.pid_path.write_text("444\n", encoding="utf-8")
        fake_proc = SimpleNamespace(pid=555, poll=lambda: None, returncode=None)
        states = [
            {"status": "stopped", "listeners": [], "configured": True},
            {"status": "ready", "pid": 555, "listeners": [], "configured": True},
        ]
        with patch.object(manager, "status_payload", side_effect=states),              patch.object(manager, "process_exists", return_value=False),              patch.object(manager, "health", return_value=(True, "healthy", {"status": "ok"})),              patch.object(manager.subprocess, "Popen", return_value=fake_proc):
            payload, code = manager.start_server(self.cfg)

        self.assertEqual(0, code)
        self.assertEqual("ready", payload["reason"])
        self.assertEqual("555", self.cfg.pid_path.read_text(encoding="utf-8").strip())

    def test_restart_uses_single_stop_then_start_path(self) -> None:
        with patch.object(manager, "stop_server", return_value=({"status": "stopped"}, 0)) as stop,              patch.object(manager, "start_server", return_value=({"status": "ready"}, 0)) as start:
            payload, code = manager.restart_server(self.cfg)

        self.assertEqual(0, code)
        self.assertEqual({"status": "ready"}, payload)
        stop.assert_called_once_with(self.cfg)
        start.assert_called_once_with(self.cfg)


if __name__ == "__main__":
    unittest.main()
