from __future__ import annotations

from typing import Any

from Agency.Core.knowledge.reasoning.selection import select_high_value_evidence


def build_reasoning_context(
    artifacts: dict[str, Any],
    evidence: dict[str, Any],
    readiness: dict[str, Any],
    *,
    inspection_classes: tuple[str, ...] | list[str],
    coverage_categories: tuple[str, ...] | list[str],
    resourcefulness_context: list[dict[str, Any]],
) -> dict[str, Any]:
    coverage = artifacts.get("coverage", {})
    files_by_class = evidence.get("files_by_class", {})

    return {
        "coverage_summary": coverage.get("categories", {}),
        "coverage_unresolved": evidence.get("coverage_unresolved", [])[:12],
        "inspection_status": {
            "inspection_complete": bool(
                coverage.get("inspection_complete", False)
            ),
            "passes": len(artifacts.get("passes", [])),
            "readiness": readiness,
            "files_inspected": len(evidence.get("files_inspected", [])),
            "files_remaining": len(evidence.get("files_remaining", [])),
        },
        "files_by_class_counts": {
            class_name: len(files_by_class.get(class_name, []))
            for class_name in inspection_classes
        },
        "high_value_observations": select_high_value_evidence(
            evidence,
            coverage_categories=coverage_categories,
        ),
        "inspected_file_inventory": evidence.get("files_inspected", [])[:40],
        "resourcefulness_context": resourcefulness_context,
    }
