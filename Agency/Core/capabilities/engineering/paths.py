from __future__ import annotations

from pathlib import Path


def _strip_outer_quotes(value: str) -> str:
    value = value.strip()
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        return value[1:-1]
    return value


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _reject_path_traversal(raw_path: str) -> None:
    if ".." in Path(raw_path).parts:
        raise ValueError(
            f"path_traversal_rejected: {raw_path}"
        )


def resolve_workspace_path(
    raw_path: str,
    dashboard_root: Path,
) -> Path:
    if not raw_path or not raw_path.strip():
        raise ValueError("empty_path_rejected")

    raw_path = _strip_outer_quotes(raw_path)
    _reject_path_traversal(raw_path)

    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = dashboard_root / candidate

    resolved = candidate.resolve()
    root = dashboard_root.resolve()

    if not _is_within(resolved, root):
        raise ValueError(
            f"path_outside_workspace_rejected: {raw_path}"
        )

    if resolved == root:
        raise ValueError("workspace_root_write_rejected")

    return resolved


def packet_relative_path(
    raw_path: str,
    dashboard_root: Path,
) -> str:
    resolved = resolve_workspace_path(
        raw_path,
        dashboard_root,
    )
    return resolved.relative_to(
        dashboard_root.resolve()
    ).as_posix()


def diff_paths(diff_text: str) -> list[str]:
    paths: list[str] = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            for raw in parts[2:4]:
                if raw.startswith(("a/", "b/")):
                    paths.append(raw[2:])

        elif line.startswith(("--- ", "+++ ")):
            raw = line[4:].strip().split("\t", 1)[0]

            if raw == "/dev/null":
                continue

            if raw.startswith(("a/", "b/")):
                raw = raw[2:]

            paths.append(raw)

    return paths
