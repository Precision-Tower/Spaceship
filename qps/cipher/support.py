from __future__ import annotations

from dataclasses import dataclass, field

from qps.cipher.ir.document import CipherDocument
from qps.cipher.ir.nodes import CipherNode, TranslationState
from qps.cipher.foreign.dependency_role import (
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

SUPPORTED_UNARY_EXPRESSIONS = {
    "not",
    "negate",
}

UNEMITTED_EXPRESSION_REASONS = {
    "augmented_assignment": "augmented assignments are not emitted",
    "conditional_expression": "conditional expressions are not emitted",
    "list_comprehension": "list comprehensions are not emitted",
    "semantic_call": "semantic calls are not emitted",
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
    if node.state == TranslationState.UNSUPPORTED:
        if node.kind == "comparison":
            report.partial(
                "comparison operator is not emitted"
            )
        else:
            report.partial(
                f"{node.kind} is not emitted"
            )

    if node.kind == "definition":
        pass

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

    elif node.kind == "if":
        conditions = [
            child
            for child in node.children
            if child.kind == "condition"
        ]
        then_branches = [
            child
            for child in node.children
            if (
                child.kind == "branch"
                and child.name == "then"
            )
        ]
        else_branches = [
            child
            for child in node.children
            if (
                child.kind == "branch"
                and child.name == "else"
            )
        ]

        if (
            len(conditions) != 1
            or len(conditions[0].children) != 1
            or len(then_branches) != 1
            or len(else_branches) > 1
        ):
            report.partial(
                "if statement shape is not emitted"
            )

    elif node.kind == "subscript":
        if len(node.children) != 2:
            report.partial(
                "subscript expression shape is not emitted"
            )
        else:
            base = node.children[0]
            index = node.children[1]

            source_type = (
                base.source_type.replace(" ", "")
                if base.source_type
                else ""
            )

            sequence_type = (
                source_type == "list"
                or source_type == "tuple"
                or source_type.startswith("list[")
                or source_type.startswith("tuple[")
            )

            if (
                base.kind != "reference"
                or not sequence_type
            ):
                report.partial(
                    "subscript base is not proven QPS SEQUENCE"
                )

            if index.kind == "Slice":
                report.partial(
                    "Slice expressions are not emitted"
                )

    elif node.kind == "raise":
        if (
            not node.name
            or len(node.children) != 1
        ):
            report.partial(
                "raise form is not emitted"
            )
        else:
            message = node.children[0]

            literal_string = (
                message.kind == "literal"
                and isinstance(message.value, str)
            )

            typed_string_reference = (
                message.kind == "reference"
                and message.source_type == "str"
            )

            if not (
                literal_string
                or typed_string_reference
            ):
                report.partial(
                    "raise message expression is not proven STRING"
                )

    elif node.kind == "interpolation":
        for part in node.children:
            if part.kind == "literal":
                continue

            if (
                part.kind != "interpolation_value"
                or len(part.children) != 1
            ):
                report.partial(
                    "interpolated strings contain unsupported components"
                )
                continue

            metadata = (
                part.value
                if isinstance(part.value, dict)
                else {}
            )

            if (
                metadata.get("conversion", -1) != -1
                or metadata.get("format_spec") is not None
            ):
                report.partial(
                    "formatted interpolation conversion/spec is not emitted"
                )
                continue

            value = part.children[0]

            if (
                value.source_type not in {
                    "str",
                    "int",
                    "float",
                }
            ):
                report.partial(
                    "interpolation value type is not proven STRING/NUMERIC"
                )

    elif (
        node.kind == "call"
        and node.name == "len"
    ):
        ready_len = False

        if len(node.children) == 1:
            argument = node.children[0]

            if (
                argument.kind == "argument"
                and argument.name is None
                and len(argument.children) == 1
            ):
                value = argument.children[0]

                if (
                    value.kind == "reference"
                    and value.source_type
                ):
                    compact = (
                        value.source_type.replace(
                            " ",
                            "",
                        )
                    )

                    ready_len = (
                        compact == "list"
                        or compact == "tuple"
                        or compact.startswith(
                            "list["
                        )
                        or compact.startswith(
                            "tuple["
                        )
                    )

        if not ready_len:
            report.partial(
                "len argument is not proven QPS SEQUENCE"
            )

    elif node.kind == "try":
        report.partial(
            "try/except control flow is not emitted"
        )

    elif node.kind == "expression_statement":
        ready_statement_call = False

        if len(node.children) == 1:
            expression = node.children[0]

            ready_statement_call = (
                expression.kind == "call"
                and bool(expression.name)
                and (
                    "." not in expression.name
                    or (
                        expression.name.endswith(".append")
                        and expression.name.count(".") == 1
                        and len(expression.children) == 1
                        and expression.children[0].kind == "argument"
                        and expression.children[0].name is None
                        and len(expression.children[0].children) == 1
                    )
                )
            )

        if not ready_statement_call:
            report.partial(
                "expression statements are not emitted"
            )

    elif node.kind in UNEMITTED_EXPRESSION_REASONS:
        report.partial(
            UNEMITTED_EXPRESSION_REASONS[node.kind]
        )

    elif (
        node.kind == "expression"
        and node.name not in (
            SUPPORTED_BINARY_EXPRESSIONS
            | SUPPORTED_UNARY_EXPRESSIONS
        )
    ):
        report.partial(
            f"{node.name or 'unknown'} expressions are not emitted"
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
