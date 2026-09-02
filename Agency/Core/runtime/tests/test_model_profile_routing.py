from __future__ import annotations

import unittest
from pathlib import Path


class ModelRuntimeRoutingTests(unittest.TestCase):
    def test_model_service_reads_environment_runtime_identity(self) -> None:
        source_path = Path(__file__).resolve().parents[1] / "model_service.py"
        source = source_path.read_text(encoding="utf-8")

        self.assertIn('.get("backend")', source)
        self.assertIn('.get("inference_route")', source)
        self.assertIn('backend == "llama_server"', source)
        self.assertNotIn('.get("profile") or "silver"', source)


if __name__ == "__main__":
    unittest.main()