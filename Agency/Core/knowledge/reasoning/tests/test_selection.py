import unittest

from Agency.Core.knowledge.reasoning import select_high_value_evidence


class SelectHighValueEvidenceTests(unittest.TestCase):
    def test_preserves_coverage_and_structure(self) -> None:
        evidence = {
            "observations": [
                {
                    "id": "obs-file-a",
                    "pass": 1,
                    "path": "a.py",
                    "kind": "file_inspected",
                    "summary": "Inspected a.py",
                },
                {
                    "id": "obs-symbol-a",
                    "pass": 1,
                    "path": "a.py",
                    "kind": "symbol",
                    "summary": "Found symbol in a.py",
                },
                {
                    "id": "obs-dependency-b",
                    "pass": 2,
                    "path": "b.py",
                    "kind": "dependency",
                    "summary": "Found dependency in b.py",
                },
                {
                    "id": "obs-late-c",
                    "pass": 3,
                    "path": "c.py",
                    "kind": "pass_observation",
                    "summary": "Late pass observation",
                },
            ],
            "coverage_evidence": {
                "runtime": [{"path": "a.py"}],
                "repository": [{"path": "b.py"}],
            },
        }

        selected = select_high_value_evidence(
            evidence,
            coverage_categories=("runtime", "repository"),
            limit=4,
        )

        selected_ids = [item["id"] for item in selected]

        self.assertIn("obs-file-a", selected_ids)
        self.assertIn("obs-symbol-a", selected_ids)
        self.assertIn("obs-dependency-b", selected_ids)
        self.assertIn("obs-late-c", selected_ids)

    def test_deduplicates_observation_ids(self) -> None:
        duplicate = {
            "id": "obs-001",
            "pass": 1,
            "path": "a.py",
            "kind": "symbol",
            "summary": "Same observation",
        }

        evidence = {
            "observations": [duplicate, dict(duplicate)],
            "coverage_evidence": {
                "runtime": [{"path": "a.py"}],
            },
        }

        selected = select_high_value_evidence(
            evidence,
            coverage_categories=("runtime",),
            limit=10,
        )

        self.assertEqual(
            [item["id"] for item in selected],
            ["obs-001"],
        )

    def test_returns_compact_shape(self) -> None:
        evidence = {
            "observations": [
                {
                    "id": "obs-001",
                    "pass": 2,
                    "path": "a.py",
                    "kind": "dependency",
                    "summary": "Depends on b.py",
                    "extra": "must not leak",
                }
            ],
            "coverage_evidence": {},
        }

        selected = select_high_value_evidence(
            evidence,
            coverage_categories=(),
        )

        self.assertEqual(
            selected,
            [
                {
                    "id": "obs-001",
                    "pass": 2,
                    "path": "a.py",
                    "kind": "dependency",
                    "summary": "Depends on b.py",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
