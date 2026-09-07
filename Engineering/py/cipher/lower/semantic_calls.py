from __future__ import annotations

from copy import deepcopy

from ..ir.document import CipherDocument
from ..ir.nodes import CipherNode, TranslationState
from ..mapping.dependencies import resolve_symbols
from ..mapping.geometry import geometry_capabilities


def _walk(node: CipherNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def lower_semantic_calls(
    document: CipherDocument,
) -> CipherDocument:
    """
    Lower implementation-specific calls into backend-neutral
    semantic calls.

    This pass does not emit QPS and does not alter function
    interfaces. It only replaces calls whose provenance and
    semantic identity are already proven by Cipher mappings.
    """
    lowered = deepcopy(document)

    resolved = resolve_symbols(lowered)
    capabilities = geometry_capabilities(lowered)

    semantic_by_source = {
        (
            capability.implementation_symbol,
            capability.source_path,
            capability.source_line,
        ): capability.semantic_name
        for capability in capabilities
    }

    call_semantics: dict[
        tuple[str, str, int | None],
        str,
    ] = {}

    for symbol in resolved:
        key = (
            symbol.implementation_symbol
            .replace("::", ".")
            .rsplit(".", 1)[-1],
            symbol.source_path,
            symbol.source_line,
        )

        semantic = semantic_by_source.get(key)

        if semantic is not None:
            call_semantics[
                (
                    symbol.call_name,
                    symbol.source_path,
                    symbol.source_line,
                )
            ] = semantic

    for root in lowered.children:
        for node in _walk(root):
            if node.kind != "call" or not node.name:
                continue

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

            semantic = call_semantics.get(
                (
                    node.name,
                    source_path,
                    source_line,
                )
            )

            if semantic is None:
                continue

            implementation = node.name

            node.kind = "semantic_call"
            node.name = semantic
            node.state = TranslationState.MAPPED

            note = (
                "Lowered implementation call "
                f"{implementation} -> {semantic}"
            )
            if note not in node.notes:
                node.notes.append(note)

    return lowered
