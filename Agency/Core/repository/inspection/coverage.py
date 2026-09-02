from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


COVERAGE_STATUS_RANK = {
    "not_started": 0,
    "partial": 1,
    "complete": 2,
}


@dataclass(frozen=True)
class InspectionCoverageDependencies:
    schema_version: Any
    coverage_categories: tuple[str, ...]
    coverage_evidence_from_context: Callable[
        [dict[str, Any]],
        dict[str, list[dict[str, str]]],
    ]


def _advance_coverage_status(
    current: str,
    candidate: str,
) -> str:
    current_rank = COVERAGE_STATUS_RANK.get(current, 0)
    candidate_rank = COVERAGE_STATUS_RANK.get(candidate, 0)
    return candidate if candidate_rank > current_rank else current


def _merge_evidence_items(
    existing: list[Any],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for item in [*existing, *incoming]:
        if not isinstance(item, dict):
            continue

        path = str(item.get("path") or "")
        reason = str(item.get("reason") or "")

        if not path or not reason:
            continue

        key = (path, reason)
        if key in seen:
            continue

        seen.add(key)
        merged.append(dict(item))

    return merged


def update_inspection_coverage(
    coverage: dict[str, Any],
    context: dict[str, Any],
    *,
    timestamp: str,
    inspection_complete: bool,
    next_files: list[str],
    dependencies: InspectionCoverageDependencies,
) -> dict[str, Any]:
    categories = coverage.get("categories", {})
    if not isinstance(categories, dict):
        categories = {}

    updated_categories = {
        category: str(categories.get(category) or "not_started")
        for category in dependencies.coverage_categories
    }

    evidence_log = coverage.get("evidence", {})
    if not isinstance(evidence_log, dict):
        evidence_log = {}

    new_evidence = dependencies.coverage_evidence_from_context(context)

    for category, items in new_evidence.items():
        if not items:
            continue

        updated_categories[category] = _advance_coverage_status(
            updated_categories.get(category, "not_started"),
            "partial",
        )

        existing_items = evidence_log.get(category, [])
        if not isinstance(existing_items, list):
            existing_items = []

        evidence_log[category] = _merge_evidence_items(
            existing_items,
            items,
        )

    unresolved: list[str] = []

    for category in dependencies.coverage_categories:
        status = updated_categories.get(category, "not_started")

        if status == "not_started":
            unresolved.append(
                f"{category} has no supporting inspection evidence yet."
            )
        elif status == "partial":
            unresolved.append(
                f"{category} has partial inspection evidence "
                "and still needs planning review."
            )

    if not inspection_complete:
        unresolved.insert(
            0,
            "Inspection remains incomplete: "
            f"{len(next_files)} next files queued.",
        )

    return {
        **coverage,
        "schema_version": coverage.get(
            "schema_version",
            dependencies.schema_version,
        ),
        "updated_at": timestamp,
        "inspection_complete": inspection_complete,
        "categories": updated_categories,
        "unresolved": unresolved,
        "next_inspection": next_files,
        "evidence": evidence_log,
        "authority": "inspection_coverage_not_capability",
    }
