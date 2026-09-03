from __future__ import annotations

import json

from ..ir.document import CipherDocument
from ..ir.nodes import CipherNode


def _scalar(value) -> str:
    if value is None:
        return "/n"

    if value is True:
        return "true/b"

    if value is False:
        return "false/b"

    if isinstance(value, (int, float)):
        return str(value)

    return json.dumps(str(value), ensure_ascii=False) + "/a"


def _emit_node(node: CipherNode, indent: int = 0) -> str:
    pad = " " * indent

    if node.kind == "term":
        label = node.name or "value"
        body = "\n".join(
            _emit_node(child, indent + 4)
            for child in node.children
        )
        return f"{pad}{label}: (\n{body}\n{pad});"

    if node.kind == "list":
        label = node.name or "value"
        body = "\n".join(
            f'{" " * (indent + 4)}item_{i}- {_scalar(child.value)};'
            if child.kind == "item"
            else _emit_node(child, indent + 4)
            for i, child in enumerate(node.children)
        )
        return f"{pad}{label}: (\n{body}\n{pad});"

    if node.kind == "item":
        label = node.name or "value"
        return f"{pad}{label}- {_scalar(node.value)};"

    if node.kind == "parameter":
        label = node.name or "parameter"
        return f"{pad}{label}- {_scalar(node.value)};"

    if node.kind == "documentation":
        label = node.name or "documentation"
        return f"{pad}{label}- {_scalar(node.value)};"

    if node.kind == "execution":
        label = node.name or "execution"
        return f"{pad}{label}- /n;"

    if node.kind in {"definition", "function"}:
        label = node.name or node.kind
        body = "\n".join(
            _emit_node(child, indent + 4)
            for child in node.children
        )
        return f"{pad}{label}: (\n{body}\n{pad});"

    raise ValueError(f"Unsupported Cipher node kind: {node.kind}")


def emit_qps(document: CipherDocument) -> str:
    return "\n".join(
        _emit_node(child)
        for child in document.children
    ) + "\n"
