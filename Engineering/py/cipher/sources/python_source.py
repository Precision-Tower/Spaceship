from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from ..ir.document import CipherDocument
from ..ir.nodes import (
    CipherNode,
    DependencyRef,
    SourceRef,
    TranslationState,
)
from ..ir.expressions import (
    expression_node,
    target_name,
)


def _literal(node: ast.AST) -> tuple[Any, TranslationState]:
    try:
        return ast.literal_eval(node), TranslationState.DIRECT
    except Exception:
        return None, TranslationState.UNRESOLVED


def _source(path: Path, node: ast.AST) -> SourceRef:
    return SourceRef(
        language="python",
        path=str(path),
        line=getattr(node, "lineno", None),
        column=getattr(node, "col_offset", None),
    )


def _assignment(
    path: Path,
    name: str,
    value_node: ast.AST,
) -> CipherNode:
    value, state = _literal(value_node)

    if state == TranslationState.DIRECT:
        return CipherNode(
            kind="item",
            name=name,
            value=value,
            source=_source(path, value_node),
            state=state,
        )

    return CipherNode(
        kind="assignment",
        name=name,
        children=[
            expression_node(path, value_node)
        ],
        source=_source(path, value_node),
        state=TranslationState.MAPPED,
        notes=[
            "Python assignment expression preserved structurally."
        ],
    )


def _statement(
    path: Path,
    node: ast.stmt,
) -> CipherNode:
    source = _source(path, node)

    if isinstance(node, ast.Assign):
        children: list[CipherNode] = []

        for target in node.targets:
            name = target_name(target)

            children.append(
                CipherNode(
                    kind="assignment",
                    name=name,
                    children=[
                        expression_node(path, node.value)
                    ],
                    source=source,
                    state=(
                        TranslationState.MAPPED
                        if name is not None
                        else TranslationState.UNRESOLVED
                    ),
                )
            )

        if len(children) == 1:
            return children[0]

        return CipherNode(
            kind="statement_group",
            children=children,
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.AnnAssign):
        name = target_name(node.target)

        children = []

        if node.value is not None:
            children.append(
                expression_node(path, node.value)
            )

        return CipherNode(
            kind="assignment",
            name=name,
            children=children,
            source=source,
            state=(
                TranslationState.MAPPED
                if name is not None
                else TranslationState.UNRESOLVED
            ),
        )

    if isinstance(node, ast.AugAssign):
        name = target_name(node.target)

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

        return CipherNode(
            kind="augmented_assignment",
            name=name,
            children=[
                CipherNode(
                    kind="expression",
                    name=operation or type(node.op).__name__,
                    children=[
                        CipherNode(
                            kind="reference",
                            name=name,
                            source=source,
                            state=TranslationState.MAPPED,
                        ),
                        expression_node(path, node.value),
                    ],
                    source=source,
                    state=(
                        TranslationState.MAPPED
                        if operation is not None
                        else TranslationState.UNSUPPORTED
                    ),
                )
            ],
            source=source,
            state=(
                TranslationState.MAPPED
                if name is not None and operation is not None
                else TranslationState.UNRESOLVED
            ),
        )

    if isinstance(node, ast.Raise):
        children = []

        if node.exc is not None:
            children.append(expression_node(path, node.exc))

        return CipherNode(
            kind="raise",
            children=children,
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, (ast.Import, ast.ImportFrom)):
        names = []
        dependencies = []

        module = (
            node.module
            if isinstance(node, ast.ImportFrom)
            else None
        )

        for alias in node.names:
            if module is None:
                package = alias.name.split(".", 1)[0]
                dependency_module = alias.name
                symbol = None
            else:
                package = module.split(".", 1)[0]
                dependency_module = module
                symbol = alias.name

            dependency = DependencyRef(
                package=package,
                module=dependency_module,
                symbol=symbol,
                alias=alias.asname,
                source=source,
            )

            dependencies.append(dependency)

            names.append(
                CipherNode(
                    kind="import_name",
                    name=alias.name,
                    value=alias.asname,
                    source=source,
                    state=TranslationState.DIRECT,
                    dependencies=[dependency],
                )
            )

        return CipherNode(
            kind="import",
            name=module,
            children=names,
            source=source,
            state=TranslationState.MAPPED,
            dependencies=dependencies,
        )

    if isinstance(node, ast.Return):
        children = []

        if node.value is not None:
            children.append(
                expression_node(path, node.value)
            )

        return CipherNode(
            kind="return",
            children=children,
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.Expr):
        return CipherNode(
            kind="expression_statement",
            children=[
                expression_node(path, node.value)
            ],
            source=source,
            state=TranslationState.MAPPED,
        )

    if isinstance(node, ast.If):
        children = [
            CipherNode(
                kind="condition",
                children=[
                    expression_node(path, node.test)
                ],
                source=_source(path, node.test),
                state=TranslationState.MAPPED,
            ),
            CipherNode(
                kind="branch",
                name="then",
                children=[
                    _statement(path, child)
                    for child in node.body
                ],
                source=source,
                state=TranslationState.MAPPED,
            ),
        ]

        if node.orelse:
            children.append(
                CipherNode(
                    kind="branch",
                    name="else",
                    children=[
                        _statement(path, child)
                        for child in node.orelse
                    ],
                    source=source,
                    state=TranslationState.MAPPED,
                )
            )

        return CipherNode(
            kind="if",
            children=children,
            source=source,
            state=TranslationState.MAPPED,
        )

    return CipherNode(
        kind="statement",
        name=type(node).__name__,
        source=source,
        state=TranslationState.UNRESOLVED,
        notes=[
            f"Python statement not yet normalized: {type(node).__name__}"
        ],
    )


def _function(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> CipherNode:
    children: list[CipherNode] = []

    positional = list(node.args.posonlyargs) + list(node.args.args)

    default_offset = len(positional) - len(node.args.defaults)

    for index, arg in enumerate(positional):
        default = None
        state = TranslationState.MAPPED

        if index >= default_offset:
            default_node = node.args.defaults[index - default_offset]
            default, default_state = _literal(default_node)

            if default_state == TranslationState.UNRESOLVED:
                state = TranslationState.UNRESOLVED

        children.append(
            CipherNode(
                kind="parameter",
                name=arg.arg,
                value=default,
                source=_source(path, arg),
                state=state,
            )
        )

    if node.args.vararg is not None:
        children.append(
            CipherNode(
                kind="parameter",
                name=f"*{node.args.vararg.arg}",
                source=_source(path, node.args.vararg),
                state=TranslationState.DEFERRED,
                notes=[
                    "Variadic positional parameter understood by Cipher; QPS execution emission deferred."
                ],
            )
        )

    for kwarg, default_node in zip(
        node.args.kwonlyargs,
        node.args.kw_defaults,
    ):
        default = None
        state = TranslationState.MAPPED

        if default_node is not None:
            default, default_state = _literal(default_node)

            if default_state == TranslationState.UNRESOLVED:
                state = TranslationState.UNRESOLVED

        children.append(
            CipherNode(
                kind="parameter",
                name=kwarg.arg,
                value=default,
                source=_source(path, kwarg),
                state=state,
            )
        )

    if node.args.kwarg is not None:
        children.append(
            CipherNode(
                kind="parameter",
                name=f"**{node.args.kwarg.arg}",
                source=_source(path, node.args.kwarg),
                state=TranslationState.DEFERRED,
                notes=[
                    "Variadic keyword parameter understood by Cipher; QPS execution emission deferred."
                ],
            )
        )

    docstring = ast.get_docstring(node)

    if docstring:
        children.append(
            CipherNode(
                kind="documentation",
                name="doc",
                value=docstring,
                source=_source(path, node),
                state=TranslationState.DIRECT,
            )
        )

    executable_children = []

    for statement in node.body:
        if (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            continue

        executable_children.append(
            _statement(path, statement)
        )

    children.append(
        CipherNode(
            kind="execution",
            name="body",
            children=executable_children,
            source=_source(path, node),
            state=TranslationState.DEFERRED,
            notes=[
                "Execution structure preserved in Cipher IR; QPS emission deferred until general execution grammar is stable."
            ],
        )
    )

    return CipherNode(
        kind="function",
        name=node.name,
        children=children,
        source=_source(path, node),
        state=TranslationState.MAPPED,
    )

def _class(
    path: Path,
    node: ast.ClassDef,
) -> CipherNode:
    children: list[CipherNode] = []

    docstring = ast.get_docstring(node)

    if docstring:
        children.append(
            CipherNode(
                kind="documentation",
                name="doc",
                value=docstring,
                source=_source(path, node),
            )
        )

    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            children.append(
                _function(path, child)
            )
            continue

        if isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    children.append(
                        _assignment(
                            path,
                            target.id,
                            child.value,
                        )
                    )
            continue

        if isinstance(child, ast.AnnAssign):
            if isinstance(child.target, ast.Name):
                if child.value is None:
                    children.append(
                        CipherNode(
                            kind="item",
                            name=child.target.id,
                            source=_source(path, child),
                            state=TranslationState.UNRESOLVED,
                            notes=[
                                "Annotated assignment has no value."
                            ],
                        )
                    )
                else:
                    children.append(
                        _assignment(
                            path,
                            child.target.id,
                            child.value,
                        )
                    )
            continue

    return CipherNode(
        kind="definition",
        name=node.name,
        children=children,
        source=_source(path, node),
        state=TranslationState.MAPPED,
    )


def load_python(path: str | Path) -> CipherDocument:
    p = Path(path)

    tree = ast.parse(
        p.read_text(encoding="utf-8"),
        filename=str(p),
    )

    children: list[CipherNode] = []

    module_docstring = ast.get_docstring(tree)

    if module_docstring:
        children.append(
            CipherNode(
                kind="documentation",
                name="module_doc",
                value=module_docstring,
                source=SourceRef(
                    language="python",
                    path=str(p),
                    line=1,
                    column=0,
                ),
            )
        )

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            children.append(_statement(p, node))
            continue

        if isinstance(node, ast.ClassDef):
            children.append(_class(p, node))
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            children.append(_function(p, node))
            continue

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    children.append(
                        _assignment(
                            p,
                            target.id,
                            node.value,
                        )
                    )
            continue

        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                if node.value is None:
                    children.append(
                        CipherNode(
                            kind="item",
                            name=node.target.id,
                            source=_source(p, node),
                            state=TranslationState.UNRESOLVED,
                            notes=[
                                "Annotated assignment has no value."
                            ],
                        )
                    )
                else:
                    children.append(
                        _assignment(
                            p,
                            node.target.id,
                            node.value,
                        )
                    )

    return CipherDocument(children=children)
