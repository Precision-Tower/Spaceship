from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..ir.document import CipherDocument, SourceArtifact
from ..ir.nodes import CipherNode, SourceRef


def _node_from_value(value: Any, name: str | None, source: SourceRef) -> CipherNode:
    if isinstance(value, dict):
        return CipherNode(
            kind="term",
            name=name,
            children=[
                _node_from_value(child, key, source)
                for key, child in value.items()
            ],
            source=source,
        )

    if isinstance(value, list):
        return CipherNode(
            kind="list",
            name=name,
            children=[
                _node_from_value(child, None, source)
                for child in value
            ],
            source=source,
        )

    return CipherNode(
        kind="item",
        name=name,
        value=value,
        source=source,
    )


def load_json(path: str | Path) -> CipherDocument:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    source = SourceRef(language="json", path=str(p))

    if isinstance(data, dict):
        return CipherDocument(
            children=[
                _node_from_value(value, key, source)
                for key, value in data.items()
            ],
            sources=[
                SourceArtifact.from_path(
                    p,
                    "JSON",
                )
            ],
        )

    return CipherDocument(
        children=[_node_from_value(data, None, source)],
        sources=[
            SourceArtifact.from_path(
                p,
                "JSON",
            )
        ],
    )
