from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from Agency.Core.work.missions import mission_runtime
from Agency.Core.runtime import model_server_manager, model_service
from Agency.Core.runtime.runtime_config import RUNTIME_PROFILES_ENV, load_model_server_config


class RuntimeConfigTest(unittest.TestCase):
    def write_profile(self, root: Path, *, context_tokens: int, gpu_layers: int = 99) -> Path:
        model_path = root / "configured-model.gguf"
        model_path.write_bytes(b"gguf-test-placeholder")
        profile_path = root / "runtime_profiles.yaml"
        profile_path.write_text(
            f"""RuntimeProfiles:
  active_profile: test
  profiles:
    test:
      model_execution:
        preferred_backend: gguf
        recommended_context_tokens: 2048
        reasoning_max_tokens: 321
      model_server:
        server_path: /bin/true
        model_path: {model_path.as_posix()}
        host: 127.0.0.1
        port: 6551
        context_tokens: {context_tokens}
        gpu_layers: {gpu_layers}
      paths:
        qwen_1_5b_gguf: {model_path.as_posix()}
""",
            encoding="utf-8",
        )
        return profile_path

    def test_model_server_config_comes_from_runtime_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = self.write_profile(Path(tmp), context_tokens=3072, gpu_layers=17)
            cfg = load_model_server_config(profile_path)

            self.assertEqual(Path("/bin/true"), cfg.server_path)
            self.assertEqual(3072, cfg.ctx_size)
            self.assertEqual(17, cfg.gpu_layers)
            self.assertEqual("model_server.context_tokens", cfg.context_source)
            self.assertEqual("model_server.gpu_layers", cfg.gpu_layers_source)

    def test_context_profile_change_updates_manager_and_localoperator_reporting(self) -> None:
        previous = os.environ.get(RUNTIME_PROFILES_ENV)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                profile_path = self.write_profile(root, context_tokens=3072)
                os.environ[RUNTIME_PROFILES_ENV] = profile_path.as_posix()
                first = model_server_manager.status_payload()
                resolved_model_path, resolved_source, _checked = model_service.resolve_model_path()
                reasoning_tokens = model_service._configured_max_tokens("reasoning_max_tokens", 192)

                self.write_profile(root, context_tokens=4096)
                second = model_server_manager.status_payload()

            self.assertEqual(Path(first["model_path"]), resolved_model_path)
            self.assertEqual("configured", resolved_source)
            self.assertEqual(321, reasoning_tokens)
            self.assertEqual(3072, first.get("ctx_size"))
            self.assertEqual(3072, first.get("model_context_tokens"))
            self.assertEqual(3072, mission_runtime._model_context_tokens(first))
            self.assertEqual(4096, second.get("ctx_size"))
            self.assertEqual(4096, second.get("model_context_tokens"))
            self.assertEqual(4096, mission_runtime._model_context_tokens(second))
        finally:
            if previous is None:
                os.environ.pop(RUNTIME_PROFILES_ENV, None)
            else:
                os.environ[RUNTIME_PROFILES_ENV] = previous


if __name__ == "__main__":
    unittest.main()
