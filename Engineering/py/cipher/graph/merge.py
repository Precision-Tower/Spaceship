from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..ir.document import CipherDocument
from ..ir.nodes import CipherNode, DependencyRef
from ..sources.python_source import load_python
from .dependency_closure import (
    DependencyClosure,
    ImportBinding,
    build_dependency_closure,
)


@dataclass
class MergedCipherDocument:
    document: CipherDocument
    closure: DependencyClosure
    foreign_dependencies: list[ImportBinding] = field(
        default_factory=list
    )


def _dependency_key(
    dependency: DependencyRef,
) -> tuple[str, str | None, str | None]:
    return (
        dependency.module or dependency.package,
        dependency.symbol,
        dependency.alias,
    )


def _foreign_keys(
    closure: DependencyClosure,
) -> set[tuple[str, str | None, str | None]]:
    return {
        (
            dependency.module,
            dependency.symbol,
            dependency.alias,
        )
        for dependency in closure.external
    }


def _keep_import(
    node: CipherNode,
    foreign_keys: set[
        tuple[str, str | None, str | None]
    ],
) -> bool:
    if node.kind != "import":
        return True

    return any(
        _dependency_key(dependency) in foreign_keys
        for dependency in node.dependencies
    )


def merge_local_python(
    entry: str | Path,
    workspace_root: str | Path,
) -> MergedCipherDocument:
    closure = build_dependency_closure(
        entry,
        workspace_root,
    )

    foreign_keys = _foreign_keys(closure)
    children: list[CipherNode] = []
    sources = []

    # Deterministic order. Entry first, then all remaining units by path.
    entry_path = closure.entry
    ordered = [
        entry_path,
        *sorted(
            path
            for path in closure.units
            if path != entry_path
        ),
    ]

    for path in ordered:
        document = load_python(path)
        sources.extend(document.sources)

        for child in document.children:
            if _keep_import(child, foreign_keys):
                children.append(child)

    return MergedCipherDocument(
        document=CipherDocument(
            children=children,
            sources=sources,
        ),
        closure=closure,
        foreign_dependencies=sorted(
            closure.external,
            key=lambda item: (
                item.module,
                item.symbol or "",
                item.alias or "",
            ),
        ),
    )
