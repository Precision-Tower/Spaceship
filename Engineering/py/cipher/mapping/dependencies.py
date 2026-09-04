from __future__ import annotations

from dataclasses import dataclass

from ..ir.document import CipherDocument
from ..ir.nodes import CipherNode, DependencyRef


@dataclass(frozen=True)
class ResolvedSymbol:
    call_name: str
    implementation_symbol: str
    dependency: DependencyRef
    source_path: str
    source_line: int | None


def _walk(node: CipherNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def _imports(document: CipherDocument) -> dict[str, DependencyRef]:
    bindings: dict[str, DependencyRef] = {}

    for root in document.children:
        if root.kind != "import":
            continue

        for dependency in root.dependencies:
            if dependency.symbol:
                local_name = dependency.alias or dependency.symbol
            else:
                local_name = dependency.alias or dependency.module

            if local_name:
                bindings[local_name] = dependency

    return bindings


def resolve_symbols(
    document: CipherDocument,
) -> list[ResolvedSymbol]:
    bindings = _imports(document)
    found: list[ResolvedSymbol] = []

    for root in document.children:
        for node in _walk(root):
            if node.kind != "call" or not node.name:
                continue

            call_name = node.name
            dependency = bindings.get(call_name)

            if dependency is not None:
                implementation_symbol = (
                    dependency.symbol
                    or dependency.module
                    or dependency.package
                )

                found.append(
                    ResolvedSymbol(
                        call_name=call_name,
                        implementation_symbol=implementation_symbol,
                        dependency=dependency,
                        source_path=(
                            node.source.path
                            if node.source is not None
                            else ""
                        ),
                        source_line=(
                            node.source.line
                            if node.source is not None
                            else None
                        ),
                    )
                )
                continue

            head, separator, tail = call_name.partition(".")

            if not separator:
                continue

            dependency = bindings.get(head)

            if dependency is None:
                continue

            base = dependency.module or dependency.package

            found.append(
                ResolvedSymbol(
                    call_name=call_name,
                    implementation_symbol=f"{base}.{tail}",
                    dependency=dependency,
                    source_path=(
                        node.source.path
                        if node.source is not None
                        else ""
                    ),
                    source_line=(
                        node.source.line
                        if node.source is not None
                        else None
                    ),
                )
            )

    return found
