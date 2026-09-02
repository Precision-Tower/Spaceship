import unittest

from Agency.Core.knowledge.reasoning import build_reasoning_context


class BuildReasoningContextTests(unittest.TestCase):
    def test_builds_shared_evidence_state(self) -> None:
        artifacts = {
            "coverage": {
                "inspection_complete": True,
                "categories": {
                    "runtime": "covered",
                },
            },
            "passes": [
                {"pass": 1},
                {"pass": 2},
            ],
        }
        evidence = {
            "coverage_unresolved": ["missing-a", "missing-b"],
            "files_by_class": {
                "runtime": ["a.py", "b.py"],
                "tests": ["test_a.py"],
            },
            "files_inspected": ["a.py", "b.py"],
            "files_remaining": ["c.py"],
            "observations": [
                {
                    "id": "obs-001",
                    "pass": 2,
                    "path": "a.py",
                    "kind": "symbol",
                    "summary": "Found runtime entry point",
                }
            ],
            "coverage_evidence": {
                "runtime": [{"path": "a.py"}],
            },
        }
        readiness = {
            "ready": True,
            "reason": "coverage sufficient",
        }
        resourcefulness_context = [
            {
                "path": "knowledge.json",
                "strategy": "reconstruct",
            }
        ]

        context = build_reasoning_context(
            artifacts,
            evidence,
            readiness,
            inspection_classes=("runtime", "tests"),
            coverage_categories=("runtime",),
            resourcefulness_context=resourcefulness_context,
        )

        self.assertEqual(
            context["coverage_summary"],
            {"runtime": "covered"},
        )
        self.assertEqual(
            context["coverage_unresolved"],
            ["missing-a", "missing-b"],
        )
        self.assertEqual(
            context["inspection_status"],
            {
                "inspection_complete": True,
                "passes": 2,
                "readiness": readiness,
                "files_inspected": 2,
                "files_remaining": 1,
            },
        )
        self.assertEqual(
            context["files_by_class_counts"],
            {
                "runtime": 2,
                "tests": 1,
            },
        )
        self.assertEqual(
            context["high_value_observations"][0]["id"],
            "obs-001",
        )
        self.assertEqual(
            context["inspected_file_inventory"],
            ["a.py", "b.py"],
        )
        self.assertIs(
            context["resourcefulness_context"],
            resourcefulness_context,
        )

    def test_applies_context_limits(self) -> None:
        evidence = {
            "coverage_unresolved": [
                f"missing-{index}"
                for index in range(20)
            ],
            "files_inspected": [
                f"file-{index}.py"
                for index in range(50)
            ],
            "files_remaining": [],
            "files_by_class": {},
            "observations": [],
            "coverage_evidence": {},
        }

        context = build_reasoning_context(
            {"coverage": {}, "passes": []},
            evidence,
            {},
            inspection_classes=(),
            coverage_categories=(),
            resourcefulness_context=[],
        )

        self.assertEqual(len(context["coverage_unresolved"]), 12)
        self.assertEqual(len(context["inspected_file_inventory"]), 40)


if __name__ == "__main__":
    unittest.main()
