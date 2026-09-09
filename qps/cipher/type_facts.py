from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qps.cipher.ir.document import CipherDocument
from qps.cipher.ir.nodes import CipherNode


@dataclass
class LocalTypeFacts:
    function_returns: dict[str, str] = field(
        default_factory=dict
    )
    definition_fields: dict[
        str,
        dict[str, str],
    ] = field(
        default_factory=dict
    )


def explicit_type_facts(
    document: CipherDocument,
) -> LocalTypeFacts:
    facts = LocalTypeFacts()

    for node in document.children:
        if (
            node.kind == "function"
            and node.name
            and node.source_type
        ):
            facts.function_returns[
                node.name
            ] = node.source_type

        if not (
            node.kind == "definition"
            and node.name
        ):
            continue

        fields = {
            child.name: child.source_type
            for child in node.children
            if (
                child.kind in {
                    "item",
                    "assignment",
                }
                and child.name
                and child.source_type
            )
        }

        if fields:
            facts.definition_fields[
                node.name
            ] = fields

    return facts


def _walk(node: CipherNode):
    yield node

    for child in node.children:
        yield from _walk(child)


def _sequence_type(
    source_type: str | None,
) -> bool:
    if not source_type:
        return False

    compact = source_type.replace(
        " ",
        "",
    )

    return (
        compact == "list"
        or compact == "tuple"
        or compact.startswith("list[")
        or compact.startswith("tuple[")
    )


def enrich_explicit_local_types(
    document: CipherDocument,
    *,
    imported_function_returns: dict[
        str,
        str,
    ] | None = None,
    imported_definition_fields: dict[
        str,
        dict[str, str],
    ] | None = None,
) -> CipherDocument:
    function_returns = dict(
        imported_function_returns
        or {}
    )

    definition_fields = {
        name: dict(fields)
        for name, fields in (
            imported_definition_fields
            or {}
        ).items()
    }

    own = explicit_type_facts(document)

    function_returns.update(
        own.function_returns
    )
    definition_fields.update(
        own.definition_fields
    )

    for function in document.children:
        if function.kind != "function":
            continue

        bindings: dict[str, str] = {}

        # Explicit parameter annotations are authored source facts.
        for node in function.children:
            if (
                node.kind == "parameter"
                and node.name
                and node.source_type
            ):
                bindings[
                    node.name
                ] = node.source_type

        changed = True

        while changed:
            changed = False

            for node in _walk(function):
                if not (
                    node.kind == "assignment"
                    and node.name
                ):
                    continue

                if node.source_type:
                    if (
                        bindings.get(node.name)
                        != node.source_type
                    ):
                        bindings[
                            node.name
                        ] = node.source_type
                        changed = True
                    continue

                value = None

                if len(node.children) == 1:
                    candidate = node.children[0]

                    if (
                        candidate.kind == "call"
                        and candidate.name
                    ):
                        value = candidate

                if value is None:
                    continue

                inferred = (
                    function_returns.get(
                        value.name
                    )
                )

                if inferred:
                    if (
                        node.source_type
                        != inferred
                    ):
                        node.source_type = (
                            inferred
                        )
                        changed = True

                    if (
                        bindings.get(
                            node.name
                        ) != inferred
                    ):
                        bindings[
                            node.name
                        ] = inferred
                        changed = True

            for node in _walk(function):
                if not (
                    node.kind == "reference"
                    and node.name
                    and node.source_type is None
                ):
                    continue

                inferred = None

                if "." not in node.name:
                    inferred = bindings.get(
                        node.name
                    )
                else:
                    root, field_name = (
                        node.name.split(
                            ".",
                            1,
                        )
                    )

                    root_type = bindings.get(
                        root
                    )

                    if (
                        root_type
                        and root_type
                        in definition_fields
                    ):
                        inferred = (
                            definition_fields[
                                root_type
                            ].get(
                                field_name
                            )
                        )

                if inferred:
                    node.source_type = inferred
                    changed = True

            for node in _walk(function):
                if not (
                    node.kind == "call"
                    and node.name == "len"
                    and node.source_type is None
                    and len(node.children) == 1
                ):
                    continue

                argument = node.children[0]

                if not (
                    argument.kind == "argument"
                    and argument.name is None
                    and len(argument.children) == 1
                ):
                    continue

                value = argument.children[0]

                if (
                    value.kind == "reference"
                    and _sequence_type(
                        value.source_type
                    )
                ):
                    node.source_type = "int"
                    changed = True

    return document


def sequence_type(
    source_type: str | None,
) -> bool:
    return _sequence_type(source_type)
