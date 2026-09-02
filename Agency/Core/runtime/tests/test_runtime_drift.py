from __future__ import annotations

import unittest

from Agency.Core.runtime.environment import (
    normalize_runtime_endpoint,
    runtime_configuration_drift,
)


class RuntimeConfigurationDriftTests(unittest.TestCase):
    def test_detects_endpoint_difference(self) -> None:
        drift = runtime_configuration_drift(
            {
                "endpoint": "http://127.0.0.1:8081",
            },
            {
                "endpoint": "http://127.0.0.1:8001",
            },
        )

        self.assertTrue(drift["detected"])
        self.assertEqual(
            {
                "configured": "http://127.0.0.1:8081",
                "observed": "http://127.0.0.1:8001",
            },
            drift["fields"]["endpoint"],
        )

    def test_ignores_endpoint_trailing_slash(self) -> None:
        drift = runtime_configuration_drift(
            {
                "endpoint": "http://127.0.0.1:8001/",
            },
            {
                "endpoint": "http://127.0.0.1:8001",
            },
        )

        self.assertFalse(drift["detected"])
        self.assertEqual({}, drift["fields"])

    def test_missing_observation_is_not_drift(self) -> None:
        drift = runtime_configuration_drift(
            {
                "endpoint": "http://127.0.0.1:8081",
            },
            {
                "endpoint": None,
            },
        )

        self.assertFalse(drift["detected"])

    def test_endpoint_normalization(self) -> None:
        self.assertEqual(
            "http://127.0.0.1:8001",
            normalize_runtime_endpoint(
                " http://127.0.0.1:8001/// "
            ),
        )


if __name__ == "__main__":
    unittest.main()
