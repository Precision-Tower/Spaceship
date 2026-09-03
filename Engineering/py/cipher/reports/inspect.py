from __future__ import annotations

from ..ir.document import CipherDocument
from ..ir.nodes import CipherNode


def _walk(node: CipherNode, path: str):
    current = (
        f"{path}.{node.name}"
        if node.name
        else f"{path}.{node.kind}"
    )

    yield current, node

    for index, child in enumerate(node.children):
        child_path = current

        if child.name is None:
            child_path = f"{current}[{index}]"

        yield from _walk(child, child_path)


def unresolved(document: CipherDocument):
    result = []

    for index, root in enumerate(document.children):
        root_path = root.name or f"root[{index}]"

        for path, node in _walk(root, root_path):
            if node.state.value in {
                "unresolved",
                "unsupported",
            }:
                result.append({
                    "path": path,
                    "kind": node.kind,
                    "state": node.state.value,
                    "source": (
                        {
                            "language": node.source.language,
                            "path": node.source.path,
                            "line": node.source.line,
                            "column": node.source.column,
                        }
                        if node.source is not None
                        else None
                    ),
                    "notes": list(node.notes),
                })

    return result
