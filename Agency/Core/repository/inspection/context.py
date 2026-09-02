from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class InspectionContextDependencies:
    dashboard_root: Path
    required_context_files: tuple[Path, ...]
    max_total_source_bytes: int
    max_prompt_source_chars: int
    max_prompt_chars: int
    candidate_files: Callable[[list[dict[str, Any]]], list[Path]]
    manifest_candidate_paths: Callable[
        [list[Any]],
        tuple[list[Path], list[dict[str, Any]]],
    ]
    path_in_validated_scopes: Callable[
        [Path, list[dict[str, Any]]],
        bool,
    ]
    skip_reason_for_path: Callable[[Path], str | None]
    read_text_file: Callable[[Path], tuple[str | None, str | None]]
    inspection_evidence_terms: Callable[[str], list[str]]
    extract_symbols: Callable[[Path, str], list[dict[str, Any]]]
    extract_dependencies: Callable[[Path, str], list[dict[str, Any]]]
    compact_json_context: Callable[[Path], dict[str, Any]]


def build_inspection_context(
    intent: str,
    scopes: list[dict[str, Any]],
    *,
    dependencies: InspectionContextDependencies,
    candidate_paths: list[Any] | None = None,
    previously_inspected: set[str] | None = None,
    file_classification: dict[str, str] | None = None,
    max_files: int | None = None,
    stop_at_file_limit: bool = False,
) -> dict[str, Any]:
    inspected_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []
    remaining_files: list[str] = []
    file_excerpts: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    dependency_records: list[dict[str, Any]] = []
    previously_inspected = previously_inspected or set()
    file_classification = file_classification or {}
    source_bytes = 0
    prompt_source_chars = 0
    dashboard_root = dependencies.dashboard_root.resolve()

    if candidate_paths is None:
        candidates = dependencies.candidate_files(scopes)
        discovered_files = [
            path.resolve(strict=True).relative_to(dashboard_root).as_posix()
            for path in candidates
        ]
    else:
        candidates, skipped_files = dependencies.manifest_candidate_paths(
            candidate_paths
        )
        discovered_files = [
            path.relative_to(dashboard_root).as_posix()
            for path in candidates
        ]

    for path in candidates:
        try:
            rel = (
                path.resolve(strict=False)
                .relative_to(dashboard_root)
                .as_posix()
            )
        except ValueError:
            skipped_files.append(
                {
                    "path": str(path),
                    "reason": "candidate_escapes_repository",
                }
            )
            continue

        if rel in previously_inspected:
            continue
        if (
            stop_at_file_limit
            and max_files is not None
            and len(inspected_files) >= max_files
        ):
            remaining_files.append(rel)
            continue
        if not path.exists():
            skipped_files.append({"path": rel, "reason": "missing"})
            continue
        if not path.is_file():
            skipped_files.append({"path": rel, "reason": "not_file"})
            continue

        resolved = path.resolve(strict=True)
        if not dependencies.path_in_validated_scopes(resolved, scopes):
            skipped_files.append(
                {"path": rel, "reason": "outside_declared_scopes"}
            )
            continue

        reason = dependencies.skip_reason_for_path(resolved)
        if reason:
            skipped_files.append({"path": rel, "reason": reason})
            continue

        if max_files is not None and len(inspected_files) >= max_files:
            skipped_files.append(
                {"path": rel, "reason": "file_count_limit_reached"}
            )
            continue

        text, read_error = dependencies.read_text_file(resolved)
        if text is None:
            skipped_files.append(
                {"path": rel, "reason": read_error or "not_text"}
            )
            continue

        encoded_len = len(text.encode("utf-8"))
        if (
            source_bytes + encoded_len
            > dependencies.max_total_source_bytes
        ):
            skipped_files.append(
                {
                    "path": rel,
                    "reason": "source_byte_limit_reached",
                    "bytes": encoded_len,
                }
            )
            continue

        line_count = len(text.splitlines())
        evidence_terms = dependencies.inspection_evidence_terms(text)
        remaining_prompt = max(
            0,
            dependencies.max_prompt_source_chars - prompt_source_chars,
        )
        excerpt = ""
        if remaining_prompt > 0:
            excerpt = text[:remaining_prompt]
            prompt_source_chars += len(excerpt)
            file_excerpts.append(
                {
                    "path": rel,
                    "bytes": encoded_len,
                    "lines": line_count,
                    "excerpt": excerpt,
                }
            )

        record = {
            "path": rel,
            "bytes": encoded_len,
            "lines": line_count,
            "included_in_prompt": bool(excerpt),
            "prompt_excerpt_chars": len(excerpt),
            "evidence_terms": evidence_terms,
        }
        if rel in file_classification:
            record["class"] = file_classification[rel]

        inspected_files.append(record)
        symbols.extend(dependencies.extract_symbols(resolved, text))
        dependency_records.extend(
            dependencies.extract_dependencies(resolved, text)
        )
        source_bytes += encoded_len

    operational_context = [
        dependencies.compact_json_context(path)
        for path in dependencies.required_context_files
    ]

    return {
        "intent": intent,
        "operational_context": operational_context,
        "discovered_files": discovered_files,
        "inspected_files": inspected_files,
        "remaining_files": remaining_files,
        "skipped_files": skipped_files,
        "symbols": symbols,
        "dependencies": dependency_records,
        "file_excerpts": file_excerpts,
        "context_limits": {
            "max_files": max_files,
            "max_total_source_bytes": dependencies.max_total_source_bytes,
            "max_prompt_source_chars": dependencies.max_prompt_source_chars,
            "max_prompt_chars": dependencies.max_prompt_chars,
        },
        "context_bytes": {
            "source_bytes_inspected": source_bytes,
            "prompt_source_chars": prompt_source_chars,
        },
    }
