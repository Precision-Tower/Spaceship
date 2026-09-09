from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qps.cipher.ir.nodes import DependencyRef


@dataclass(frozen=True)
class LibraryLookup:
    dependency: DependencyRef
    namespace_root: Path
    index_path: Path | None
    symbol_path: Path | None
    state: str
    detail: str = ""


def _parse_surface(index_path: Path) -> dict[str, str]:
    """
    Minimal read-only parser for the canonical immediate-child
    `surface: (...)` contract used by qps/libs indexes.

    This is deliberately narrow. It does not attempt to become
    another QPS parser.
    """
    text = index_path.read_text(encoding="utf-8")

    marker = "surface: ("
    start = text.find(marker)

    if start < 0:
        raise ValueError(
            f"library index has no surface: {index_path}"
        )

    open_pos = text.find("(", start)
    depth = 0
    quoted = False
    escaped = False
    end = None

    for i in range(open_pos, len(text)):
        c = text[i]

        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
            continue

        if c == '"':
            quoted = True
            continue

        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1

            if depth == 0:
                end = i
                break

    if end is None:
        raise ValueError(
            f"unterminated surface in {index_path}"
        )

    body = text[open_pos + 1:end]
    result: dict[str, str] = {}

    for raw in body.splitlines():
        line = raw.strip()

        if not line or line.startswith("//"):
            continue

        if "- " not in line:
            continue

        key, value = line.split("- ", 1)

        key = key.strip()
        value = value.strip()

        if value.endswith(";"):
            value = value[:-1].rstrip()

        if (
            len(value) >= 2
            and value[0] == '"'
            and value[-1] == '"'
        ):
            value = value[1:-1]

        result[key] = value

    return result


def _module_parts(dependency: DependencyRef) -> list[str]:
    module = (
        dependency.module
        or dependency.package
        or ""
    )

    return [
        part
        for part in module.split(".")
        if part
    ]


def lookup_python_library(
    dependency: DependencyRef,
    workspace_root: str | Path,
) -> LibraryLookup:
    workspace_root = Path(workspace_root).resolve()

    namespace_root = (
        workspace_root
        / "libs"
        / "Python"
    )

    current_index = namespace_root / "_index.qps"

    if not current_index.exists():
        return LibraryLookup(
            dependency=dependency,
            namespace_root=namespace_root,
            index_path=None,
            symbol_path=None,
            state="unresolved",
            detail="Python library root is not indexed",
        )

    parts = _module_parts(dependency)

    for part in parts:
        surface = _parse_surface(current_index)

        child = surface.get(part)

        if child is None:
            return LibraryLookup(
                dependency=dependency,
                namespace_root=namespace_root,
                index_path=current_index,
                symbol_path=None,
                state="library-missing",
                detail=(
                    "missing namespace component "
                    f"{part}"
                ),
            )

        child_path = (
            current_index.parent / child
        ).resolve()

        if child_path.name == "_index.qps":
            next_index = child_path
        elif child_path.is_dir():
            next_index = child_path / "_index.qps"
        else:
            next_index = child_path

        if not next_index.exists():
            return LibraryLookup(
                dependency=dependency,
                namespace_root=namespace_root,
                index_path=current_index,
                symbol_path=None,
                state="library-missing",
                detail=(
                    "indexed namespace target missing: "
                    f"{next_index}"
                ),
            )

        current_index = next_index

    symbol = dependency.symbol

    if not symbol:
        return LibraryLookup(
            dependency=dependency,
            namespace_root=namespace_root,
            index_path=current_index,
            symbol_path=None,
            state="library-resolved",
            detail="module namespace resolved",
        )

    surface = _parse_surface(current_index)
    child = surface.get(symbol)

    if child is None:
        return LibraryLookup(
            dependency=dependency,
            namespace_root=namespace_root,
            index_path=current_index,
            symbol_path=None,
            state="library-missing",
            detail=f"missing canonical symbol {symbol}",
        )

    symbol_path = (
        current_index.parent / child
    ).resolve()

    if not symbol_path.exists():
        return LibraryLookup(
            dependency=dependency,
            namespace_root=namespace_root,
            index_path=current_index,
            symbol_path=symbol_path,
            state="library-missing",
            detail=(
                "indexed symbol target does not exist: "
                f"{symbol_path}"
            ),
        )

    return LibraryLookup(
        dependency=dependency,
        namespace_root=namespace_root,
        index_path=current_index,
        symbol_path=symbol_path,
        state="library-resolved",
    )
