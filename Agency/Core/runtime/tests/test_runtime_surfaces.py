from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.runtime import agent_shell

DASHBOARD_ROOT = Path(__file__).resolve().parents[4]


class RuntimeSurfaceTests(unittest.TestCase):
    def test_agent_shell_prompt_uses_shared_ask_agent(self) -> None:
        payload = {
            "ok": True,
            "draft": "OK",
            "response_provenance": "model_inference",
        }
        output = io.StringIO()
        with patch("Agency.Core.runtime.model_service.ask_agent", return_value=payload) as ask,              contextlib.redirect_stdout(output):
            code = agent_shell.main("Editor", ["Reply with exactly: OK"])

        self.assertEqual(0, code)
        self.assertIn("[Inference]", output.getvalue())
        ask.assert_called_once()
        self.assertEqual("Editor", ask.call_args.args[0])
        self.assertIn("Reply with exactly: OK", ask.call_args.args[1])

    def test_inline_tool_help_uses_dispatchable_command_surface(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            raw, keep_running, code = agent_shell._handle_command("/tools", raw=False)

        text = output.getvalue()
        self.assertFalse(raw)
        self.assertTrue(keep_running)
        self.assertEqual(0, code)
        self.assertIn("git-status", text)
        self.assertNotIn("COMMAND_REGISTRY", text)

    def test_top_level_help_lists_current_model_and_agent_surfaces(self) -> None:
        proc = subprocess.run(
            [sys.executable, "run.py", "-h"],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("agent", proc.stdout)
        self.assertIn("model", proc.stdout)

    def test_agent_help_documents_current_invocation_form(self) -> None:
        proc = subprocess.run(
            [sys.executable, "run.py", "agent", "-h"],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn('ask <AgentName> "prompt"', proc.stdout)
        self.assertNotIn("Run.py", proc.stdout)

    def test_model_help_forwards_to_model_service_commands(self) -> None:
        proc = subprocess.run(
            [sys.executable, "run.py", "model", "-h"],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("status", proc.stdout)
        self.assertIn("ask", proc.stdout)
        self.assertIn("agent-ask", proc.stdout)
        self.assertNotIn("positional arguments:\n  args", proc.stdout)

    def test_model_manager_help_includes_reconcile(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "Agency.Core.runtime.model_server_manager",
                "-h",
            ],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("reconcile", proc.stdout)

    def test_agent_shell_prompt_returns_nonzero_when_agent_payload_fails(self) -> None:
        payload = {
            "ok": False,
            "status": "named_file_not_found",
            "reason": "One or more explicitly named files could not be resolved.",
        }
        output = io.StringIO()
        with (
            patch("Agency.Core.runtime.model_service.ask_agent", return_value=payload),
            contextlib.redirect_stdout(output),
        ):
            code = agent_shell.main("Editor", ["Review Missing/Nope.py"])

        self.assertEqual(1, code)
        self.assertIn("Editor unavailable", output.getvalue())

    def test_ask_agent_rejects_missing_filesystem_agent_before_inference(self) -> None:
        from Agency.Core.runtime import model_service

        payload = model_service.ask_agent("MissingAgent", "Reply with exactly: NOPE")

        self.assertFalse(payload["ok"])
        self.assertEqual("agent_not_available", payload["status"])
        self.assertFalse(payload["model_inference_used"])
        self.assertIn("Editor", payload["available_agents"])

    def test_run_py_agent_ask_returns_nonzero_when_payload_not_ok(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "run.py",
                "agent",
                "ask",
                "Editor",
                "Review Missing/Nope.py",
            ],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(1, proc.returncode)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual("named_file_not_found", payload["status"])

    def test_run_py_agent_ask_rejects_missing_filesystem_agent(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "run.py",
                "agent",
                "ask",
                "MissingAgent",
                "Reply with exactly: NOPE",
            ],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(1, proc.returncode)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual("agent_not_available", payload["status"])
        self.assertFalse(payload["model_inference_used"])

    def test_run_py_model_agent_ask_rejects_missing_filesystem_agent(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "run.py",
                "model",
                "agent-ask",
                "MissingAgent",
                "Reply with exactly: NOPE",
            ],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(1, proc.returncode)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual("agent_not_available", payload["status"])
        self.assertFalse(payload["model_inference_used"])

    def test_run_py_model_agent_ask_returns_nonzero_when_payload_not_ok(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "run.py",
                "model",
                "agent-ask",
                "Editor",
                "Review Missing/Nope.py",
            ],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(1, proc.returncode)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual("named_file_not_found", payload["status"])

    def test_task_inspect_help_uses_current_task_route(self) -> None:
        proc = subprocess.run(
            [sys.executable, "run.py", "task", "inspect", "-h"],
            cwd=DASHBOARD_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("usage: python run.py task inspect", proc.stdout)
        self.assertNotIn("python run.py editor", proc.stdout)


if __name__ == "__main__":
    unittest.main()
