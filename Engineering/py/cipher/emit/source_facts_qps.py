from __future__ import annotations

import math
from typing import Any

from ..ir.source_facts import (
    DependencyFact,
    SourceArtifactFact,
    SourceDocumentFacts,
    SourceFact,
    SourceFactRef,
)


def _q(value: str) -> str:
    return (
        '"'
        + value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        + '"'
    )


def _lines(
    lines: list[str],
    depth: int,
    text: str,
) -> None:
    lines.append(
        "    " * depth + text
    )


def _emit_value(
    value: Any,
    lines: list[str],
    depth: int,
) -> None:
    if value is None:
        _lines(lines, depth, 'kind- "none";')
        return

    if isinstance(value, bool):
        _lines(lines, depth, 'kind- "boolean";')
        _lines(
            lines,
            depth,
            f'value- "{str(value).lower()}";',
        )
        return

    if isinstance(value, (int, float)):
        if (
            isinstance(value, float)
            and not math.isfinite(value)
        ):
            raise ValueError(
                "Non-finite numeric source fact "
                "cannot be serialized truthfully."
            )

        _lines(lines, depth, 'kind- "number";')
        _lines(lines, depth, f"value- {value!r};")
        return

    if isinstance(value, str):
        _lines(lines, depth, 'kind- "string";')
        _lines(lines, depth, f"value- {_q(value)};")
        return

    if isinstance(value, (list, tuple)):
        _lines(lines, depth, 'kind- "sequence";')
        _lines(lines, depth, "elements: (")

        for index, element in enumerate(
            value,
            start=1,
        ):
            _lines(
                lines,
                depth + 1,
                f"element_{index}: (",
            )
            _emit_value(
                element,
                lines,
                depth + 2,
            )
            _lines(lines, depth + 1, ");")

        _lines(lines, depth, ");")
        return

    if isinstance(value, dict):
        _lines(lines, depth, 'kind- "mapping";')
        _lines(lines, depth, "entries: (")

        for index, (key, element) in enumerate(
            value.items(),
            start=1,
        ):
            _lines(
                lines,
                depth + 1,
                f"entry_{index}: (",
            )

            _lines(lines, depth + 2, "key: (")
            _emit_value(
                key,
                lines,
                depth + 3,
            )
            _lines(lines, depth + 2, ");")

            _lines(lines, depth + 2, "value: (")
            _emit_value(
                element,
                lines,
                depth + 3,
            )
            _lines(lines, depth + 2, ");")

            _lines(lines, depth + 1, ");")

        _lines(lines, depth, ");")
        return

    raise TypeError(
        "Unsupported factual source value: "
        f"{type(value).__name__}"
    )


def _emit_source_ref(
    source: SourceFactRef,
    lines: list[str],
    depth: int,
) -> None:
    _lines(
        lines,
        depth,
        f"language- {_q(source.language)};",
    )
    _lines(
        lines,
        depth,
        f"path- {_q(source.path)};",
    )

    if source.line is not None:
        _lines(
            lines,
            depth,
            f"line- {source.line};",
        )

    if source.column is not None:
        _lines(
            lines,
            depth,
            f"column- {source.column};",
        )


def _emit_dependency(
    dependency: DependencyFact,
    lines: list[str],
    depth: int,
) -> None:
    _lines(
        lines,
        depth,
        f"package- {_q(dependency.package)};",
    )

    if dependency.module is not None:
        _lines(
            lines,
            depth,
            f"module- {_q(dependency.module)};",
        )

    if dependency.symbol is not None:
        _lines(
            lines,
            depth,
            f"symbol- {_q(dependency.symbol)};",
        )

    if dependency.alias is not None:
        _lines(
            lines,
            depth,
            f"alias- {_q(dependency.alias)};",
        )

    if dependency.version is not None:
        _lines(
            lines,
            depth,
            f"version- {_q(dependency.version)};",
        )


def _emit_node(
    node: SourceFact,
    lines: list[str],
    depth: int,
) -> None:
    _lines(
        lines,
        depth,
        f"kind- {_q(node.kind)};",
    )

    if node.name is not None:
        _lines(
            lines,
            depth,
            f"name- {_q(node.name)};",
        )

    _lines(lines, depth, "value: (")
    _emit_value(
        node.value,
        lines,
        depth + 1,
    )
    _lines(lines, depth, ");")

    if node.source is not None:
        _lines(lines, depth, "source: (")
        _emit_source_ref(
            node.source,
            lines,
            depth + 1,
        )
        _lines(lines, depth, ");")

    _lines(lines, depth, "dependencies: (")

    for index, dependency in enumerate(
        node.dependencies,
        start=1,
    ):
        _lines(
            lines,
            depth + 1,
            f"dependency_{index}: (",
        )
        _emit_dependency(
            dependency,
            lines,
            depth + 2,
        )
        _lines(lines, depth + 1, ");")

    _lines(lines, depth, ");")

    _lines(lines, depth, "children: (")

    for index, child in enumerate(
        node.children,
        start=1,
    ):
        _lines(
            lines,
            depth + 1,
            f"node_{index}: (",
        )
        _emit_node(
            child,
            lines,
            depth + 2,
        )
        _lines(lines, depth + 1, ");")

    _lines(lines, depth, ");")


def _emit_artifact(
    artifact: SourceArtifactFact,
    lines: list[str],
    depth: int,
) -> None:
    _lines(
        lines,
        depth,
        f"path- {_q(artifact.path)};",
    )
    _lines(
        lines,
        depth,
        f"family- {_q(artifact.family)};",
    )
    _lines(
        lines,
        depth,
        f"extension- {_q(artifact.extension)};",
    )


def emit_source_facts_qps(
    facts: SourceDocumentFacts,
) -> str:
    lines: list[str] = [
        "Cipher_Source_Facts.",
    ]

    _lines(lines, 0, "sources: (")

    for index, artifact in enumerate(
        facts.sources,
        start=1,
    ):
        _lines(
            lines,
            1,
            f"source_{index}: (",
        )
        _emit_artifact(
            artifact,
            lines,
            2,
        )
        _lines(lines, 1, ");")

    _lines(lines, 0, ");")

    _lines(lines, 0, "nodes: (")

    for index, node in enumerate(
        facts.children,
        start=1,
    ):
        _lines(
            lines,
            1,
            f"node_{index}: (",
        )
        _emit_node(
            node,
            lines,
            2,
        )
        _lines(lines, 1, ");")

    _lines(lines, 0, ");")

    return "\n".join(lines) + "\n"
