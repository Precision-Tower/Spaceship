from __future__ import annotations

from Agency.Core.runtime.commands import mission_command
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class InspectionAnalysisDependencies:
    """Dependencies required by pure inspection analysis."""

    dashboard_root: Path
    inspection_classes: Sequence[str]
    mission_coverage_categories: Sequence[str]
    dedupe_manifest_paths: Callable[[list[Any]], list[str]]
    classify_inspection_file: Callable[..., dict[str, str]]
    sort_class_paths: Callable[[list[str], set[str]], list[str]]
    next_action_after_plan: Callable[..., dict[str, Any]]


def classify_mission_files(
    discovered_files: list[str],
    *,
    intent_requests: set[str],
    referenced_paths: set[str],
    dependencies: InspectionAnalysisDependencies,
) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    """Validate, classify, and order discovered mission paths."""

    files_by_class = {
        class_name: []
        for class_name in dependencies.inspection_classes
    }
    skipped: list[dict[str, str]] = []

    repo_root = dependencies.dashboard_root.resolve()

    for raw_path in dependencies.dedupe_manifest_paths(
        discovered_files
    ):
        rel_path = Path(raw_path)

        if rel_path.is_absolute() or ".." in rel_path.parts:
            files_by_class["ignored"].append(str(raw_path))
            skipped.append({
                "path": str(raw_path),
                "reason": "invalid_manifest_path",
            })
            continue

        path = (
            dependencies.dashboard_root / rel_path
        ).resolve(strict=False)

        try:
            normalized = path.relative_to(
                repo_root
            ).as_posix()
        except ValueError:
            files_by_class["ignored"].append(str(raw_path))
            skipped.append({
                "path": str(raw_path),
                "reason": "manifest_path_escapes_repository",
            })
            continue

        if not path.exists():
            files_by_class["ignored"].append(normalized)
            skipped.append({
                "path": normalized,
                "reason": "missing",
            })
            continue

        if not path.is_file():
            files_by_class["ignored"].append(normalized)
            skipped.append({
                "path": normalized,
                "reason": "not_file",
            })
            continue

        classification = (
            dependencies.classify_inspection_file(
                path,
                intent_requests=intent_requests,
            )
        )
        class_name = classification["class"]
        files_by_class[class_name].append(normalized)

        if class_name == "ignored":
            skipped.append({
                "path": normalized,
                "reason": classification.get(
                    "reason",
                    "ignored_by_classification",
                ),
            })

    for class_name in (
        "primary",
        "secondary",
        "evidence",
    ):
        files_by_class[class_name] = (
            dependencies.sort_class_paths(
                files_by_class[class_name],
                referenced_paths,
            )
        )

    files_by_class["ignored"] = sorted(
        files_by_class["ignored"],
        key=lambda path: (
            path.lower(),
            path,
        ),
    )

    return files_by_class, skipped


def coverage_evidence_from_context(
    context: dict[str, Any],
    *,
    dependencies: InspectionAnalysisDependencies,
) -> dict[str, list[dict[str, str]]]:
    """Derive inspection coverage evidence from inspected files."""

    evidence: dict[str, list[dict[str, str]]] = {
        category: []
        for category in dependencies.mission_coverage_categories
    }

    for record in context.get("inspected_files", []):
        path = str(record.get("path") or "")
        lower_path = path.lower()
        terms = set(record.get("evidence_terms", []))
        file_class = str(record.get("class") or "")

        is_primary = file_class == "primary"
        is_evidence = file_class == "evidence"

        if (
            path in {
                "UI/Main/Main.gd",
                "UI/OperatorShell/Main.gd",
            }
            or "route" in terms
            or "route" in lower_path
        ):
            evidence["route_ownership"].append({
                "path": path,
                "reason": (
                    "inspected route-related path or marker"
                ),
            })

        if (
            "workspace" in lower_path
            or "workspace" in terms
        ):
            evidence["workspace_host"].append({
                "path": path,
                "reason": (
                    "inspected workspace-related path or marker"
                ),
            })

        if (
            path in {
                "UI/Workbench/Main/Main.gd",
                "UI/Workbench/Main/Main.tscn",
                "UI/Workbench/scenes/Workbench.gd",
                "UI/Workbench/scenes/Workbench.tscn",
            }
            or (
                is_primary
                and "workbench" in terms
            )
        ):
            evidence["workbench_root"].append({
                "path": path,
                "reason": (
                    "inspected Workbench path or marker"
                ),
            })

        if terms.intersection({
            "instantiate",
            "add_child",
        }):
            evidence["creation_lifecycle"].append({
                "path": path,
                "reason": (
                    "inspected creation lifecycle marker"
                ),
            })

        if terms.intersection({
            "remove_child",
            "queue_free",
            "cleanup",
        }):
            evidence["cleanup_lifecycle"].append({
                "path": path,
                "reason": (
                    "inspected cleanup lifecycle marker"
                ),
            })

        if is_primary and path:
            evidence["expected_modified_files"].append({
                "path": path,
                "reason": (
                    "primary engineering source inspected"
                ),
            })

        if (
            is_evidence
            or terms.intersection({
                "screenshot",
                "audit",
                "test",
                "verify",
            })
            or any(
                marker in lower_path
                for marker in (
                    "audit",
                    "test",
                    "screenshot",
                    "verify",
                )
            )
        ):
            evidence["verification_surfaces"].append({
                "path": path,
                "reason": (
                    "inspected verification-related path "
                    "or marker"
                ),
            })

    return evidence


def mission_next_command_from_artifacts(
    mission_dir: Path,
    *,
    state: dict[str, Any],
    plan: dict[str, Any],
    proposed: bool,
    planned: bool,
    approved: bool,
    review_decision: str,
    unit_progress: dict[str, Any],
    verification_report: dict[str, Any],
    inspection_passes: list[Path],
    dependencies: InspectionAnalysisDependencies,
) -> dict[str, Any]:
    """Determine the next mission command from recorded artifacts."""

    mission_id = mission_dir.name

    if verification_report.get("result") == "passed":
        return {
            "command": None,
            "reason": "Mission completed successfully.",
        }

    if verification_report:
        return {
            "command": "Review verification/report.json",
            "reason": "Final verification did not pass.",
        }

    if unit_progress.get("implementation_complete"):
        return {
            "command": mission_command("verify", mission_id),
            "reason": (
                "Implementation is complete and final "
                "verification is pending."
            ),
        }

    if approved:
        return {
            "command": mission_command("implement", mission_id),
            "reason": (
                "Approved implementation units remain "
                "incomplete."
            ),
        }

    if review_decision in {
        "rejected",
        "changes_requested",
    }:
        return {
            "command": "Review proposal or regenerate.",
            "reason": (
                "Operator review did not approve "
                "implementation."
            ),
        }

    if proposed:
        return {
            "command": mission_command("review", mission_id, "--approve"),
            "reason": (
                "No approved operator review artifact "
                "is recorded."
            ),
        }

    if planned:
        return dependencies.next_action_after_plan(
            mission_id,
            plan,
            state=state,
        )

    if inspection_passes:
        return {
            "command": mission_command("plan", mission_id),
            "reason": (
                "No architecture plan artifact is recorded."
            ),
        }

    return {
        "command": mission_command("inspect", mission_id),
        "reason": "No inspection passes are recorded.",
    }