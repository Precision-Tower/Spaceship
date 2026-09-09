from dataclasses import fields
from pathlib import Path

from qps.cipher.ir.source_facts import (
    DependencyFact,
    SourceDocumentFacts,
    SourceFact,
    SourceFactRef,
    project_source_facts,
)
from qps.cipher.sources.python_source import (
    load_python,
)


FORBIDDEN = {
    "state",
    "notes",
    "ready",
    "blockers",
    "foreign",
    "libraries",
    "candidate",
    "status",
    "detail",
    "semantic_identity",
}


def walk(node):
    yield node

    for child in node.children:
        yield from walk(child)


def field_names(model):
    return {
        field.name
        for field in fields(model)
    }


def main():
    source = Path(
        "Engineering/py/Physics/Domains/motion.py"
    )

    facts = project_source_facts(
        load_python(source)
    )

    assert isinstance(
        facts,
        SourceDocumentFacts,
    )

    assert not (
        field_names(SourceFact)
        & FORBIDDEN
    )

    assert not (
        field_names(SourceFactRef)
        & FORBIDDEN
    )

    assert not (
        field_names(DependencyFact)
        & FORBIDDEN
    )

    nodes = list(
        child
        for root in facts.children
        for child in walk(root)
    )

    imports = [
        node
        for node in facts.children
        if node.kind == "import"
    ]

    assert len(imports) == 2

    gravity = next(
        dependency
        for node in imports
        for dependency in node.dependencies
        if dependency.symbol
        == "GRAVITY_EARTH_M_S2"
    )

    equation_result = next(
        dependency
        for node in imports
        for dependency in node.dependencies
        if dependency.symbol
        == "EquationResult"
    )

    assert gravity.module == (
        "Engineering.py.Physics.constants"
    )

    assert equation_result.module == (
        "Engineering.py.Physics.equations"
    )

    function = next(
        node
        for node in facts.children
        if node.kind == "function"
        and node.name == "weight_force_n"
    )

    call = next(
        node
        for node in walk(function)
        if node.kind == "call"
        and node.name == "EquationResult"
    )

    arguments = [
        child
        for child in call.children
        if child.kind == "argument"
    ]

    assert [
        argument.name
        for argument in arguments
    ] == [
        "equation_id",
        "description",
        "inputs",
        "output_name",
        "output_value",
        "output_unit",
        "domain",
        "blocked_interpretations",
    ]

    assert any(
        node.kind == "mapping_expression"
        for node in nodes
    )

    assert any(
        node.kind == "list_expression"
        for node in nodes
    )

    print(
        "CIPHER_SOURCE_FACT_PROJECTION=PASS"
    )


if __name__ == "__main__":
    main()
