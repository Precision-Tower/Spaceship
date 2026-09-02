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
environment = importlib.import_module("Agency.Core.runtime.environment")
model_service = importlib.import_module("Agency.Core.runtime.model_service")
agent_shell = importlib.import_module("Agency.Core.runtime.agent_shell")
authoritative = importlib.import_module("Agency.Core.runtime.authoritative_state")


class GeneratedAgentAuthoritativeStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agency_root = self.root / "Agency"
        self.agents_root = self.agency_root / "Agents"
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
                    "python_executable": "/home/spaztic/miniconda3/envs/weebo_env/bin/python",
                    "python_environment": "weebo_env",
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
        environment.save_environment_manifest(self.manifest, self.manifest_path)
        self.patches = [
            patch.object(ca, "AGENTS_ROOT", self.agents_root),
            patch.object(spec_mod, "AGENTS_ROOT", self.agents_root),
            patch.object(state_engine, "AGENTS_ROOT", self.agents_root),
            patch.object(ca, "load_or_create_environment_manifest", return_value=self.manifest),
            patch.object(ca, "environment_manifest_path", return_value=self.manifest_path),
            patch.object(model_service, "AGENT_ROOT", self.agents_root),
            patch.object(agent_shell, "AGENCY_ROOT", self.agency_root),
            patch.object(authoritative, "AGENCY_ROOT", self.agency_root),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

        spec = spec_mod.build_agent_spec(
            name="StateScout",
            role="continuity_and_codebase_observation_agent",
            description="Authoritative state regression agent.",
        )
        ca.create_agent_from_spec(spec)

    def ask(self, prompt: str) -> dict:
        payload = model_service.ask_agent("StateScout", prompt)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual("authoritative_state", payload["context_route"])
        self.assertEqual(0, payload["memory_results_loaded"])
        self.assertTrue(payload["memory_retrieval_skipped"])
        return payload

    def test_generated_module_exposes_authoritative_state_api(self) -> None:
        module_path = self.agents_root / "StateScout" / "statescout.py"
        spec = importlib.util.spec_from_file_location(
            "statescout_authoritative_state_test",
            module_path,
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)

        state = module.authoritative_state()

        self.assertTrue(state.available)
        self.assertEqual("StateScout", state.identity["name"])
        self.assertEqual("llama_server", state.runtime["backend"])
        self.assertEqual("local_gpu", state.runtime["execution_mode"])
        self.assertTrue(state.memory["vector_store_enabled"])

    def test_generated_agent_status_uses_authoritative_state(self) -> None:
        module_path = self.agents_root / "StateScout" / "statescout.py"
        spec = importlib.util.spec_from_file_location(
            "statescout_status_authoritative_state_test",
            module_path,
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = module.main(["/status"])
        text = output.getvalue()

        self.assertEqual(0, code)
        self.assertIn("StateScout status", text)
        self.assertIn("Identity", text)
        self.assertIn("name: StateScout", text)
        self.assertIn("role: continuity_and_codebase_observation_agent", text)
        self.assertIn("Runtime", text)
        self.assertIn("backend: llama_server", text)
        self.assertIn("execution_mode: local_gpu", text)
        self.assertIn("Authority", text)
        self.assertIn("runtime: EnvironmentManifest", text)
        self.assertIn("Mission", text)
        self.assertIn("active: none", text)
        for name in ("runtime", "output_contract", "action_policy", "autonomy"):
            self.assertIn(f"  {name}", text)
        self.assertIn("Memory", text)
        self.assertIn("vector_store: enabled", text)
        self.assertIn("memory/Chroma", text)
        self.assertNotIn("status: scaffold", text)
        self.assertNotIn("local_agent_memory_only_not_validation", text)

    def test_authoritative_response_provenance_is_displayed_by_shell(self) -> None:
        module_path = self.agents_root / "StateScout" / "statescout.py"
        spec = importlib.util.spec_from_file_location(
            "statescout_provenance_authoritative_state_test",
            module_path,
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = module.main(["Describe your runtime authority."])
        text = output.getvalue()

        self.assertEqual(0, code)
        self.assertIn("[Authoritative State]", text)
        self.assertNotIn("[Inference]", text)
        self.assertIn("EnvironmentManifest", text)

    def test_who_are_you_uses_generated_identity(self) -> None:
        payload = self.ask("Who are you?")

        self.assertEqual("identity", payload["authoritative_state_topic"])
        self.assertIn("StateScout", payload["draft"])
        self.assertIn("continuity_and_codebase_observation_agent", payload["draft"])
        self.assertNotIn("I am autonomous", payload["draft"])

    def test_runtime_authority_uses_environment_manifest(self) -> None:
        prompts = [
            "Describe your runtime authority.",
            "Where do your runtime decisions come from?",
            "Who owns your runtime?",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                payload = self.ask(prompt)
                draft = payload["draft"]

                self.assertEqual("runtime_authority", payload["authoritative_state_topic"])
                self.assertIn("EnvironmentManifest", draft)
                self.assertIn("I do not own runtime selection", draft)
                self.assertIn("shared runtime", draft)
                self.assertNotIn("memory", draft.lower())
                self.assertNotIn("I am autonomous", draft)

    def test_runtime_identity_answers_backend_and_execution_mode(self) -> None:
        backend = self.ask("What backend are you using?")
        execution_mode = self.ask("What execution mode are you using?")
        runtime = self.ask("Describe your runtime.")

        self.assertEqual("runtime", backend["authoritative_state_topic"])
        self.assertIn("Backend: llama_server", backend["draft"])
        self.assertIn("Execution mode: local_gpu", execution_mode["draft"])
        self.assertIn("Backend: llama_server", runtime["draft"])
        self.assertEqual("llama_server", backend["runtime_identity"]["backend"])
        self.assertEqual("local_gpu", execution_mode["runtime_identity"]["execution_mode"])

    def test_active_mission_and_loaded_policies_are_structured_state(self) -> None:
        mission = self.ask("What mission is active?")
        policies = self.ask("What policies are loaded?")

        self.assertEqual("active_mission", mission["authoritative_state_topic"])
        self.assertEqual("No active mission.", mission["draft"])
        self.assertEqual("loaded_policies", policies["authoritative_state_topic"])
        for name in ("runtime", "output_contract", "action_policy", "autonomy"):
            self.assertIn(name, policies["draft"])

    def test_environment_question_uses_environment_manifest(self) -> None:
        payload = self.ask("What environment are you running in?")

        self.assertEqual("environment", payload["authoritative_state_topic"])
        self.assertIn("Operator account: spaztic", payload["draft"])
        self.assertIn("Machine: nitro", payload["draft"])
        self.assertIn("Python environment: weebo_env", payload["draft"])

    def test_repository_runtime_questions_do_not_use_authoritative_route(self) -> None:
        self.assertIsNone(
            authoritative.classify_authoritative_state_request(
                "Explain Agency/Core/runtime"
            )
        )
        self.assertIsNone(
            authoritative.classify_authoritative_state_request(
                "Where is EnvironmentManifest defined?"
            )
        )


    def test_rewrite_text_with_environment_terms_is_not_authoritative(self) -> None:
        prompt = (
            "Rewrite this sentence for clarity: The runtime maybe should probably "
            "load the model based on the environment."
        )
        self.assertIsNone(authoritative.classify_authoritative_state_request(prompt))

        routed_payload = {
            "authority": "remote_model_draft_not_truth",
            "runtime": "llama_server",
            "backend": "llama_server",
            "ok": True,
            "status": "completed",
            "draft": "The runtime should load the model based on the environment.",
            "finish_reason": "stop",
            "completion_status": "completed",
        }
        with patch("Agency.Core.runtime.runtime_router.ask", return_value=routed_payload) as routed, \
             patch.object(model_service, "compose_agent_system_context", wraps=model_service.compose_agent_system_context) as composed:
            payload = model_service.ask_agent("StateScout", prompt)

        self.assertEqual({}, composed.call_args.kwargs["output_contract"])
        self.assertEqual("model_inference", payload["response_provenance"])
        self.assertEqual("rewrite", payload["context_route"])
        self.assertEqual("rewrite", payload["inference_policy"]["route"])
        self.assertFalse(payload["thinking_enabled"])
        routed.assert_called_once()

    def test_machine_and_selected_model_runtime_questions_use_authoritative_state(self) -> None:
        machine = self.ask("What machine is hosting Dashboard?")
        runtime = self.ask("What model runtime is currently selected?")

        self.assertEqual("environment", machine["authoritative_state_topic"])
        self.assertIn("Machine: nitro", machine["draft"])
        self.assertEqual("runtime", runtime["authoritative_state_topic"])
        self.assertIn("Backend: llama_server", runtime["draft"])

    def test_unavailable_state_returns_fixed_failure_message(self) -> None:
        missing = authoritative.authoritative_state("MissingAgent", agents_root=self.agents_root)
        answer = authoritative.answer_authoritative_state_question(
            missing,
            "runtime_authority",
        )

        self.assertFalse(missing.available)
        self.assertEqual(authoritative.UNAVAILABLE_MESSAGE, answer)


if __name__ == "__main__":
    unittest.main()
