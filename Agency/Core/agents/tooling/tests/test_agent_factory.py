from __future__ import annotations

import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ca = importlib.import_module("Agency.Core.agents.tooling.create_agent")
spec_mod = importlib.import_module("Agency.Core.agents.tooling.agent_spec")
state_engine = importlib.import_module("Agency.Core.state.engine")
agent_commands = importlib.import_module("Agency.Core.interfaces.cli.commands.agent_commands")
environment = importlib.import_module("Agency.Core.runtime.environment")
mission_runtime = importlib.import_module("Agency.Core.work.missions.mission_runtime")
run_py = importlib.import_module("run")


class AgentFactoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agents_root = self.root / "Agency" / "Agents"
        self.agents_root.mkdir(parents=True)
        self.manifest_path = self.root / "environment_manifest.yaml"
        self.manifest = environment.EnvironmentManifest(
            schema_version=1,
            authority="environment_identity_runtime_capability_authority",
            created_at="2026-07-26T00:00:00Z",
            updated_at="2026-07-26T00:00:00Z",
            identity={
                "operator": {
                    "account": "spaztic",
                    "account_source": "operating_system",
                    "display_name": None,
                    "display_name_source": "operator",
                },
                "machine": {
                    "hostname": "nitro",
                    "hostname_source": "operating_system",
                    "operating_system": "linux",
                    "architecture": "x86_64",
                    "python_executable": "/home/spaztic/miniconda3/envs/dashboard_env/bin/python",
                    "python_environment": "dashboard_env",
                    "workspace": {
                        "name": "Dashboard",
                        "root": self.root.as_posix(),
                    },
                },
            },
            capabilities={
                "gpu": {
                    "available": True,
                    "vendor": "NVIDIA",
                    "model": "GeForce GTX 1050",
                    "cuda": True,
                    "vram_mib": 4096,
                },
                "cpu": {"logical_cores": 8},
                "memory": {"total_mib": 16384},
                "runtimes": {
                    "llama_server": True,
                    "ollama": False,
                    "vllm": False,
                },
                "network": {"available": True},
            },
            resolved_runtime=environment.ResolvedRuntime(
                backend="llama_server",
                accelerator="cuda",
                inference_route="local",
                execution_mode="local_gpu",
                selection_reason=["CUDA available", "llama-server detected"],
                router_runtime="llama_server",
            ),
            source={"platform_adapter": "linux"},
        )
        self.patches = [
            patch.object(ca, "AGENTS_ROOT", self.agents_root),
            patch.object(spec_mod, "AGENTS_ROOT", self.agents_root),
            patch.object(state_engine, "AGENTS_ROOT", self.agents_root),
            patch.object(agent_commands, "AGENTS_ROOT", self.agents_root),
            patch.object(ca, "load_or_create_environment_manifest", return_value=self.manifest),
            patch.object(ca, "environment_manifest_path", return_value=self.manifest_path),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def test_name_only_creation_uses_environment_manifest_and_artifacts(self) -> None:
        result = ca.create_agent("scout-agent")
        agent_dir = self.agents_root / "Scoutagent"

        self.assertEqual("created", result["status"])
        self.assertEqual("Scoutagent", result["agent"])
        expected = [
            "__init__.py",
            "README.md",
            "scoutagent.py",
            "runtime.yaml",
            "output_contract.yaml",
            "action_policy.yaml",
            "autonomy/autonomy.yaml",
            "memory/sources.yaml",
            "memory/short_term.yaml",
            "memory/Chroma/.keep",
            "state/agent_state.yaml",
            "state/transition_log.yaml",
            "state/README.md",
            "actions/proposals/.keep",
            "actions/results/.keep",
            "actions/sandbox/.keep",
        ]
        for rel in expected:
            self.assertTrue((agent_dir / rel).exists(), rel)

        runtime = (agent_dir / "runtime.yaml").read_text(encoding="utf-8")
        self.assertIn("route: Agency/Core/runtime/model_service.py", runtime)
        self.assertIn(f"runtime_authority: {self.manifest_path.as_posix()}", runtime)
        self.assertIn("backend: llama_server", runtime)
        self.assertIn("accelerator: cuda", runtime)
        self.assertIn("inference_route: local", runtime)
        self.assertIn("execution_mode: local_gpu", runtime)
        self.assertNotIn("profile:", runtime)
        self.assertNotIn("inference_target:", runtime)
        readme = (agent_dir / "README.md").read_text(encoding="utf-8")
        self.assertIn("role: agent_identity_scaffold", readme)

    def test_interactive_and_declarative_inputs_produce_same_agent_spec(self) -> None:
        parser = ca.build_parser()
        declarative = ca.spec_from_args(parser.parse_args([
            "--name", "Scout",
            "--role", "observer",
            "--description", "Inspects bounded repository surfaces",
            "--model-enabled",
            "--memory-enabled",
            "--vector-store-enabled",
            "--autonomy-enabled",
            "--capability", "read_context",
            "--capability", "summarize_context",
            "--capability", "propose_patch",
            "--capability", "prepare_handoff",
            "--capability", "interpret_guardrails",
            "--voice-disabled",
            "--non-interactive",
        ]), input_func=lambda _prompt: self.fail("declarative mode prompted unexpectedly"))

        responses = iter([
            "Scout",
            "observer",
            "Inspects bounded repository surfaces",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "y",
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            interactive = ca.collect_interactive_agent_spec(input_func=lambda _prompt: next(responses))

        self.assertEqual(declarative.to_dict(), interactive.to_dict())

    def test_validation_happens_before_writes_for_invalid_capability(self) -> None:
        spec = spec_mod.build_agent_spec(name="BadAgent", role="observer", capabilities=("teleport",))

        with self.assertRaises(spec_mod.AgentSpecValidationError) as ctx:
            ca.create_agent_from_spec(spec)

        self.assertIn("unknown capability: teleport", ctx.exception.errors)
        self.assertFalse((self.agents_root / "BadAgent").exists())

    def test_empty_normalized_name_fails_with_structured_normalization_phase(self) -> None:
        output: list[str] = []
        code = ca.main(
            ["--name", "!!!", "--role", "observer", "--non-interactive"],
            input_func=lambda _prompt: self.fail("non-interactive mode prompted unexpectedly"),
            output_func=output.append,
        )

        rendered = "\n".join(output)
        self.assertEqual(1, code)
        self.assertIn("AGENT_CREATE_FAILED", rendered)
        self.assertIn("phase: normalization", rendered)
        self.assertIn("agent_name_empty", rendered)
        self.assertEqual([], list(self.agents_root.iterdir()))

    def test_unsupported_activation_fails_deterministically(self) -> None:
        output: list[str] = []
        code = ca.main(
            ["--name", "Talker", "--role", "observer", "--voice-enabled", "--non-interactive"],
            input_func=lambda _prompt: self.fail("non-interactive mode prompted unexpectedly"),
            output_func=output.append,
        )

        self.assertEqual(1, code)
        rendered = "\n".join(output)
        self.assertIn("AGENT_CREATE_FAILED", rendered)
        self.assertIn("activation is unsupported by current platform contract: voice", rendered)
        self.assertFalse((self.agents_root / "Talker").exists())

    def test_existing_files_are_preserved_and_reported(self) -> None:
        ca.create_agent("Scout")
        readme = self.agents_root / "Scout" / "README.md"
        readme.write_text("custom readme\n", encoding="utf-8")

        result = ca.create_agent("Scout")

        self.assertEqual("custom readme\n", readme.read_text(encoding="utf-8"))
        self.assertTrue(any(path.endswith("Agency/Agents/Scout/README.md") for path in result["preserved_existing"]))

    def test_state_initialization_is_delegated_to_shared_state_engine(self) -> None:
        spec = spec_mod.build_agent_spec(name="Stateful", role="observer")
        with patch.object(ca, "init_agent_state", wraps=state_engine.init_agent_state) as init_state:
            result = ca.create_agent_from_spec(spec)

        init_state.assert_called_once_with("Stateful")
        self.assertTrue(any(path.endswith("Agency/Agents/Stateful/state/agent_state.yaml") for path in result["created"]))

    def test_generated_agent_is_discovered_by_list_agents(self) -> None:
        ca.create_agent("Scout")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = agent_commands.ListAgentsCommand(None).run(None)

        self.assertEqual(0, code)
        rendered = output.getvalue()
        self.assertIn("Scout [complete]", rendered)
        self.assertIn("runtime: True", rendered)
        self.assertIn("memory_sources: True", rendered)

    def test_non_interactive_name_option_missing_role_does_not_prompt_or_write(self) -> None:
        output: list[str] = []
        code = ca.main(
            ["--name", "NoRole", "--non-interactive"],
            input_func=lambda _prompt: self.fail("non-interactive mode prompted unexpectedly"),
            output_func=output.append,
        )

        self.assertEqual(1, code)
        rendered = "\n".join(output)
        self.assertIn("AGENT_CREATE_FAILED", rendered)
        self.assertIn("identity.role is required", rendered)
        self.assertFalse((self.agents_root / "NoRole").exists())

    def test_legacy_positional_name_only_non_interactive_uses_defaults(self) -> None:
        output: list[str] = []
        code = ca.main(
            ["Legacy", "--non-interactive", "--raw"],
            input_func=lambda _prompt: self.fail("legacy non-interactive mode prompted unexpectedly"),
            output_func=output.append,
        )

        self.assertEqual(0, code)
        result = json.loads("\n".join(output))
        self.assertEqual("Legacy", result["agent"])
        self.assertEqual("agent_identity_scaffold", result["agent_spec"]["identity"]["role"])
        self.assertEqual("llama_server", result["runtime_selection"]["backend"])
        self.assertTrue((self.agents_root / "Legacy" / "runtime.yaml").exists())

    def test_raw_result_does_not_claim_runtime_health(self) -> None:
        output: list[str] = []
        code = ca.main(
            ["--name", "Scout", "--role", "observer", "--non-interactive", "--raw"],
            output_func=output.append,
        )

        self.assertEqual(0, code)
        result = json.loads("\n".join(output))
        self.assertEqual("created", result["status"])
        self.assertIn("environment_manifest", result)
        self.assertNotIn("model_status", result)
        self.assertNotIn("runtime_health", result)
        self.assertNotIn("model_available", result)

    def test_no_secondary_agent_registry_is_created(self) -> None:
        ca.create_agent("Scout")
        agent_dir = self.agents_root / "Scout"

        registry_files = [path for path in agent_dir.rglob("*") if "registry" in path.name.lower()]
        self.assertEqual([], registry_files)

    def test_run_py_agent_create_delegates_to_factory_parser(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = run_py.run_agent_command([
                "create",
                "--name", "Bridge",
                "--role", "observer",
                "--non-interactive",
            ])

        self.assertEqual(0, code)
        self.assertIn("AGENT_CREATED", output.getvalue())
        self.assertTrue((self.agents_root / "Bridge" / "runtime.yaml").exists())

    def test_generated_agent_runtime_exposes_mission_lifecycle(self) -> None:
        result = ca.create_agent("MissionScout")
        agent_dir = self.agents_root / result["agent"]
        module_path = agent_dir / f"{ca.agent_slug(result['agent'])}.py"
        mission_root = self.root / "runtime" / "missions"
        mission_root.mkdir(parents=True)

        spec = importlib.util.spec_from_file_location(
            "missionscout_generated_runtime_test",
            module_path,
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)

        output = io.StringIO()
        inspect_output = io.StringIO()
        plan_output = io.StringIO()
        with patch.object(mission_runtime, "MISSIONS_ROOT", mission_root):
            with patch.object(
                mission_runtime,
                "agency_blocks_dependent_operations",
                return_value=[],
            ):
                with contextlib.redirect_stdout(output):
                    code = module.main([
                        "mission",
                        "create",
                        "--intent",
                        "Generated mission lifecycle",
                        "--scope",
                        "UI/Main",
                    ])
                with contextlib.redirect_stdout(inspect_output):
                    inspect_code = module.main([
                        "mission",
                        "inspect",
                        "--mission",
                        "1",
                    ])
                with contextlib.redirect_stdout(plan_output):
                    plan_code = module.main([
                        "mission",
                        "plan",
                        "--mission",
                        "1",
                    ])

        payload = json.loads(output.getvalue())
        inspect_payload = json.loads(inspect_output.getvalue())
        plan_payload = json.loads(plan_output.getvalue())
        self.assertEqual(0, code)
        self.assertEqual("mission_created", payload["status"])
        self.assertEqual(0, inspect_code)
        self.assertIn(plan_code, {0, 1})
        self.assertEqual("mission-1", inspect_payload["mission_id"])
        self.assertEqual("mission-1", plan_payload["mission_id"])
        self.assertTrue((mission_root / "mission-1" / "intent.json").exists())
        self.assertTrue((mission_root / "mission-1" / "inspect" / "pass_001.json").exists())

    def test_auto_runtime_uses_manifest_recommendation(self) -> None:
        output: list[str] = []
        code = ca.main(
            [
                "--name", "AutoRuntime",
                "--role", "observer",
                "--auto-runtime",
                "--non-interactive",
                "--raw",
            ],
            output_func=output.append,
        )

        self.assertEqual(0, code)
        result = json.loads("\n".join(output))
        runtime = (self.agents_root / "AutoRuntime" / "runtime.yaml").read_text(encoding="utf-8")
        self.assertEqual("llama_server", result["runtime_selection"]["backend"])
        self.assertEqual("cuda", result["runtime_selection"]["accelerator"])
        self.assertEqual("local", result["runtime_selection"]["inference_route"])
        self.assertEqual("local_gpu", result["runtime_selection"]["execution_mode"])
        self.assertEqual("environment_manifest", result["agent_spec"]["runtime"]["selection_mode"])
        self.assertIn("backend: llama_server", runtime)
        self.assertIn("accelerator: cuda", runtime)
        self.assertIn("inference_route: local", runtime)
        self.assertIn("execution_mode: local_gpu", runtime)
        self.assertIn("detected: true", runtime)

    def test_generated_runtime_preserves_environment_distinctions(self) -> None:
        spec = spec_mod.build_agent_spec(name="SplitRuntime", role="observer")

        result = ca.create_agent_from_spec(spec)
        runtime = (self.agents_root / "SplitRuntime" / "runtime.yaml").read_text(encoding="utf-8")

        self.assertEqual("llama_server", result["runtime_selection"]["backend"])
        self.assertEqual("cuda", result["runtime_selection"]["accelerator"])
        self.assertIn("RuntimeIdentity:", runtime)
        self.assertIn("backend: llama_server", runtime)
        self.assertIn("accelerator: cuda", runtime)
        self.assertIn("inference_route: local", runtime)
        self.assertIn("execution_mode: local_gpu", runtime)

    def test_environment_runtime_preserves_existing_files(self) -> None:
        ca.create_agent("Stable")
        runtime_path = self.agents_root / "Stable" / "runtime.yaml"
        runtime_path.write_text("custom runtime\n", encoding="utf-8")
        spec = spec_mod.build_agent_spec(name="Stable", role="observer")

        result = ca.create_agent_from_spec(spec)

        self.assertEqual("custom runtime\n", runtime_path.read_text(encoding="utf-8"))
        self.assertTrue(any(path.endswith("Agency/Agents/Stable/runtime.yaml") for path in result["preserved_existing"]))

    def test_generated_next_commands_use_lowercase_run_py(self) -> None:
        result = ca.create_agent("CommandScout")

        self.assertTrue(result["next_commands"])
        self.assertTrue(all(command.startswith("python run.py ") for command in result["next_commands"]))
        self.assertFalse(any("Run.py" in command for command in result["next_commands"]))

    def test_agent_creation_is_deterministic_with_mocked_manifest(self) -> None:
        first = ca.create_agent_from_spec(spec_mod.build_agent_spec(name="AutoOne", role="observer"))
        second = ca.create_agent_from_spec(spec_mod.build_agent_spec(name="AutoTwo", role="observer"))

        self.assertEqual(first["runtime_selection"], second["runtime_selection"])
        first_runtime = (self.agents_root / "AutoOne" / "runtime.yaml").read_text(encoding="utf-8")
        second_runtime = (self.agents_root / "AutoTwo" / "runtime.yaml").read_text(encoding="utf-8")
        for expected in (
            "backend: llama_server",
            "accelerator: cuda",
            "inference_route: local",
            "execution_mode: local_gpu",
        ):
            self.assertIn(expected, first_runtime)
            self.assertIn(expected, second_runtime)

    def test_cli_help_lists_factory_defaults(self) -> None:
        output = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, contextlib.redirect_stdout(output):
            ca.build_parser().parse_args(["--help"])

        self.assertEqual(0, ctx.exception.code)
        help_text = output.getvalue()
        self.assertIn("role=agent_identity_scaffold", help_text)
        self.assertIn("runtime=environment_manifest", help_text)
        self.assertIn("voice=false", help_text)


class AgentPackageLauncherContractTests(unittest.TestCase):
    def test_render_agent_init_exports_callable_entrypoint(self) -> None:
        spec = type("Spec", (), {"agent_name": "TestAgent"})()

        rendered = ca.render_agent_init(spec)

        self.assertIn("from .testagent import main", rendered)
        self.assertIn('__all__ = ["main"]', rendered)

if __name__ == "__main__":
    unittest.main()