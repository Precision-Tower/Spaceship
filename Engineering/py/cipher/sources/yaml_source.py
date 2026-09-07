from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "PyYAML is required for YAML Cipher input."
    ) from exc

from ..ir.document import CipherDocument, SourceArtifact
from ..ir.nodes import CipherNode, SourceRef


def _node_from_value(value, name, source):
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


def load_yaml(path: str | Path) -> CipherDocument:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    source = SourceRef(language="yaml", path=str(p))

    if isinstance(data, dict):
        return CipherDocument(
            children=[
                _node_from_value(value, key, source)
                for key, value in data.items()
            ],
            sources=[
                SourceArtifact.from_path(
                    p,
                    "YAML",
                )
            ],
        )

    return CipherDocument(
        children=[_node_from_value(data, None, source)],
        sources=[
            SourceArtifact.from_path(
                p,
                "YAML",
            )
        ],
    )
