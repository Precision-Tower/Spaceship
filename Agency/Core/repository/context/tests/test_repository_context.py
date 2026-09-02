from __future__ import annotations

import contextlib
import hashlib
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
from Agency.Core.repository.context import builder
from Agency.Core.runtime import agent_shell
from Agency.Core.runtime import environment
from Agency.Core.runtime import model_service


class RepositoryContextBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.work = self.repo / "Agency" / "Agents" / "Editor" / "work" / "Inspections"
        self.core = self.repo / "Agency" / "Core"
        self.runtime = self.core / "runtime"
        self.runtime.mkdir(parents=True)
        self.agent_root = self.repo / "Agency" / "Agents"
        self.agent_dir = self.agent_root / "Scout"
        self.agent_dir.mkdir(parents=True)
        (self.agent_dir / "runtime.yaml").write_text(
            """AgentRuntime:
  owner: Scout
  identity:
    role: observer
    description: null
  RuntimeIdentity:
    runtime:
      backend: llama_server
      accelerator: cuda
      inference_route: local
      execution_mode: local_gpu
  model:
    backend: llama_server
    accelerator: cuda
    inference_route: local
    execution_mode: local_gpu
""",
            encoding="utf-8",
        )
        (self.runtime / "sample.py").write_text(
            """import os
from Agency.Core.runtime.environment import EnvironmentManifest

VALUE = 1

class Sample:
    def method(self):
        return authoritative_state()

async def async_worker():
    return VALUE

def authoritative_state():
    return EnvironmentManifest

def caller():
    return authoritative_state()
""",
            encoding="utf-8",
        )
        (self.runtime / "bad.py").write_text("def broken(:\n", encoding="utf-8")
        (self.runtime / "notes.txt").write_text("legacy_profiles is mentioned here\n", encoding="utf-8")
        (self.runtime / "binary.bin").write_bytes(b"\x00\x01\x02")
        (self.runtime / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
        self.patches = [
            patch.object(builder, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "AGENCY_ROOT", self.repo / "Agency"),
            patch.object(builder, "WORK_INSPECTIONS_ROOT", self.work),
            patch.object(model_service, "AGENT_ROOT", self.agent_root),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def request(self, **kwargs):
        values = {
            "request_id": "test-request",
            "objective": "test inspection",
            "include": ["Agency/Core/runtime"],
            "operations": ["path_discovery", "text_search", "symbol_definition", "imports", "references", "dependency_trace"],
            "symbols": ["authoritative_state", "Sample", "async_worker"],
            "text": ["legacy_profiles"],
            "paths": ["sample.py"],
            "limits": dict(builder.DEFAULT_LIMITS),
        }
        values.update(kwargs)
        return builder.RepositoryContextRequest(**values)

    def test_known_text_and_symbols_are_found_with_lines(self) -> None:
        bundle = builder.build_repository_context(self.request(), persist=False)

        self.assertEqual("completed", bundle.status)
        self.assertTrue(any(item["symbol"] == "authoritative_state" for item in bundle.symbols))
        self.assertTrue(any(item["definition_kind"] == "class" for item in bundle.symbols))
        self.assertTrue(any(item["definition_kind"] == "async_function" for item in bundle.symbols))
        self.assertTrue(any("legacy_profiles" in item["evidence"][0]["excerpt"] for item in bundle.findings))
        for item in bundle.findings:
            evidence = item["evidence"][0]
            self.assertFalse(Path(evidence["path"]).is_absolute())
            self.assertGreaterEqual(evidence["start_line"], 1)
            self.assertIn(item["classification"], {"confirmed", "strongly_inferred", "weakly_inferred", "unresolved", "not_found_within_scope"})

    def test_imports_and_call_references_are_classified(self) -> None:
        bundle = builder.build_repository_context(self.request(), persist=False)

        self.assertTrue(any(item["module"] == "os" or item["module"] == "Agency.Core.runtime.environment" for item in bundle.imports))
        self.assertTrue(any(item["reference_type"] == "possible_call_site" for item in bundle.references))
        self.assertTrue(any(item["relationship_type"] == "calls_directly" for item in bundle.dependency_edges))
        self.assertTrue(all(item.get("depth", 1) <= 2 for item in bundle.dependency_edges))

    def test_negative_symbol_reports_not_found_within_scope(self) -> None:
        req = self.request(symbols=["definitely_not_a_real_runtime_symbol_7f91"], text=[], operations=["symbol_definition"])
        bundle = builder.build_repository_context(req, persist=False)

        self.assertEqual("completed", bundle.status)
        self.assertEqual([], bundle.symbols)
        self.assertEqual("not_found_within_scope", bundle.negative_results[0]["result"])
        self.assertIn("Agency/Core/runtime", bundle.negative_results[0]["searched_scope"])

    def test_scope_safety_and_skips(self) -> None:
        rejected = builder.build_repository_context(self.request(include=["../outside"]), persist=False)
        self.assertEqual("rejected", rejected.status)
        rejected_abs = builder.build_repository_context(self.request(include=["/etc"]), persist=False)
        self.assertEqual("rejected", rejected_abs.status)
        bundle = builder.build_repository_context(self.request(), persist=False)
        reasons = {item["reason"] for item in bundle.files_skipped}
        self.assertIn("sensitive_path_excluded", reasons)
        self.assertIn("binary_file_skipped", reasons)

    def test_symlink_escape_is_rejected(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        link = self.runtime / "escape.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("symlink not supported")
        bundle = builder.build_repository_context(self.request(), persist=False)
        self.assertTrue(any(item["reason"] == "symlink_escape_rejected" for item in bundle.files_skipped))

    def test_repository_files_remain_unchanged_and_code_is_not_executed(self) -> None:
        source = self.runtime / "sample.py"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        bundle = builder.build_repository_context(self.request(), persist=False)
        after = hashlib.sha256(source.read_bytes()).hexdigest()

        self.assertEqual(before, after)
        self.assertFalse(bundle.repository_mutation_performed)
        self.assertTrue(any(item["path"].endswith("bad.py") for item in bundle.parse_failures))

    def test_limits_produce_partial_status(self) -> None:
        req = self.request(limits={**builder.DEFAULT_LIMITS, "max_files": 1})
        bundle = builder.build_repository_context(req, persist=False)
        self.assertEqual("partial", bundle.status)
        self.assertTrue(bundle.limits["reached"]["max_files"])

    def test_persistence_round_trip(self) -> None:
        bundle = builder.build_repository_context(self.request(request_id="persisted"), persist=True)
        loaded = builder.load_evidence_bundle("persisted")

        self.assertEqual(bundle.request_id, loaded.request_id)
        self.assertTrue((self.work / "persisted" / "request.yaml").exists())
        self.assertTrue((self.work / "persisted" / "evidence.yaml").exists())
        self.assertTrue((self.work / "persisted" / "metadata.yaml").exists())


class RepositoryContextRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.runtime = self.repo / "Agency" / "Core" / "runtime"
        self.runtime.mkdir(parents=True)
        (self.runtime / "state.py").write_text(
            """def authoritative_state():
    return 'state'
""",
            encoding="utf-8",
        )
        self.agents = self.repo / "Agency" / "Agents"
        agent = self.agents / "Scout"
        agent.mkdir(parents=True)
        (agent / "runtime.yaml").write_text(
            """AgentRuntime:
  owner: Scout
  identity:
    role: observer
    description: null
  RuntimeIdentity:
    runtime:
      backend: llama_server
      accelerator: cuda
      inference_route: local
      execution_mode: local_gpu
  model:
    backend: llama_server
    accelerator: cuda
    inference_route: local
    execution_mode: local_gpu
""",
            encoding="utf-8",
        )
        self.patches = [
            patch.object(builder, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "AGENCY_ROOT", self.repo / "Agency"),
            patch.object(builder, "WORK_INSPECTIONS_ROOT", self.repo / "Agency" / "Agents" / "Editor" / "work" / "Inspections"),
            patch.object(model_service, "AGENT_ROOT", self.agents),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_authoritative_questions_still_route_to_authoritative_state(self) -> None:
        payload = model_service.ask_agent("Scout", "What backend are you using?")
        self.assertEqual("authoritative_state", payload["context_route"])

    def test_repository_questions_route_to_repository_inspection(self) -> None:
        payload = model_service.ask_agent("Scout", "Inspect Agency/Core/runtime")
        self.assertEqual("repository_inspection", payload["context_route"])
        self.assertEqual("repository_evidence", payload["response_provenance"])
        self.assertTrue(payload["repository_evidence_loaded"])
        self.assertEqual(0, payload["memory_results_loaded"])

    def test_trace_runtime_dependencies_does_not_route_to_authoritative_state(self) -> None:
        payload = model_service.ask_agent("Scout", "Trace environment runtime dependencies in Agency/Core/runtime")
        self.assertEqual("repository_inspection", payload["context_route"])
        self.assertNotEqual("authoritative_state", payload["context_route"])

    def test_structured_request_takes_precedence(self) -> None:
        prompt = """RepositoryContextRequest:
  objective: What backend are you using, but inspect source
  scope:
    include:
      - Agency/Core/runtime
  operations:
    - symbol_definition
  query:
    symbols:
      - authoritative_state
"""
        payload = model_service.ask_agent("Scout", prompt)
        self.assertEqual("repository_inspection", payload["context_route"])
        self.assertTrue(payload["evidence_bundle"]["symbols"])

    def test_ordinary_prompt_is_not_repository_request(self) -> None:
        self.assertIsNone(builder.parse_repository_context_request("Tell me a short joke."))


class GeneratedAgentRepositoryContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.agency_root = self.repo / "Agency"
        self.agents_root = self.agency_root / "Agents"
        self.agents_root.mkdir(parents=True)
        runtime = self.agency_root / "Core" / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "state.py").write_text(
            """def authoritative_state():
    return 'state'
""",
            encoding="utf-8",
        )
        self.manifest_path = self.repo / "environment_manifest.yaml"
        self.manifest = environment.EnvironmentManifest(
            schema_version=1,
            authority="environment_identity_runtime_capability_authority",
            created_at="2026-07-26T00:00:00Z",
            updated_at="2026-07-26T00:00:00Z",
            identity={
                "operator": {"account": "tester", "account_source": "test"},
                "machine": {
                    "hostname": "test-host",
                    "hostname_source": "test",
                    "operating_system": "linux",
                    "architecture": "x86_64",
                    "python_executable": "python",
                    "python_environment": "test",
                    "workspace": {"name": "repo", "root": self.repo.as_posix()},
                },
            },
            capabilities={
                "gpu": {"available": False, "cuda": False},
                "cpu": {"logical_cores": 2},
                "memory": {"total_mib": 2048},
                "runtimes": {"llama_server": True, "ollama": False, "vllm": False},
                "network": {"available": False},
            },
            resolved_runtime=environment.ResolvedRuntime(
                backend="llama_server",
                accelerator="cpu",
                inference_route="local",
                execution_mode="local_cpu",
                selection_reason=["test runtime"],
                router_runtime="llama_server",
            ),
            source={"platform_adapter": "test"},
        )
        self.patches = [
            patch.object(ca, "AGENTS_ROOT", self.agents_root),
            patch.object(spec_mod, "AGENTS_ROOT", self.agents_root),
            patch.object(state_engine, "AGENTS_ROOT", self.agents_root),
            patch.object(ca, "load_or_create_environment_manifest", return_value=self.manifest),
            patch.object(ca, "environment_manifest_path", return_value=self.manifest_path),
            patch.object(builder, "DASHBOARD_ROOT", self.repo),
            patch.object(builder, "AGENCY_ROOT", self.agency_root),
            patch.object(builder, "WORK_INSPECTIONS_ROOT", self.agency_root / "Agents" / "Editor" / "work" / "Inspections"),
            patch.object(model_service, "AGENT_ROOT", self.agents_root),
            patch.object(agent_shell, "AGENCY_ROOT", self.agency_root),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_generated_agent_inherits_repository_inspection(self) -> None:
        spec = spec_mod.build_agent_spec(name="RepoScout", role="observer")
        ca.create_agent_from_spec(spec)
        module_path = self.agents_root / "RepoScout" / "reposcout.py"
        spec_obj = importlib.util.spec_from_file_location("reposcout_repository_context_test", module_path)
        module = importlib.util.module_from_spec(spec_obj)
        self.assertIsNotNone(spec_obj.loader)
        spec_obj.loader.exec_module(module)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = module.main(["Find the definition of authoritative_state in Agency/Core/runtime."])
        text = output.getvalue()

        self.assertEqual(0, code)
        self.assertIn("[Repository Evidence]", text)
        self.assertIn("Repository inspection: completed", text)
        self.assertIn("authoritative_state at Agency/Core/runtime/state.py", text)


if __name__ == "__main__":
    unittest.main()

