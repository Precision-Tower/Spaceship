from __future__ import annotations

import ast
from pathlib import Path

from .nodes import CipherNode, SourceRef, TranslationState


def _source(path: Path, node: ast.AST) -> SourceRef:
    return SourceRef(
        language="python",
        path=str(path),
        line=getattr(node, "lineno", None),
        column=getattr(node, "col_offset", None),
    )


def target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        base = target_name(node.value)
        if base is None:
            return node.attr
        return f"{base}.{node.attr}"

    if isinstance(node, ast.Subscript):
        base = target_name(node.value)
        if base is None:
            return None
        return f"{base}[...]"

    return None


def expression_node(
    path: Path,
    node: ast.AST,
) -> CipherNode:
    source = _source(path, node)

    if isinstance(node, ast.Constant):
        return CipherNode(
            kind="literal",
            value=node.value,
            source=source,
            state=TranslationState.DIRECT,
        )

    if isinstance(node, ast.Name):
        return CipherNode(
            kind="reference",
            name=node.id,
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Attribute):
        return CipherNode(
            kind="reference",
            name=target_name(node),
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.JoinedStr):
        children = []

        for part in node.values:
            if isinstance(part, ast.Constant):
                children.append(
                    CipherNode(
                        kind="literal",
                        value=part.value,
                        source=_source(path, part),
                        state=TranslationState.DIRECT,
                    )
                )
                continue

            if isinstance(part, ast.FormattedValue):
                children.append(
                    CipherNode(
                        kind="interpolation_value",
                        value={
                            "conversion": part.conversion,
                            "format_spec": (
                                ast.unparse(part.format_spec)
                                if part.format_spec is not None
                                else None
                            ),
                        },
                        children=[
                            expression_node(path, part.value)
                        ],
                        source=_source(path, part),
                        state=TranslationState.MAPPED,
                    )
                )
                continue

            children.append(
                CipherNode(
                    kind="expression",
                    name=type(part).__name__,
                    source=_source(path, part),
                    state=TranslationState.UNRESOLVED,
                    notes=[
                        f"Unsupported f-string component: {type(part).__name__}"
                    ],
                )
            )

        return CipherNode(
            kind="interpolation",
            children=children,
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Subscript):
        return CipherNode(
            kind="subscript",
            children=[
                expression_node(path, node.value),
                expression_node(path, node.slice),
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Compare):
        operators = {
            ast.Eq: "equal",
            ast.NotEq: "not_equal",
            ast.Lt: "less_than",
            ast.LtE: "less_than_or_equal",
            ast.Gt: "greater_than",
            ast.GtE: "greater_than_or_equal",
            ast.Is: "is",
            ast.IsNot: "is_not",
            ast.In: "in",
            ast.NotIn: "not_in",
        }

        children = [expression_node(path, node.left)]
        supported = True
        names = []

        for operator, comparator in zip(node.ops, node.comparators):
            name = operators.get(type(operator))

            if name is None:
                supported = False
                name = type(operator).__name__

            if isinstance(operator, (ast.Is, ast.IsNot)):
                if not (
                    isinstance(comparator, ast.Constant)
                    and comparator.value in (
                        None,
                        True,
                        False,
                    )
                ):
                    supported = False

            names.append(name)
            children.append(expression_node(path, comparator))

        return CipherNode(
            kind="comparison",
            name=",".join(names),
            children=children,
            source=source,
            state=(
                TranslationState.MAPPED
                if supported
                else TranslationState.UNSUPPORTED
            ),
        )

    if isinstance(node, ast.BoolOp):
        operators = {
            ast.And: "and",
            ast.Or: "or",
        }

        operation = operators.get(type(node.op))

        return CipherNode(
            kind="boolean_expression",
            name=operation or type(node.op).__name__,
            children=[
                expression_node(path, value)
                for value in node.values
            ],
            source=source,
            state=(
                TranslationState.MAPPED
                if operation is not None
                else TranslationState.UNSUPPORTED
            ),
        )

    if isinstance(node, ast.IfExp):
        return CipherNode(
            kind="conditional_expression",
            children=[
                CipherNode(
                    kind="condition",
                    children=[expression_node(path, node.test)],
                    source=_source(path, node.test),
                    state=TranslationState.MAPPED,
                ),
                CipherNode(
                    kind="branch",
                    name="then",
                    children=[expression_node(path, node.body)],
                    source=_source(path, node.body),
                    state=TranslationState.MAPPED,
                ),
                CipherNode(
                    kind="branch",
                    name="else",
                    children=[expression_node(path, node.orelse)],
                    source=_source(path, node.orelse),
                    state=TranslationState.MAPPED,
                ),
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.BinOp):
        operators = {
            ast.Add: "add",
            ast.Sub: "subtract",
            ast.Mult: "multiply",
            ast.Div: "divide",
            ast.FloorDiv: "floor_divide",
            ast.Mod: "modulo",
            ast.Pow: "power",
        }

        operation = operators.get(type(node.op))

        if operation is None:
            return CipherNode(
                kind="expression",
                name="binary",
                source=source,
                state=TranslationState.UNSUPPORTED,
                notes=[
                    f"Unsupported Python binary operator: {type(node.op).__name__}"
                ],
            )

        return CipherNode(
            kind="expression",
            name=operation,
            children=[
                expression_node(path, node.left),
                expression_node(path, node.right),
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.UnaryOp):
        operators = {
            ast.USub: "negate",
            ast.UAdd: "positive",
            ast.Not: "not",
        }

        operation = operators.get(type(node.op))

        if operation is None:
            return CipherNode(
                kind="expression",
                name="unary",
                source=source,
                state=TranslationState.UNSUPPORTED,
                notes=[
                    f"Unsupported Python unary operator: {type(node.op).__name__}"
                ],
            )

        return CipherNode(
            kind="expression",
            name=operation,
            children=[
                expression_node(path, node.operand)
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Call):
        callee = target_name(node.func)

        children: list[CipherNode] = []

        for argument in node.args:
            children.append(
                CipherNode(
                    kind="argument",
                    children=[
                        expression_node(path, argument)
                    ],
                    source=_source(path, argument),
                    state=TranslationState.MAPPED,
                )
            )

        for keyword in node.keywords:
            children.append(
                CipherNode(
                    kind="argument",
                    name=keyword.arg,
                    children=[
                        expression_node(path, keyword.value)
                    ],
                    source=_source(path, keyword.value),
                    state=TranslationState.MAPPED,
                )
            )

        return CipherNode(
            kind="call",
            name=callee,
            children=children,
            source=source,
            state=(
                TranslationState.MAPPED
                if callee is not None
                else TranslationState.UNRESOLVED
            ),
        )

    if isinstance(node, ast.ListComp):
        generators = []

        for generator in node.generators:
            target = target_name(generator.target)

            generator_children = [
                CipherNode(
                    kind="iterable",
                    children=[
                        expression_node(path, generator.iter)
                    ],
                    source=_source(path, generator.iter),
                    state=TranslationState.MAPPED,
                )
            ]

            for condition in generator.ifs:
                generator_children.append(
                    CipherNode(
                        kind="condition",
                        children=[
                            expression_node(path, condition)
                        ],
                        source=_source(path, condition),
                        state=TranslationState.MAPPED,
                    )
                )

            generators.append(
                CipherNode(
                    kind="comprehension_generator",
                    name=target,
                    children=generator_children,
                    source=_source(path, generator),
                    state=(
                        TranslationState.MAPPED
                        if target is not None
                        else TranslationState.UNRESOLVED
                    ),
                )
            )

        return CipherNode(
            kind="list_comprehension",
            children=[
                CipherNode(
                    kind="result_expression",
                    children=[
                        expression_node(path, node.elt)
                    ],
                    source=_source(path, node.elt),
                    state=TranslationState.MAPPED,
                ),
                *generators,
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Set):
        return CipherNode(
            kind="set_expression",
            children=[
                expression_node(path, child)
                for child in node.elts
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.List):
        return CipherNode(
            kind="list_expression",
            children=[
                expression_node(path, child)
                for child in node.elts
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Tuple):
        return CipherNode(
            kind="tuple_expression",
            children=[
                expression_node(path, child)
                for child in node.elts
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Dict):
        children: list[CipherNode] = []

        for key, value in zip(node.keys, node.values):
            key_node = (
                expression_node(path, key)
                if key is not None
                else CipherNode(
                    kind="literal",
                    value=None,
                    source=source,
                    state=TranslationState.UNRESOLVED,
                )
            )

            children.append(
                CipherNode(
                    kind="mapping_entry",
                    children=[
                        key_node,
                        expression_node(path, value),
                    ],
                    source=_source(path, value),
                    state=TranslationState.MAPPED,
                )
            )

        return CipherNode(
            kind="mapping_expression",
            children=children,
            source=source,
            state=TranslationState.MAPPED,
        )

    return CipherNode(
        kind="expression",
        name=type(node).__name__,
        source=source,
        state=TranslationState.UNRESOLVED,
        notes=[
            f"Python expression not yet normalized: {type(node).__name__}"
        ],
    )
