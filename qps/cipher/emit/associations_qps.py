from __future__ import annotations

import os
from pathlib import Path


def relative_qps_file_address(
    source_qps: str | Path,
    target_qps: str | Path,
) -> str:
    source = Path(source_qps)
    target = Path(target_qps)

    relative = Path(
        os.path.relpath(
            target,
            source.parent,
        )
    )

    parts = list(relative.parts)

    parent_depth = 0

    while parts and parts[0] == "..":
        parent_depth += 1
        parts.pop(0)

    if parts and parts[0] == ".":
        parts.pop(0)

    if not parts:
        raise ValueError(
            "QPS association target cannot be empty"
        )

    final = Path(parts[-1])

    if final.suffix == ".qps":
        parts[-1] = final.stem

    if parts[-1] == "_index":
        parts.pop()

    if parent_depth == 0:
        prefix = "."
    else:
        prefix = "/" * parent_depth

    if not parts:
        return prefix

    return prefix + "/".join(parts)


def emit_association(
    *,
    local_name: str,
    source_qps: str | Path,
    target_qps: str | Path,
    target_identity: str | None = None,
) -> str:
    address = relative_qps_file_address(
        source_qps,
        target_qps,
    )

    if target_identity:
        address += "." + target_identity

    return (
        f"{local_name}: "
        f"[>{address}];"
    )
