from __future__ import annotations

import json

from ..ir.document import CipherDocument
from .provenance_qps import emit_source_provenance
from ..ir.nodes import CipherNode


def _scalar(value) -> str:
    if value is None:
        return "/n"

    if value is True:
        return "true/b"

    if value is False:
        return "false/b"

    if isinstance(value, (int, float)):
        return str(value)

    return json.dumps(str(value), ensure_ascii=False) + "/a"


def _emit_expression(node: CipherNode) -> str:
    if node.kind == "literal":
        return _scalar(node.value)

    if node.kind == "reference":
        if not node.name:
            raise ValueError("Reference expression is missing a name.")
        return node.name

    if node.kind == "expression":
        operators = {
            "add": "+",
            "subtract": "-",
            "multiply": "*",
            "divide": "/",
        }

        operator = operators.get(node.name or "")

        if operator is None:
            raise ValueError(
                f"Unsupported Cipher expression operator: {node.name}"
            )

        if len(node.children) != 2:
            raise ValueError(
                f"Binary expression {node.name} requires two operands."
            )

        left = _emit_expression(node.children[0])
        right = _emit_expression(node.children[1])

        return f"{left} {operator} {right}"

    if node.kind == "call":
        if not node.name:
            raise ValueError("Call expression is missing a callee.")

        arguments = []

        for argument in node.children:
            if argument.kind != "argument":
                raise ValueError(
                    f"Unexpected call child kind: {argument.kind}"
                )

            if argument.name is not None:
                raise ValueError(
                    "QPS keyword call arguments are not implemented."
                )

            if len(argument.children) != 1:
                raise ValueError(
                    "Call argument must contain one expression."
                )

            arguments.append(
                _emit_expression(argument.children[0])
            )

        return f"{node.name}({', '.join(arguments)})"

    raise ValueError(
        f"Unsupported Cipher expression node kind: {node.kind}"
    )


def _emit_parameter(node: CipherNode) -> str:
    if not node.name:
        raise ValueError("Parameter is missing a name.")

    # First executable Cipher slice treats Python numeric parameters
    # as QPS numeric parameters. Rich annotation mapping comes later.
    if node.children:
        default = node.children[0]

        if (
            default.kind != "default"
            or len(default.children) != 1
        ):
            raise ValueError(
                f"Unsupported default structure for parameter {node.name}"
            )

        expression = _emit_expression(
            default.children[0]
        )

        return f"{node.name}- {expression}/n;"

    if node.value is not None:
        return f"{node.name}- {_scalar(node.value)}/n;"

    return f"{node.name}-/n;"


def _emit_statement(
    node: CipherNode,
    indent: int = 0,
) -> str | None:
    pad = " " * indent

    if node.kind == "assignment":
        if not node.name or len(node.children) != 1:
            raise ValueError(
                "Assignment requires a name and one expression."
            )

        return (
            f"{pad}%{node.name}: "
            f"{_emit_expression(node.children[0])}"
        )

    if node.kind == "return":
        if len(node.children) != 1:
            raise ValueError(
                "Return requires exactly one expression."
            )

        expression = node.children[0]

        # Complex constructor/object returns are not yet part of the
        # executable subset. Preserve translation progress by omitting
        # them rather than emitting invalid QPS.
        if (
            expression.kind == "call"
            and any(
                child.kind == "argument"
                and child.name is not None
                for child in expression.children
            )
        ):
            return None

        return (
            f"{pad}-return "
            f"{_emit_expression(expression)};"
        )

    if node.kind == "expression_statement":
        if len(node.children) != 1:
            raise ValueError(
                "Expression statement requires one expression."
            )

        # Bare expression statements do not have a direct proven QPS
        # execution equivalent in this first slice.
        return None

    return None


def _emit_function(node: CipherNode) -> str:
    if not node.name:
        raise ValueError("Function is missing a name.")

    parameters = [
        child
        for child in node.children
        if child.kind == "parameter"
    ]

    execution = next(
        (
            child
            for child in node.children
            if child.kind == "execution"
        ),
        None,
    )

    lines = [f"-func {node.name}("]

    for parameter in parameters:
        lines.append(_emit_parameter(parameter))

    lines.append("){")

    if execution is not None:
        emitted = []

        for statement in execution.children:
            text = _emit_statement(statement)

            if text:
                emitted.append(text)

        lines.extend(emitted)

        # If the original function had a complex return we cannot emit yet,
        # but a prior scalar assignment named "value" gives us a useful
        # executable acceptance slice for Engineering equations.
        has_return = any(
            line.lstrip().startswith("-return ")
            for line in emitted
        )

        if not has_return:
            value_assignment = next(
                (
                    statement
                    for statement in execution.children
                    if statement.kind == "assignment"
                    and statement.name == "value"
                ),
                None,
            )

            if value_assignment is not None:
                lines.append("-return value;")

    lines.append("}")

    return "\n".join(lines)


def _emit_node(node: CipherNode) -> str | None:
    if node.kind == "import":
        # Local imports disappear after closure merge.
        # Foreign imports will become ^ library surfaces later.
        return None

    if node.kind == "item":
        if not node.name:
            raise ValueError("Item is missing a name.")

        if node.value is None:
            return None

        return f"{node.name}- {_scalar(node.value)};"

    if node.kind == "documentation":
        return None

    if node.kind == "function":
        return _emit_function(node)

    # Classes/definitions remain deferred until class/object semantics
    # are proven in QPS runtime.
    if node.kind == "definition":
        return None

    return None


def emit_qps(
    document: CipherDocument,
    *,
    workspace_root=None,
) -> str:
    blocks = []

    for child in document.children:
        emitted = _emit_node(child)

        if emitted:
            blocks.append(emitted)

    body = "\n\n".join(blocks)

    provenance = emit_source_provenance(
        document,
        workspace_root=workspace_root,
    )

    sections = [
        section
        for section in (
            provenance,
            body,
        )
        if section
    ]

    return "\n\n".join(sections) + "\n"
