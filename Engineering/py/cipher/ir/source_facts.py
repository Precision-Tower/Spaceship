from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .document import CipherDocument
from .nodes import CipherNode, DependencyRef, SourceRef


@dataclass(frozen=True)
class SourceFactRef:
    language: str
    path: str
    line: int | None
    column: int | None


@dataclass(frozen=True)
class DependencyFact:
    package: str
    module: str | None
    symbol: str | None
    alias: str | None
    version: str | None


@dataclass(frozen=True)
class SourceFact:
    kind: str
    name: str | None
    value: Any
    children: tuple["SourceFact", ...]
    source: SourceFactRef | None
    dependencies: tuple[DependencyFact, ...]


@dataclass(frozen=True)
class SourceArtifactFact:
    path: str
    family: str
    extension: str


@dataclass(frozen=True)
class SourceDocumentFacts:
    children: tuple[SourceFact, ...]
    sources: tuple[SourceArtifactFact, ...]


def _source_fact(
    source: SourceRef | None,
) -> SourceFactRef | None:
    if source is None:
        return None

    return SourceFactRef(
        language=source.language,
        path=source.path,
        line=source.line,
        column=source.column,
    )


def _dependency_fact(
    dependency: DependencyRef,
) -> DependencyFact:
    return DependencyFact(
        package=dependency.package,
        module=dependency.module,
        symbol=dependency.symbol,
        alias=dependency.alias,
        version=dependency.version,
    )


def _node_fact(
    node: CipherNode,
) -> SourceFact:
    return SourceFact(
        kind=node.kind,
        name=node.name,
        value=node.value,
        children=tuple(
            _node_fact(child)
            for child in node.children
        ),
        source=_source_fact(node.source),
        dependencies=tuple(
            _dependency_fact(dependency)
            for dependency in node.dependencies
        ),
    )


def project_source_facts(
    document: CipherDocument,
) -> SourceDocumentFacts:
    return SourceDocumentFacts(
        children=tuple(
            _node_fact(child)
            for child in document.children
        ),
        sources=tuple(
            SourceArtifactFact(
                path=source.path,
                family=source.family,
                extension=source.extension,
            )
            for source in document.sources
        ),
    )
