from __future__ import annotations

from dataclasses import dataclass, field

from .ir.document import CipherDocument
from .ir.nodes import CipherNode
from .libs.dependency_role import (
    classify_dependency_role,
)


DependencyKey = tuple[
    str,
    str | None,
    str | None,
]

SUPPORTED_BINARY_EXPRESSIONS = {
    "add",
    "subtract",
    "multiply",
    "divide",
}

UNEMITTED_EXPRESSION_REASONS = {
    "augmented_assignment": "augmented assignments are not emitted",
    "boolean_expression": "boolean expressions are not emitted",
    "comparison": "comparisons are not emitted",
    "conditional_expression": "conditional expressions are not emitted",
    "interpolation": "interpolated strings are not emitted",
    "list_comprehension": "list comprehensions are not emitted",
    "list_expression": "list expressions are not emitted",
    "mapping_expression": "mapping expressions are not emitted",
    "raise": "raise statements are not emitted",
    "semantic_call": "semantic calls are not emitted",
    "subscript": "subscript expressions are not emitted",
    "tuple_expression": "tuple expressions are not emitted",
}


def dependency_key(
    dependency,
) -> DependencyKey:
    return (
        dependency.module
        or dependency.package
        or "",
        dependency.symbol,
        dependency.alias,
    )


@dataclass
class SupportReport:
    status: str = "ready"
    reasons: list[str] = field(
        default_factory=list
    )

    def partial(
        self,
        reason: str,
    ) -> None:
        if self.status == "ready":
            self.status = "partial"

        if reason not in self.reasons:
            self.reasons.append(reason)

    def block(
        self,
        reason: str,
    ) -> None:
        self.status = "blocked"

        if reason not in self.reasons:
            self.reasons.append(reason)


def _walk(
    node: CipherNode,
    report: SupportReport,
    resolved_dependencies: set[
        DependencyKey
    ],
) -> None:
    if node.kind == "definition":
        report.partial(
            "definition/object semantics are not emitted"
        )

    elif node.kind == "import":
        unresolved = []

        for dependency in node.dependencies:
            role = classify_dependency_role(
                dependency
            )

            if role.role == "source-only":
                continue

            if (
                dependency_key(dependency)
                in resolved_dependencies
            ):
                continue

            unresolved.append(
                dependency
            )

        if unresolved:
            report.partial(
                "foreign dependency remains unresolved"
            )

    elif node.kind == "expression_statement":
        report.partial(
            "expression statements are not emitted"
        )

    elif node.kind in UNEMITTED_EXPRESSION_REASONS:
        report.partial(
            UNEMITTED_EXPRESSION_REASONS[node.kind]
        )

    elif (
        node.kind == "expression"
        and node.name not in SUPPORTED_BINARY_EXPRESSIONS
    ):
        report.partial(
            f"{node.name or 'unknown'} expressions are not emitted"
        )

    elif node.kind == "call":
        if any(
            child.kind == "argument"
            and child.name is not None
            for child in node.children
        ):
            report.partial(
                "keyword call arguments are not emitted"
            )

    elif node.kind == "return":
        if (
            len(node.children) == 1
            and node.children[0].kind
            == "call"
            and any(
                child.kind == "argument"
                and child.name is not None
                for child in
                node.children[0].children
            )
        ):
            report.partial(
                "structured keyword-constructor "
                "return is not emitted"
            )

    for child in node.children:
        _walk(
            child,
            report,
            resolved_dependencies,
        )


def inspect_support(
    document: CipherDocument,
    *,
    resolved_dependencies: set[
        DependencyKey
    ] | None = None,
) -> SupportReport:
    report = SupportReport()

    resolved = (
        resolved_dependencies
        if resolved_dependencies is not None
        else set()
    )

    for child in document.children:
        _walk(
            child,
            report,
            resolved,
        )

    return report
