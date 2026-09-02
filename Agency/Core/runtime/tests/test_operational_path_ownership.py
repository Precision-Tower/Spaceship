from __future__ import annotations

import unittest
from pathlib import Path

from Agency.Core import paths
from Agency.Core.work.work_packets import execution as work_execution
from Agency.Core.runtime import environment, runtime_config
from Agency.Core.state import event_log, replay, transitions


class OperationalPathOwnershipTests(unittest.TestCase):
    def assert_under_agents(self, path: Path) -> None:
        rel = path.resolve().relative_to(paths.DASHBOARD_ROOT.resolve()).as_posix()
        self.assertTrue(rel.startswith("Agency/Agents/"), rel)

    def test_default_generated_roots_are_agent_owned(self) -> None:
        generated_roots = [
            paths.STATE_ROOT,
            paths.WORK_ROOT,
            paths.MISSIONS_ROOT,
            paths.PINBOARD_ROOT,
            paths.PROPOSALS_ROOT,
            paths.WORK_PACKETS_ROOT,
            paths.EDITOR_TASKS_ROOT,
            paths.INSPECTIONS_ROOT,
            paths.ENVIRONMENT_MANIFEST_PATH,
            paths.MODEL_SERVER_PID_PATH,
            paths.MODEL_SERVER_LOG_PATH,
            paths.WATCH_LOG,
        ]
        for generated_path in generated_roots:
            with self.subTest(path=generated_path):
                self.assert_under_agents(generated_path)

    def test_runtime_config_uses_agent_owned_pid_and_log_defaults(self) -> None:
        config = runtime_config.load_model_server_config()
        self.assertEqual(paths.MODEL_SERVER_PID_PATH, config.pid_path)
        self.assertEqual(paths.MODEL_SERVER_LOG_PATH, config.log_path)

    def test_environment_manifest_default_is_agent_owned(self) -> None:
        self.assertEqual(paths.ENVIRONMENT_MANIFEST_PATH, environment.environment_manifest_path())

    def test_work_packet_authorization_reference_is_agent_owned(self) -> None:
        rel = work_execution._authorization_path("wp-1", "auth-1")
        self.assertEqual(
            "Agency/Agents/Editor/work/WorkPackets/wp-1/authorizations/auth-1.json",
            rel,
        )

    def test_agent_state_helpers_use_agent_directory(self) -> None:
        self.assertEqual(
            paths.AGENTS_ROOT / "Editor" / "state" / "transition_log.yaml",
            event_log.agent_log_path("Editor"),
        )
        self.assertEqual(
            paths.AGENTS_ROOT / "Editor" / "state" / "agent_state.yaml",
            transitions.agent_state_path("Editor"),
        )
        self.assertEqual(
            paths.AGENTS_ROOT / "Editor" / "state" / "agent_state.yaml",
            replay.agent_paths("Editor")["state"],
        )


if __name__ == "__main__":
    unittest.main()
