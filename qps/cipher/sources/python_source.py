from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from qps.cipher.ir.document import CipherDocument, SourceArtifact
from qps.cipher.ir.nodes import (
    CipherNode,
    DependencyRef,
    SourceRef,
    TranslationState,
)
from qps.cipher.ir.expressions import (
    expression_node,
    target_name,
)


def _literal(node: ast.AST) -> tuple[Any, TranslationState]:
    try:
        return ast.literal_eval(node), TranslationState.DIRECT
    except Exception:
        return None, TranslationState.UNRESOLVED


def _source_type(node: ast.AST | None) -> str | None:
    if node is None:
        return None

    try:
        return ast.unparse(node)
    except Exception:
        return None


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
    # Collection syntax must remain visible to Cipher rather than being
    # collapsed through ast.literal_eval().
    #
    # Python lists have a proven canonical QPS translation to sequence(...).
    # Python mappings are preserved as mapping_expression IR, but remain an
    # explicit support blocker until their exact native QPS syntax equivalent
    # is proven.  Preserving syntax here does not authorize record(...).
    if isinstance(
        value_node,
        (ast.List, ast.Dict),
    ):
        expression = expression_node(
            path,
            value_node,
        )

        return CipherNode(
            kind="assignment",
            name=name,
            children=[
                expression
            ],
            source=_source(path, value_node),
            state=TranslationState.MAPPED,
            notes=[
                (
                    "Python collection syntax preserved as "
                    f"{expression.kind}."
                )
            ],
        )

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
            source_type=_source_type(node.annotation),
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
        exception_name = None

        if node.exc is not None:
            if (
                isinstance(node.exc, ast.Call)
                and isinstance(node.exc.func, ast.Name)
                and len(node.exc.args) == 1
                and not node.exc.keywords
            ):
                exception_name = node.exc.func.id
                children.append(
                    expression_node(
                        path,
                        node.exc.args[0],
                    )
                )
            else:
                children.append(
                    expression_node(
                        path,
                        node.exc,
                    )
                )

        return CipherNode(
            kind="raise",
            name=exception_name,
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

    if isinstance(node, ast.Try):
        children: list[CipherNode] = []

        try_body = CipherNode(
            kind="try_body",
            children=[
                _statement(
                    path,
                    statement,
                )
                for statement in node.body
            ],
            source=source,
            state=TranslationState.DEFERRED,
        )

        children.append(try_body)

        for handler in node.handlers:
            handler_children = [
                _statement(
                    path,
                    statement,
                )
                for statement in handler.body
            ]

            children.append(
                CipherNode(
                    kind="except_handler",
                    name=(
                        target_name(
                            handler.type
                        )
                        if handler.type
                        is not None
                        else None
                    ),
                    value=handler.name,
                    children=handler_children,
                    source=_source(
                        path,
                        handler,
                    ),
                    state=TranslationState.DEFERRED,
                    notes=[
                        "Python exception control flow preserved structurally; QPS emission is not yet authorized."
                    ],
                )
            )

        if node.orelse:
            children.append(
                CipherNode(
                    kind="try_else",
                    children=[
                        _statement(
                            path,
                            statement,
                        )
                        for statement in node.orelse
                    ],
                    source=source,
                    state=TranslationState.DEFERRED,
                )
            )

        if node.finalbody:
            children.append(
                CipherNode(
                    kind="try_finally",
                    children=[
                        _statement(
                            path,
                            statement,
                        )
                        for statement in node.finalbody
                    ],
                    source=source,
                    state=TranslationState.DEFERRED,
                )
            )

        return CipherNode(
            kind="try",
            children=children,
            source=source,
            state=TranslationState.DEFERRED,
            notes=[
                "Python try structure preserved in Cipher IR; QPS exception-control emission is not yet proven."
            ],
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


def _propagate_local_source_types(
    function: CipherNode,
    *,
    function_returns: dict[str, str] | None = None,
    definition_fields: dict[
        str,
        dict[str, str],
    ] | None = None,
) -> None:
    source_types: dict[str, str] = {}

    known_returns = (
        function_returns
        if function_returns is not None
        else {}
    )

    known_fields = (
        definition_fields
        if definition_fields is not None
        else {}
    )

    for child in function.children:
        if (
            child.kind == "parameter"
            and child.name
            and child.source_type
        ):
            source_types[child.name] = child.source_type

    execution = next(
        (
            child
            for child in function.children
            if child.kind == "execution"
        ),
        None,
    )

    if execution is None:
        return

    def collect(node: CipherNode) -> None:
        if (
            node.kind == "assignment"
            and node.name
        ):
            if node.source_type:
                source_types[
                    node.name
                ] = node.source_type

            elif len(node.children) == 1:
                value = node.children[0]

                if (
                    value.kind == "call"
                    and value.name
                    and value.name in known_returns
                ):
                    source_types[
                        node.name
                    ] = known_returns[
                        value.name
                    ]

                elif (
                    value.kind == "call"
                    and value.name
                    and value.name in known_fields
                ):
                    source_types[
                        node.name
                    ] = value.name

        for child in node.children:
            collect(child)

    collect(execution)

    def propagate(node: CipherNode) -> None:
        if (
            node.kind == "reference"
            and node.name
            and node.source_type is None
        ):
            if (
                "." not in node.name
                and node.name in source_types
            ):
                node.source_type = (
                    source_types[
                        node.name
                    ]
                )

            elif "." in node.name:
                root, field = (
                    node.name.split(
                        ".",
                        1,
                    )
                )

                root_type = (
                    source_types.get(
                        root
                    )
                )

                if (
                    root_type
                    and root_type in known_fields
                    and field in known_fields[
                        root_type
                    ]
                ):
                    node.source_type = (
                        known_fields[
                            root_type
                        ][field]
                    )

        for child in node.children:
            propagate(child)

    propagate(execution)


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

        parameter_children = []

        if index >= default_offset:
            default_node = node.args.defaults[index - default_offset]
            default, default_state = _literal(default_node)

            if default_state == TranslationState.UNRESOLVED:
                parameter_children.append(
                    CipherNode(
                        kind="default",
                        children=[
                            expression_node(path, default_node)
                        ],
                        source=_source(path, default_node),
                        state=TranslationState.MAPPED,
                    )
                )

        children.append(
            CipherNode(
                kind="parameter",
                name=arg.arg,
                value=default,
                source_type=_source_type(arg.annotation),
                children=parameter_children,
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
                source_type=_source_type(kwarg.annotation),
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

    function = CipherNode(
        kind="function",
        name=node.name,
        source_type=_source_type(node.returns),
        children=children,
        source=_source(path, node),
        state=TranslationState.MAPPED,
    )

    return function

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
                            source_type=_source_type(
                                child.annotation
                            ),
                            source=_source(path, child),
                            state=TranslationState.UNRESOLVED,
                            notes=[
                                "Annotated assignment has no value."
                            ],
                        )
                    )
                else:
                    field = _assignment(
                        path,
                        child.target.id,
                        child.value,
                    )
                    field.source_type = _source_type(
                        child.annotation
                    )
                    children.append(field)
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

    function_returns = {
        child.name: child.source_type
        for child in children
        if (
            child.kind == "function"
            and child.name
            and child.source_type
        )
    }

    definition_fields = {
        child.name: {
            field.name: field.source_type
            for field in child.children
            if (
                field.kind in {
                    "item",
                    "assignment",
                }
                and field.name
                and field.source_type
            )
        }
        for child in children
        if (
            child.kind == "definition"
            and child.name
        )
    }

    for child in children:
        if child.kind != "function":
            continue

        _propagate_local_source_types(
            child,
            function_returns=
                function_returns,
            definition_fields=
                definition_fields,
        )

    return CipherDocument(
        children=children,
        sources=[
            SourceArtifact.from_path(
                p,
                "Python",
            )
        ],
    )
