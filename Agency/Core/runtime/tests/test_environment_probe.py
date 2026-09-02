from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Agency.Core.runtime import environment


class EnvironmentManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest_path = self.root / "environment_manifest.yaml"

    def command_runner(self, *, gpu: bool = True, llama: bool = True):
        def run(command: list[str], timeout: float):
            joined = " ".join(command)
            if command[0] == "nvidia-smi":
                if not gpu:
                    raise FileNotFoundError("nvidia-smi")
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "NVIDIA GeForce GTX 1050, 4096, 1000, 3096, 13.0\n",
                    "",
                )
            if command[:2] == ["pgrep", "-af"]:
                if llama and command[-1] == "llama-server":
                    return subprocess.CompletedProcess(command, 0, "123 llama-server\n", "")
                return subprocess.CompletedProcess(command, 1, "", "")
            if "command -v" in joined:
                return subprocess.CompletedProcess(command, 1, "", "")
            if "ip route" in joined:
                return subprocess.CompletedProcess(command, 0, "", "")
            return subprocess.CompletedProcess(command, 1, "", "")
        return run

    def test_linux_bootstrap_creates_manifest(self) -> None:
        manifest = environment.bootstrap_environment_manifest(
            path=self.manifest_path,
            platform_name="linux",
            run_command=self.command_runner(),
            interactive=False,
        )

        self.assertTrue(self.manifest_path.exists())
        self.assertEqual("linux", manifest.identity["machine"]["operating_system"])
        self.assertEqual("llama_server", manifest.resolved_runtime.backend)
        self.assertEqual("cuda", manifest.resolved_runtime.accelerator)
        self.assertEqual("local_gpu", manifest.resolved_runtime.execution_mode)

    def test_windows_bootstrap_normalizes_shape(self) -> None:
        manifest = environment.bootstrap_environment_manifest(
            path=self.manifest_path,
            platform_name="windows",
            run_command=self.command_runner(gpu=False, llama=False),
            interactive=False,
        )

        self.assertEqual("windows", manifest.identity["machine"]["operating_system"])
        self.assertIn("gpu", manifest.capabilities)
        self.assertIn("runtimes", manifest.capabilities)
        self.assertEqual("gguf", manifest.resolved_runtime.backend)

    def test_macos_bootstrap_normalizes_shape(self) -> None:
        manifest = environment.bootstrap_environment_manifest(
            path=self.manifest_path,
            platform_name="macos",
            run_command=self.command_runner(gpu=False, llama=False),
            interactive=False,
        )

        self.assertEqual("macos", manifest.identity["machine"]["operating_system"])
        self.assertIn("cpu", manifest.capabilities)
        self.assertEqual("local_cpu", manifest.resolved_runtime.execution_mode)

    def test_manifest_reload_does_not_prompt_or_probe_again(self) -> None:
        environment.bootstrap_environment_manifest(
            path=self.manifest_path,
            platform_name="linux",
            run_command=self.command_runner(),
            interactive=False,
        )

        def fail_input(prompt: str) -> str:
            raise AssertionError(f"unexpected prompt: {prompt}")

        def fail_run(command: list[str], timeout: float):
            raise AssertionError(f"unexpected probe: {command}")

        loaded = environment.load_or_create_environment_manifest(
            path=self.manifest_path,
            platform_name="linux",
            run_command=fail_run,
            interactive=True,
            input_func=fail_input,
        )

        self.assertEqual("llama_server", loaded.resolved_runtime.backend)

    def test_operator_completion_asks_only_for_unresolved_identity(self) -> None:
        discovered = {
            "identity": {
                "operator": {"account": None, "account_source": "unresolved", "display_name": None},
                "machine": {"hostname": "nitro", "operating_system": "linux"},
            },
            "capabilities": {"gpu": {"available": False, "cuda": False}, "runtimes": {}},
        }
        prompts: list[str] = []
        answers = iter(["spaztic", ""])

        manifest = environment.build_environment_manifest(
            discovered,
            interactive=True,
            input_func=lambda prompt: prompts.append(prompt) or next(answers),
            platform_name="linux",
        )

        self.assertEqual("spaztic", manifest.identity["operator"]["account"])
        self.assertEqual(2, len(prompts))
        self.assertFalse(any("hostname" in prompt.lower() for prompt in prompts))

    def test_runtime_selection_from_capabilities(self) -> None:
        resolved = environment.resolve_runtime_from_capabilities({
            "gpu": {"available": True, "cuda": True},
            "runtimes": {"llama_server": True},
        })

        self.assertEqual("llama_server", resolved.backend)
        self.assertEqual("cuda", resolved.accelerator)
        self.assertEqual("local", resolved.inference_route)
        self.assertEqual("local_gpu", resolved.execution_mode)

    def test_gpu_presence_alone_does_not_select_llama_server(self) -> None:
        resolved = environment.resolve_runtime_from_capabilities({
            "gpu": {"available": True, "cuda": True},
            "runtimes": {"llama_server": False},
        })

        self.assertEqual("gguf", resolved.backend)
        self.assertEqual("local_cpu", resolved.execution_mode)

    def test_ui_payload_reads_manifest(self) -> None:
        environment.bootstrap_environment_manifest(
            path=self.manifest_path,
            platform_name="linux",
            run_command=self.command_runner(),
            interactive=False,
        )

        payload = environment.environment_payload_for_ui(self.manifest_path)

        self.assertEqual("environment_identity_runtime_capability_authority", payload["authority"])
        self.assertEqual("llama_server", payload["resolved_runtime"]["backend"])


if __name__ == "__main__":
    unittest.main()