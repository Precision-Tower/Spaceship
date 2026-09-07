from __future__ import annotations

import json
from pathlib import Path

from ..ir.document import CipherDocument, SourceArtifact


def _q(value: str) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
    )


def stable_source_path(
    source: SourceArtifact,
    workspace_root: str | Path | None,
) -> str:
    path = Path(source.path)

    if workspace_root is None:
        return path.as_posix()

    root = Path(workspace_root).resolve()

    try:
        resolved = path.resolve()
    except OSError:
        return path.as_posix()

    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def emit_source_provenance(
    document: CipherDocument,
    *,
    workspace_root: str | Path | None = None,
) -> str:
    if not document.sources:
        return ""

    lines = [
        "cipher_source: (",
    ]

    seen: set[
        tuple[str, str, str]
    ] = set()

    index = 0

    for source in document.sources:
        path = stable_source_path(
            source,
            workspace_root,
        )

        identity = (
            path,
            source.family,
            source.extension,
        )

        if identity in seen:
            continue

        seen.add(identity)
        index += 1

        lines.extend(
            [
                f"source_{index}: (",
                f"path- {_q(path)};",
                f"family- {_q(source.family)};",
                f"extension- {_q(source.extension)};",
                ");",
                "",
            ]
        )

    lines.append(");")

    return "\n".join(lines)

def source_artifact_for_path(
    document: CipherDocument,
    source_path: str,
) -> SourceArtifact | None:
    if not source_path:
        return None

    candidate = Path(source_path)

    try:
        candidate_resolved = candidate.resolve()
    except OSError:
        candidate_resolved = candidate

    for source in document.sources:
        stored = Path(source.path)

        try:
            stored_resolved = stored.resolve()
        except OSError:
            stored_resolved = stored

        if stored_resolved == candidate_resolved:
            return source

    return None
