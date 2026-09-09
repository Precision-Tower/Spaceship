from __future__ import annotations

from copy import deepcopy

from qps.cipher.ir.document import CipherDocument
from qps.cipher.ir.nodes import CipherNode, TranslationState
from qps.cipher.mapping.dependencies import resolve_symbols


def _walk(node: CipherNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def lower_semantic_calls(
    document: CipherDocument,
    *,
    capability_provider=None,
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

    if capability_provider is None:
        capabilities = []
    else:
        capabilities = capability_provider(lowered)

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

    # A profile may describe a capability directly from source evidence
    # even when the source call does not originate from an import binding.
    # Keep that path generic: match the authored implementation symbol plus
    # truthful source location rather than assuming Python import structure.
    for capability in capabilities:
        implementation = (
            capability.implementation_symbol
            .replace("::", ".")
            .rsplit(".", 1)[-1]
        )

        call_semantics.setdefault(
            (
                implementation,
                capability.source_path,
                capability.source_line,
            ),
            capability.semantic_name,
        )

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
