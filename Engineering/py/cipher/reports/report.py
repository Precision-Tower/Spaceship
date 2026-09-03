from __future__ import annotations

from collections import Counter

from ..ir.document import CipherDocument
from ..ir.nodes import CipherNode


def _walk(node: CipherNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def summarize(document: CipherDocument) -> dict[str, int]:
    counter = Counter()

    for root in document.children:
        for node in _walk(root):
            counter[node.state.value] += 1

    return dict(sorted(counter.items()))
