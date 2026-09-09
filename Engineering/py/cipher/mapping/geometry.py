from __future__ import annotations

from dataclasses import dataclass
import re

from qps.cipher.ir.document import CipherDocument
from qps.cipher.ir.nodes import CipherNode
from .dependencies import resolve_symbols


@dataclass(frozen=True)
class GeometryCapability:
    semantic_name: str
    implementation_symbol: str
    source_path: str
    source_line: int | None


# This table deliberately describes CE-OS meaning rather than
# reproducing the OCCT API hierarchy.
#
# More than one implementation symbol may map to one CE-OS capability.
_SYMBOL_CAPABILITIES = {
    "BRepPrimAPI_MakeCylinder": "construct.cylinder",
    "BRepAlgoAPI_Cut": "boolean.cut",
    "BRepAlgoAPI_Fuse": "boolean.fuse",
    "BRepAlgoAPI_Common": "boolean.common",
    "BRepCheck_Analyzer": "validate.brep",
    "BRepMesh_IncrementalMesh": "mesh.triangulate",
    "BRep_Tool::Triangulation": "mesh.extract_triangles",
    "TopExp_Explorer": "topology.explore",
    "TopoDS::Face": "topology.face",
    "ShapeType": "inspect.shape_kind",
    "Transformation": "transform.resolve",
    "Transform": "transform.apply",
    "NbNodes": "mesh.vertex_count",
    "Node": "mesh.vertex",
    "NbTriangles": "mesh.triangle_count",
    "Triangle": "mesh.triangle",
}


def _walk(node: CipherNode):
    yield node

    for child in node.children:
        yield from _walk(child)


def geometry_capabilities(
    document: CipherDocument,
) -> list[GeometryCapability]:
    found: dict[
        tuple[str, str, str, int | None],
        GeometryCapability,
    ] = {}

    # Resolve Python calls through their actual import provenance first.
    for resolved in resolve_symbols(document):
        symbol_tail = (
            resolved.implementation_symbol
            .replace("::", ".")
            .rsplit(".", 1)[-1]
        )

        semantic = _SYMBOL_CAPABILITIES.get(symbol_tail)

        if semantic is not None:
            capability = GeometryCapability(
                semantic_name=semantic,
                implementation_symbol=symbol_tail,
                source_path=resolved.source_path,
                source_line=resolved.source_line,
            )

            found[
                (
                    semantic,
                    symbol_tail,
                    resolved.source_path,
                    resolved.source_line,
                )
            ] = capability

    for root in document.children:
        for node in _walk(root):
            source_path = (
                node.source.path
                if node.source is not None
                else ""
            )

            source_line = (
                node.source.line
                if node.source is not None
                else None
            )

            # Mapped call nodes.
            if node.kind == "call" and node.name:
                for symbol, semantic in _SYMBOL_CAPABILITIES.items():
                    if node.name == symbol or node.name.endswith(
                        "::" + symbol
                    ):
                        capability = GeometryCapability(
                            semantic_name=semantic,
                            implementation_symbol=symbol,
                            source_path=source_path,
                            source_line=source_line,
                        )

                        found[
                            (
                                semantic,
                                symbol,
                                source_path,
                                source_line,
                            )
                        ] = capability

            # Raw C++ execution is retained as deferred evidence.
            # Use it to identify constructor/type APIs that a
            # lightweight structural parser may not classify as calls.
            if (
                node.kind == "raw_execution"
                and isinstance(node.value, str)
            ):
                for symbol, semantic in _SYMBOL_CAPABILITIES.items():
                    if re.search(
                        r"\b" + re.escape(symbol) + r"\b",
                        node.value,
                    ):
                        capability = GeometryCapability(
                            semantic_name=semantic,
                            implementation_symbol=symbol,
                            source_path=source_path,
                            source_line=source_line,
                        )

                        found[
                            (
                                semantic,
                                symbol,
                                source_path,
                                source_line,
                            )
                        ] = capability

    return sorted(
        found.values(),
        key=lambda item: (
            item.semantic_name,
            item.implementation_symbol,
            item.source_path,
            item.source_line or 0,
        ),
    )


def semantic_vocabulary(
    document: CipherDocument,
) -> list[str]:
    return sorted({
        capability.semantic_name
        for capability in geometry_capabilities(document)
    })
