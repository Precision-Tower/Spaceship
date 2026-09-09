from __future__ import annotations

import json

from qps.cipher.ir.document import CipherDocument
from .provenance_qps import emit_source_provenance
from qps.cipher.ir.nodes import CipherNode


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


def _expression_string_literal(value) -> str:
    return json.dumps(
        str(value),
        ensure_ascii=False,
    )


def _emit_interpolation(
    node: CipherNode,
) -> str:
    if node.kind != "interpolation":
        raise ValueError(
            "Interpolation emitter requires interpolation node."
        )

    parts = []

    for child in node.children:
        if child.kind == "literal":
            parts.append(
                _expression_string_literal(
                    child.value
                )
            )
            continue

        if (
            child.kind != "interpolation_value"
            or len(child.children) != 1
        ):
            raise ValueError(
                "Unsupported interpolation component."
            )

        metadata = (
            child.value
            if isinstance(child.value, dict)
            else {}
        )

        if (
            metadata.get("conversion", -1) != -1
            or metadata.get("format_spec") is not None
        ):
            raise ValueError(
                "Formatted interpolation conversion/spec "
                "is not emitted."
            )

        value = child.children[0]

        if (
            value.source_type not in {
                "str",
                "int",
                "float",
            }
        ):
            raise ValueError(
                "Interpolation value lacks proven "
                "STRING/NUMERIC source type."
            )

        parts.append(
            f"string({_emit_expression(value)})"
        )

    if not parts:
        return '""'

    return " + ".join(
        f"({part})"
        for part in parts
    )


def _source_type_is_sequence(
    source_type: str | None,
) -> bool:
    if source_type is None:
        return False

    compact = source_type.replace(" ", "")

    return (
        compact == "list"
        or compact == "tuple"
        or compact.startswith("list[")
        or compact.startswith("tuple[")
    )


def _emit_expression(node: CipherNode) -> str:
    if node.kind == "literal":
        if node.value is None:
            return "null"

        if node.value is True:
            return "true"

        if node.value is False:
            return "false"

        if isinstance(node.value, (int, float)):
            return str(node.value)

        return _expression_string_literal(
            node.value
        )

    if node.kind == "interpolation":
        return _emit_interpolation(
            node
        )

    if node.kind == "reference":
        if not node.name:
            raise ValueError("Reference expression is missing a name.")
        return node.name

    if node.kind == "subscript":
        if len(node.children) != 2:
            raise ValueError(
                "Subscript expression requires base and index."
            )

        base = node.children[0]
        index = node.children[1]

        if (
            base.kind != "reference"
            or not _source_type_is_sequence(
                base.source_type
            )
        ):
            raise ValueError(
                "Subscript base is not proven QPS SEQUENCE."
            )

        if index.kind == "Slice":
            raise ValueError(
                "Slice expressions are not emitted."
            )

        return (
            "sequence_at("
            f"value- {_emit_expression(base)}, "
            f"index- {_emit_expression(index)}"
            ")"
        )

    if node.kind == "boolean_expression":
        operators = {
            "and": "-and",
            "or": "-or",
        }

        operator = operators.get(node.name or "")

        if operator is None:
            raise ValueError(
                "Unsupported Cipher boolean operator: "
                f"{node.name}"
            )

        if len(node.children) < 2:
            raise ValueError(
                "Boolean expression requires at least two operands."
            )

        return (
            "("
            + f" {operator} ".join(
                _emit_expression(child)
                for child in node.children
            )
            + ")"
        )

    if node.kind == "comparison":
        if len(node.children) != 2:
            raise ValueError(
                "Comparison requires exactly two operands."
            )

        left = _emit_expression(
            node.children[0]
        )
        right = _emit_expression(
            node.children[1]
        )

        operator = node.name or ""

        if operator == "equal":
            return f"{left} == {right}"

        if operator == "not_equal":
            return f"-not ({left} == {right})"

        if operator == "less_than":
            return f"{left} < {right}"

        if operator == "less_than_or_equal":
            return f"-not ({right} < {left})"

        if operator == "greater_than":
            return f"{right} < {left}"

        if operator == "greater_than_or_equal":
            return f"-not ({left} < {right})"

        if operator in {"in", "not_in"}:
            membership = (
                f"contains({left}, {right})"
            )

            if operator == "in":
                return membership

            return f"-not ({membership})"

        if operator in {"is", "is_not"}:
            right_node = node.children[1]

            if (
                right_node.kind != "literal"
                or right_node.value not in (
                    None,
                    True,
                    False,
                )
            ):
                raise ValueError(
                    "Python identity comparison is only proven "
                    "for None/True/False."
                )

            equality = f"{left} == {right}"

            if operator == "is":
                return equality

            return f"-not ({equality})"

        raise ValueError(
            "Unsupported Cipher comparison operator: "
            f"{node.name}"
        )

    if (
        node.kind == "expression"
        and node.name == "negate"
    ):
        if len(node.children) != 1:
            raise ValueError(
                "negate expression requires one operand."
            )

        operand = _emit_expression(
            node.children[0]
        )

        return f"0 - ({operand})"

    if (
        node.kind == "expression"
        and node.name == "not"
    ):
        if len(node.children) != 1:
            raise ValueError(
                "not expression requires one operand."
            )

        operand = _emit_expression(
            node.children[0]
        )

        return f"-not ({operand})"

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

    if node.kind in {
        "list_expression",
        "tuple_expression",
        "set_expression",
    }:
        return (
            "sequence(" +
            ", ".join(
                _emit_expression(child)
                for child in node.children
            ) +
            ")"
        )

    if (
        node.kind == "call"
        and node.name == "len"
    ):
        if len(node.children) != 1:
            raise ValueError(
                "len(...) requires one argument."
            )

        argument = node.children[0]

        if (
            argument.kind != "argument"
            or argument.name is not None
            or len(argument.children) != 1
        ):
            raise ValueError(
                "len(...) requires one positional argument."
            )

        value = argument.children[0]

        if (
            value.kind != "reference"
            or not _source_type_is_sequence(
                value.source_type
            )
        ):
            raise ValueError(
                "len(...) argument is not proven QPS SEQUENCE."
            )

        return (
            "sequence_size("
            f"value- {_emit_expression(value)}"
            ")"
        )

    if node.kind == "call":
        if not node.name:
            raise ValueError("Call expression is missing a callee.")

        arguments = []

        for argument in node.children:
            if argument.kind != "argument":
                raise ValueError(
                    f"Unexpected call child kind: {argument.kind}"
                )

            if len(argument.children) != 1:
                raise ValueError(
                    "Call argument must contain one expression."
                )

            expression = _emit_expression(
                argument.children[0]
            )

            if argument.name is None:
                arguments.append(expression)
            else:
                arguments.append(
                    f"{argument.name}- {expression}"
                )

        return f"{node.name}({', '.join(arguments)})"

    raise ValueError(
        f"Unsupported Cipher expression node kind: {node.kind}"
    )



def _emit_mapping_term(
    name: str,
    node: CipherNode,
    indent: int = 0,
) -> str:
    if node.kind != "mapping_expression":
        raise ValueError(
            "Native mapping Term emission requires mapping_expression."
        )

    pad = " " * indent
    child_pad = " " * (indent + 4)
    lines = [
        f"{pad}{name}: ("
    ]

    for entry in node.children:
        if (
            entry.kind != "mapping_entry"
            or len(entry.children) != 2
        ):
            raise ValueError(
                "mapping_expression requires mapping_entry key/value children."
            )

        key_node, value_node = entry.children

        if (
            key_node.kind != "literal"
            or not isinstance(key_node.value, str)
        ):
            raise ValueError(
                "Native QPS mapping Term keys must be proven string literals."
            )

        key = key_node.value

        if value_node.kind == "mapping_expression":
            lines.append(
                _emit_mapping_term(
                    key,
                    value_node,
                    indent + 4,
                )
            )
            continue

        lines.append(
            f"{child_pad}{key}- "
            f"{_emit_expression(value_node)};"
        )

    lines.append(
        f"{pad});"
    )

    return "\n".join(lines)


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

        expression = node.children[0]

        if expression.kind == "mapping_expression":
            return _emit_mapping_term(
                node.name,
                expression,
                indent,
            )

        return (
            f"{pad}%{node.name}: "
            f"{_emit_expression(expression)}"
        )

    if node.kind == "if":
        condition_nodes = [
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
            len(condition_nodes) != 1
            or len(then_branches) != 1
            or len(else_branches) > 1
        ):
            raise ValueError(
                "Python if requires one condition, one then branch, "
                "and at most one else branch."
            )

        condition = condition_nodes[0]

        if len(condition.children) != 1:
            raise ValueError(
                "Python if condition requires one expression."
            )

        def emit_branch(
            branch: CipherNode,
            branch_indent: int,
        ) -> list[str]:
            lines = []

            for statement in branch.children:
                if statement.kind == "import":
                    # Dependency topology is emitted by the conversion plan,
                    # not as raw source import syntax.
                    continue

                emitted = _emit_statement(
                    statement,
                    branch_indent,
                )

                if emitted is None:
                    raise ValueError(
                        "Unsupported executable statement inside Python if: "
                        f"{statement.kind}"
                    )

                lines.append(emitted)

            return lines

        lines = [
            f"{pad}-if "
            f"{_emit_expression(condition.children[0])} {{"
        ]

        lines.extend(
            emit_branch(
                then_branches[0],
                indent + 4,
            )
        )
        lines.append(f"{pad}}}")

        if else_branches:
            lines.append(f"{pad}-else {{")
            lines.extend(
                emit_branch(
                    else_branches[0],
                    indent + 4,
                )
            )
            lines.append(f"{pad}}}")

        return "\n".join(lines)

    if node.kind == "raise":
        if (
            not node.name
            or len(node.children) != 1
        ):
            raise ValueError(
                "Only single-message Python exception raises "
                "have a proven QPS -raise equivalent."
            )

        message_node = node.children[0]

        if (
            message_node.kind == "literal"
            and isinstance(message_node.value, str)
        ):
            message = _expression_string_literal(
                message_node.value
            )
        else:
            message = _emit_expression(
                message_node
            )

        return (
            f"{pad}-raise {message};"
        )

    if node.kind == "return":
        if len(node.children) != 1:
            raise ValueError(
                "Return requires exactly one expression."
            )

        expression = node.children[0]

        if expression.kind == "call":
            prefix = []
            rewritten_arguments = []

            for argument in expression.children:
                if (
                    argument.kind != "argument"
                    or len(argument.children) != 1
                ):
                    raise ValueError(
                        "Call argument must contain one expression."
                    )

                value = argument.children[0]

                if (
                    argument.name is not None
                    and value.kind == "mapping_expression"
                ):
                    prefix.append(
                        _emit_mapping_term(
                            argument.name,
                            value,
                            indent,
                        )
                    )

                    rewritten_arguments.append(
                        f"{argument.name}- {argument.name}"
                    )
                    continue

                emitted = _emit_expression(value)

                if argument.name is None:
                    rewritten_arguments.append(emitted)
                else:
                    rewritten_arguments.append(
                        f"{argument.name}- {emitted}"
                    )

            if prefix:
                call = (
                    f"{expression.name}(" +
                    ", ".join(rewritten_arguments) +
                    ")"
                )

                return (
                    "\n".join(prefix)
                    + "\n"
                    + f"{pad}-return {call};"
                )

        return (
            f"{pad}-return "
            f"{_emit_expression(expression)};"
        )

    if node.kind == "expression_statement":
        if len(node.children) != 1:
            raise ValueError(
                "Expression statement requires one expression."
            )

        expression = node.children[0]

        if (
            expression.kind == "call"
            and expression.name
        ):
            if (
                expression.name.endswith(".append")
                and expression.name.count(".") == 1
                and len(expression.children) == 1
                and expression.children[0].kind == "argument"
                and expression.children[0].name is None
                and len(expression.children[0].children) == 1
            ):
                receiver, _ = expression.name.rsplit(".", 1)
                value = _emit_expression(
                    expression.children[0].children[0]
                )

                return (
                    f"{pad}append("
                    f"{receiver}, {value}"
                    f");"
                )

            if "." not in expression.name:
                return (
                    f"{pad}"
                    f"{_emit_expression(expression)};"
                )

        return None

    return None



def _emit_definition_constructor(
    node: CipherNode,
) -> str:
    if not node.name:
        raise ValueError(
            "Definition is missing a name."
        )

    fields = []
    defaulted = {}

    for child in node.children:
        if child.kind == "item":
            if not child.name:
                raise ValueError(
                    "Definition field is missing a name."
                )

            fields.append(child.name)
            continue

        if child.kind == "assignment":
            if (
                not child.name
                or len(child.children) != 1
            ):
                raise ValueError(
                    "Definition field assignment is malformed."
                )

            value = child.children[0]

            if (
                value.kind == "call"
                and value.name == "field"
                and len(value.children) == 1
            ):
                argument = value.children[0]

                if (
                    argument.kind == "argument"
                    and argument.name == "default_factory"
                    and len(argument.children) == 1
                    and argument.children[0].kind == "reference"
                    and argument.children[0].name == "list"
                ):
                    fields.append(child.name)
                    defaulted[child.name] = "sequence()"
                    continue

            raise ValueError(
                "Unsupported definition field default shape."
            )

        if child.kind in {
            "function",
            "documentation",
        }:
            continue

        raise ValueError(
            "Unsupported definition child kind: "
            f"{child.kind}"
        )

    if not fields:
        raise ValueError(
            "Definition constructor requires fields."
        )

    lines = [
        f"-func {node.name}("
    ]

    for field in fields:
        default = defaulted.get(field)

        if default is None:
            lines.append(
                f"{field}-;"
            )
        else:
            lines.append(
                f"{field}- {default};"
            )

    lines.append("){")
    lines.append(
        f"{node.name}: ("
    )

    for field in fields:
        lines.append(
            f"{field}- {field};"
        )

    lines.append(");")
    lines.append("")
    lines.append(
        f"-return {node.name};"
    )
    lines.append("}")

    return "\n".join(lines)


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


def _emit_structural_node(
    node: CipherNode,
    indent: int = 0,
) -> str:
    pad = " " * indent

    if node.kind == "item":
        # Anonymous Items are canonical children of structural list Terms.
        name = node.name if node.name is not None else "item"

        if node.value is None:
            return f"{pad}{name}- /n;"

        return f"{pad}{name}- {_scalar(node.value)};"

    if node.kind in {"term", "list"}:
        if not node.name:
            raise ValueError(
                f"{node.kind} structural node is missing a name."
            )

        lines = [
            f"{pad}{node.name}: ("
        ]

        for child in node.children:
            if child.kind not in {
                "item",
                "term",
                "list",
            }:
                raise ValueError(
                    "Unsupported structural child kind "
                    f"{child.kind} beneath {node.kind} {node.name}."
                )

            lines.append(
                _emit_structural_node(
                    child,
                    indent + 4,
                )
            )

        lines.append(
            f"{pad});"
        )

        return "\n".join(lines)

    raise ValueError(
        f"Unsupported structural node kind: {node.kind}"
    )


def _emit_node(node: CipherNode) -> str | None:
    if node.kind == "import":
        # Import relationships are resolved by the ConversionPlan and
        # projected dependency associations. Raw source import syntax
        # is not emitted directly as QPS source text here.
        return None

    if node.kind == "assignment":
        if not node.name or len(node.children) != 1:
            return None

        expression = node.children[0]

        if expression.kind == "mapping_expression":
            return _emit_mapping_term(
                node.name,
                expression,
            )

        if expression.kind not in {
            "list_expression",
            "call",
        }:
            return None

        return (
            f"{node.name}- "
            f"{_emit_expression(expression)};"
        )

    if node.kind in {
        "item",
        "term",
        "list",
    }:
        return _emit_structural_node(node)

    if node.kind == "documentation":
        return None

    if node.kind == "function":
        return _emit_function(node)

    if node.kind == "definition":
        return _emit_definition_constructor(
            node
        )

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
