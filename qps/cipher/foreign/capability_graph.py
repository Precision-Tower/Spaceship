from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True, order=True)
class CapabilityIdentity:
    module: str
    members: tuple[str, ...] = ()

    @property
    def canonical(self) -> str:
        if not self.members:
            return self.module
        return ".".join((self.module, *self.members))


@dataclass(frozen=True)
class ImportNamespaceBinding:
    local_name: str
    module: str
    members: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityRequirement:
    identity: CapabilityIdentity
    source_line: int
    source_column: int


@dataclass
class CapabilityNode:
    identity: CapabilityIdentity
    first_tier: int
    requires: set[CapabilityIdentity] = field(default_factory=set)
    required_by: set[CapabilityIdentity] = field(default_factory=set)


@dataclass(frozen=True)
class TierEvidence:
    tier: int
    encountered: int
    new: int
    deduplicated: int
    catalog_hits: int = 0


@dataclass
class CapabilityGraph:
    roots: tuple[CapabilityIdentity, ...]
    nodes: dict[CapabilityIdentity, CapabilityNode]
    tiers: tuple[TierEvidence, ...]

    @property
    def depth(self) -> int:
        if not self.nodes:
            return 0
        return max(node.first_tier for node in self.nodes.values())


def _attribute_chain(node: ast.AST) -> tuple[str, tuple[str, ...]] | None:
    members: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        members.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    members.reverse()
    return current.id, tuple(members)


def import_namespace_bindings(tree: ast.AST) -> dict[str, ImportNamespaceBinding]:
    bindings: dict[str, ImportNamespaceBinding] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = tuple(alias.name.split("."))
                if alias.asname:
                    bindings[alias.asname] = ImportNamespaceBinding(
                        alias.asname, alias.name
                    )
                else:
                    bindings[parts[0]] = ImportNamespaceBinding(
                        parts[0], parts[0]
                    )
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                bindings[local] = ImportNamespaceBinding(
                    local,
                    node.module,
                    (alias.name,),
                )
    return bindings

def discover_used_capabilities(source: str) -> tuple[CapabilityRequirement, ...]:
    tree = ast.parse(source)
    requirements: dict[CapabilityIdentity, CapabilityRequirement] = {}

    class UsageVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scopes: list[dict[str, ImportNamespaceBinding | None]] = [{}]
            self.global_scopes: list[set[str]] = [set()]
            self.nonlocal_scopes: list[set[str]] = [set()]

        def lookup(self, name: str) -> ImportNamespaceBinding | None:
            if len(self.scopes) > 1 and name in self.global_scopes[-1]:
                return self.scopes[0].get(name)
            for scope in reversed(self.scopes):
                if name in scope:
                    return scope[name]
            return None

        def bind_import(self, name: str, binding: ImportNamespaceBinding) -> None:
            self.scopes[-1][name] = binding

        def shadow(self, name: str) -> None:
            self.scopes[-1][name] = None

        def record(self, identity: CapabilityIdentity, node: ast.AST) -> None:
            requirements.setdefault(
                identity,
                CapabilityRequirement(
                    identity,
                    getattr(node, "lineno", 0),
                    getattr(node, "col_offset", 0),
                ),
            )

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                if alias.asname:
                    local = alias.asname
                    module = alias.name
                else:
                    local = alias.name.split(".", 1)[0]
                    module = local
                self.bind_import(
                    local,
                    ImportNamespaceBinding(local, module),
                )

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.level or not node.module:
                return
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                self.bind_import(
                    local,
                    ImportNamespaceBinding(
                        local,
                        node.module,
                        (alias.name,),
                    ),
                )

        def _function_declarations(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> tuple[set[str], set[str], set[str]]:
            assigned: set[str] = set()
            globals_: set[str] = set()
            nonlocals: set[str] = set()

            class DeclarationVisitor(ast.NodeVisitor):
                def _target(self, target: ast.AST) -> None:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)
                    elif isinstance(target, (ast.Tuple, ast.List)):
                        for item in target.elts:
                            self._target(item)

                def visit_Global(self, current: ast.Global) -> None:
                    globals_.update(current.names)

                def visit_Nonlocal(self, current: ast.Nonlocal) -> None:
                    nonlocals.update(current.names)

                def visit_Assign(self, current: ast.Assign) -> None:
                    for target in current.targets:
                        self._target(target)
                    self.visit(current.value)

                def visit_AnnAssign(self, current: ast.AnnAssign) -> None:
                    self._target(current.target)
                    if current.value is not None:
                        self.visit(current.value)

                def visit_AugAssign(self, current: ast.AugAssign) -> None:
                    self._target(current.target)
                    self.visit(current.value)

                def visit_For(self, current: ast.For) -> None:
                    self._target(current.target)
                    self.visit(current.iter)
                    for statement in current.body + current.orelse:
                        self.visit(statement)

                visit_AsyncFor = visit_For

                def visit_With(self, current: ast.With) -> None:
                    for item in current.items:
                        self.visit(item.context_expr)
                        if item.optional_vars is not None:
                            self._target(item.optional_vars)
                    for statement in current.body:
                        self.visit(statement)

                visit_AsyncWith = visit_With

                def visit_Import(self, current: ast.Import) -> None:
                    for alias in current.names:
                        assigned.add(alias.asname or alias.name.split(".", 1)[0])

                def visit_ImportFrom(self, current: ast.ImportFrom) -> None:
                    for alias in current.names:
                        if alias.name != "*":
                            assigned.add(alias.asname or alias.name)

                def visit_FunctionDef(self, current: ast.FunctionDef) -> None:
                    if current is node:
                        for statement in current.body:
                            self.visit(statement)
                    else:
                        assigned.add(current.name)

                visit_AsyncFunctionDef = visit_FunctionDef

                def visit_ClassDef(self, current: ast.ClassDef) -> None:
                    assigned.add(current.name)

                def visit_Lambda(self, current: ast.Lambda) -> None:
                    return

                def visit_ListComp(self, current: ast.ListComp) -> None:
                    return

                visit_SetComp = visit_ListComp
                visit_GeneratorExp = visit_ListComp

                def visit_DictComp(self, current: ast.DictComp) -> None:
                    return

            DeclarationVisitor().visit(node)
            assigned.difference_update(globals_)
            assigned.difference_update(nonlocals)
            return assigned, globals_, nonlocals

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.shadow(node.name)

            # Defaults/decorators execute in the enclosing scope.
            for decorator in node.decorator_list:
                self.visit(decorator)
            for default in node.args.defaults:
                self.visit(default)
            for default in node.args.kw_defaults:
                if default is not None:
                    self.visit(default)

            assigned, globals_, nonlocals = self._function_declarations(node)
            self.scopes.append({})
            self.global_scopes.append(set(globals_))
            self.nonlocal_scopes.append(set(nonlocals))
            for local in assigned:
                self.shadow(local)
            for argument in (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            ):
                self.shadow(argument.arg)
            if node.args.vararg:
                self.shadow(node.args.vararg.arg)
            if node.args.kwarg:
                self.shadow(node.args.kwarg.arg)
            for statement in node.body:
                self.visit(statement)
            self.scopes.pop()
            self.global_scopes.pop()
            self.nonlocal_scopes.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Global(self, node: ast.Global) -> None:
            return

        def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
            return

        def visit_Lambda(self, node: ast.Lambda) -> None:
            for default in node.args.defaults:
                self.visit(default)
            for default in node.args.kw_defaults:
                if default is not None:
                    self.visit(default)
            self.scopes.append({})
            self.global_scopes.append(set())
            self.nonlocal_scopes.append(set())
            for argument in (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            ):
                self.shadow(argument.arg)
            if node.args.vararg:
                self.shadow(node.args.vararg.arg)
            if node.args.kwarg:
                self.shadow(node.args.kwarg.arg)
            self.visit(node.body)
            self.scopes.pop()
            self.global_scopes.pop()
            self.nonlocal_scopes.pop()

        def _visit_comprehension(self, node: ast.AST) -> None:
            generators = node.generators
            self.scopes.append({})
            self.global_scopes.append(set())
            self.nonlocal_scopes.append(set())
            for generator in generators:
                self.visit(generator.iter)
                self._shadow_target(generator.target)
                for condition in generator.ifs:
                    self.visit(condition)
            if isinstance(node, ast.DictComp):
                self.visit(node.key)
                self.visit(node.value)
            else:
                self.visit(node.elt)
            self.scopes.pop()
            self.global_scopes.pop()
            self.nonlocal_scopes.pop()

        visit_ListComp = _visit_comprehension
        visit_SetComp = _visit_comprehension
        visit_GeneratorExp = _visit_comprehension
        visit_DictComp = _visit_comprehension

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.shadow(node.name)
            for decorator in node.decorator_list:
                self.visit(decorator)
            for base in node.bases:
                self.visit(base)
            for keyword in node.keywords:
                self.visit(keyword.value)
            self.scopes.append({})
            self.global_scopes.append(set())
            self.nonlocal_scopes.append(set())
            for statement in node.body:
                self.visit(statement)
            self.scopes.pop()
            self.global_scopes.pop()
            self.nonlocal_scopes.pop()

        def _shadow_target(self, node: ast.AST) -> None:
            if isinstance(node, ast.Name):
                self.shadow(node.id)
            elif isinstance(node, (ast.Tuple, ast.List)):
                for item in node.elts:
                    self._shadow_target(item)

        def visit_Assign(self, node: ast.Assign) -> None:
            self.visit(node.value)
            for target in node.targets:
                self._shadow_target(target)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if node.value is not None:
                self.visit(node.value)
            self._shadow_target(node.target)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            self.visit(node.target)
            self.visit(node.value)
            self._shadow_target(node.target)

        def visit_For(self, node: ast.For) -> None:
            self.visit(node.iter)
            self._shadow_target(node.target)
            for statement in node.body:
                self.visit(statement)
            for statement in node.orelse:
                self.visit(statement)

        visit_AsyncFor = visit_For

        def visit_With(self, node: ast.With) -> None:
            for item in node.items:
                self.visit(item.context_expr)
                if item.optional_vars is not None:
                    self._shadow_target(item.optional_vars)
            for statement in node.body:
                self.visit(statement)

        visit_AsyncWith = visit_With

        def visit_Attribute(self, node: ast.Attribute) -> None:
            chain = _attribute_chain(node)
            if chain is not None:
                local, members = chain
                binding = self.lookup(local)
                if binding is not None:
                    self.record(
                        CapabilityIdentity(
                            binding.module,
                            binding.members + members,
                        ),
                        node,
                    )
                    # One outermost canonical capability is sufficient.
                    return
            self.generic_visit(node)

        def visit_Name(self, node: ast.Name) -> None:
            if not isinstance(node.ctx, ast.Load):
                return
            binding = self.lookup(node.id)
            if binding is not None:
                self.record(
                    CapabilityIdentity(
                        binding.module,
                        binding.members,
                    ),
                    node,
                )

    UsageVisitor().visit(tree)
    return tuple(
        sorted(
            requirements.values(),
            key=lambda item: item.identity.canonical,
        )
    )

def discover_file_capabilities(path: Path) -> tuple[CapabilityRequirement, ...]:
    return discover_used_capabilities(path.read_text())


RequirementExpander = Callable[
    [CapabilityIdentity], Iterable[CapabilityIdentity]
]
ClosureProofLookup = Callable[
    [CapabilityIdentity], Iterable[CapabilityIdentity] | None
]


def build_capability_graph(
    roots: Iterable[CapabilityIdentity],
    expand: RequirementExpander,
    closure_lookup: ClosureProofLookup | None = None,
) -> CapabilityGraph:
    root_tuple = tuple(dict.fromkeys(roots))
    nodes: dict[CapabilityIdentity, CapabilityNode] = {
        identity: CapabilityNode(identity, 1)
        for identity in root_tuple
    }
    frontier = list(root_tuple)
    tier = 1
    evidence: list[TierEvidence] = []

    while frontier:
        next_frontier: list[CapabilityIdentity] = []
        encountered = 0
        new_count = 0
        deduplicated = 0
        catalog_hits = 0

        for parent_identity in frontier:
            parent = nodes[parent_identity]
            catalog_requirements = (
                closure_lookup(parent_identity)
                if closure_lookup is not None
                else None
            )
            if catalog_requirements is not None:
                catalog_hits += 1
                children = catalog_requirements
            else:
                children = expand(parent_identity)

            for child_identity in dict.fromkeys(children):
                encountered += 1
                parent.requires.add(child_identity)
                existing = nodes.get(child_identity)
                if existing is None:
                    existing = CapabilityNode(child_identity, tier + 1)
                    nodes[child_identity] = existing
                    next_frontier.append(child_identity)
                    new_count += 1
                else:
                    deduplicated += 1
                existing.required_by.add(parent_identity)

        evidence.append(
            TierEvidence(
                tier=tier,
                encountered=encountered,
                new=new_count,
                deduplicated=deduplicated,
                catalog_hits=catalog_hits,
            )
        )
        if not next_frontier:
            break
        frontier = next_frontier
        tier += 1

    return CapabilityGraph(root_tuple, nodes, tuple(evidence))


@dataclass(frozen=True)
class PythonCapabilitySource:
    identity: CapabilityIdentity
    module: str
    source: Path
    definition_kind: str
    definition_name: str
    line: int
    requirements: tuple[CapabilityIdentity, ...]
    dynamic: tuple[str, ...] = ()
    conditional: tuple[str, ...] = ()


def _definition_for_member(
    tree: ast.Module,
    member: str,
) -> ast.AST | None:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == member:
                return node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
            )
            for target in targets:
                if isinstance(target, ast.Name) and target.id == member:
                    return node
    return None


def _module_defined_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for current in tree.body:
        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            names.add(current.name)
        elif isinstance(current, (ast.Assign, ast.AnnAssign)):
            targets = (
                current.targets
                if isinstance(current, ast.Assign)
                else [current.target]
            )
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _function_local_names(node: ast.AST) -> set[str]:
    names: set[str] = set()

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for argument in (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        ):
            names.add(argument.arg)
        if node.args.vararg:
            names.add(node.args.vararg.arg)
        if node.args.kwarg:
            names.add(node.args.kwarg.arg)

    class LocalVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, current: ast.FunctionDef) -> None:
            if current is node:
                for statement in current.body:
                    self.visit(statement)
            else:
                names.add(current.name)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, current: ast.ClassDef) -> None:
            if current is node:
                for statement in current.body:
                    self.visit(statement)
            else:
                names.add(current.name)

        def visit_Import(self, current: ast.Import) -> None:
            for alias in current.names:
                names.add(alias.asname or alias.name.split(".", 1)[0])

        def visit_ImportFrom(self, current: ast.ImportFrom) -> None:
            for alias in current.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)

        def _target(self, target: ast.AST) -> None:
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for item in target.elts:
                    self._target(item)

        def visit_Assign(self, current: ast.Assign) -> None:
            for target in current.targets:
                self._target(target)
            self.visit(current.value)

        def visit_AnnAssign(self, current: ast.AnnAssign) -> None:
            self._target(current.target)
            if current.value is not None:
                self.visit(current.value)

        def visit_For(self, current: ast.For) -> None:
            self._target(current.target)
            self.visit(current.iter)
            for statement in current.body + current.orelse:
                self.visit(statement)

        visit_AsyncFor = visit_For

    LocalVisitor().visit(node)
    return names


def _source_segment_capabilities(
    tree: ast.Module,
    node: ast.AST,
    module: str | None = None,
) -> tuple[CapabilityIdentity, ...]:
    bindings = import_namespace_bindings(tree)

    module_names = _module_defined_names(tree)
    local_names = _function_local_names(node)

    # A module import binding remains a valid provider inside a selected
    # function even though the imported name is lexically local only when
    # that function itself binds it. _function_local_names includes imports
    # found in the selected function; those must shadow module imports, while
    # ordinary module-level import bindings remain available.
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(node):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    local_import_nodes: dict[str, ImportNamespaceBinding] = {}
    for current in ast.walk(node):
        if isinstance(current, ast.Import):
            for alias in current.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                module_name = alias.name if alias.asname else local
                local_import_nodes[local] = ImportNamespaceBinding(
                    local, module_name
                )
        elif (
            isinstance(current, ast.ImportFrom)
            and current.level == 0
            and current.module
        ):
            for alias in current.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                local_import_nodes[local] = ImportNamespaceBinding(
                    local, current.module, (alias.name,)
                )

    identities: set[CapabilityIdentity] = set()
    for current in ast.walk(node):
        if isinstance(current, ast.Attribute):
            parent = parents.get(current)
            if isinstance(parent, ast.Attribute) and parent.value is current:
                continue
            chain = _attribute_chain(current)
            if chain is None:
                continue
            local, members = chain
            binding = local_import_nodes.get(local)
            if binding is None and local not in local_names:
                binding = bindings.get(local)
            if binding is not None:
                identities.add(
                    CapabilityIdentity(
                        binding.module,
                        binding.members + members,
                    )
                )
                continue

            if (
                module
                and local in module_names
                and local not in local_names
            ):
                identities.add(
                    CapabilityIdentity(module, (local,))
                )

        elif isinstance(current, ast.Name):
            if not isinstance(current.ctx, ast.Load):
                continue
            parent = parents.get(current)
            if isinstance(parent, ast.Attribute) and parent.value is current:
                continue

            binding = local_import_nodes.get(current.id)
            if binding is None and current.id not in local_names:
                binding = bindings.get(current.id)
            if binding is not None:
                identities.add(
                    CapabilityIdentity(binding.module, binding.members)
                )
                continue

            if (
                module
                and current.id in module_names
                and current.id not in local_names
            ):
                identities.add(
                    CapabilityIdentity(module, (current.id,))
                )

    return tuple(sorted(identities, key=lambda item: item.canonical))

def _resolve_reexport(
    tree: ast.Module,
    identity: CapabilityIdentity,
) -> CapabilityIdentity | None:
    if not identity.members:
        return None

    wanted = identity.members[0]

    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level:
            package_parts = identity.module.split(".")
            ascend = node.level - 1
            if ascend > len(package_parts):
                continue
            base_parts = (
                package_parts[:len(package_parts) - ascend]
                if ascend
                else package_parts
            )
            if node.module:
                base_parts = [*base_parts, *node.module.split(".")]
            provider_module = ".".join(base_parts)
        else:
            if not node.module:
                continue
            provider_module = node.module

        if not provider_module:
            continue

        for alias in node.names:
            if alias.name == "*":
                continue
            bound = alias.asname or alias.name
            if bound != wanted:
                continue
            return CapabilityIdentity(
                provider_module,
                (alias.name, *identity.members[1:]),
            )

    return None


def resolve_python_capability_source(
    identity: CapabilityIdentity,
    source: Path,
) -> PythonCapabilitySource | None:
    text = source.read_text()
    tree = ast.parse(text)

    if not identity.members:
        return None

    # The source module owns the first capability member. Remaining members
    # are attributes on the selected value/class and require deeper semantic
    # resolution before they can be narrowed safely.
    definition_name = identity.members[0]
    node = _definition_for_member(tree, definition_name)
    if node is None:
        reexport = _resolve_reexport(tree, identity)
        if reexport is None:
            return None
        return PythonCapabilitySource(
            identity=identity,
            module=identity.module,
            source=source,
            definition_kind="reexport",
            definition_name=definition_name,
            line=0,
            requirements=(reexport,),
        )

    kind = type(node).__name__
    requirements = _source_segment_capabilities(tree, node, identity.module)

    dynamic: list[str] = []
    conditional: list[str] = []
    for current in ast.walk(node):
        if isinstance(current, ast.If):
            conditional.append(
                f"if@{getattr(current, 'lineno', 0)}"
            )
        elif isinstance(current, ast.Try):
            conditional.append(
                f"try@{getattr(current, 'lineno', 0)}"
            )

        if isinstance(current, ast.Call):
            if isinstance(current.func, ast.Name) and current.func.id in {
                "getattr", "setattr", "delattr", "__import__",
            }:
                dynamic.append(
                    f"{current.func.id}@{getattr(current, 'lineno', 0)}"
                )
            elif (
                isinstance(current.func, ast.Attribute)
                and current.func.attr == "import_module"
            ):
                dynamic.append(
                    f"import_module@{getattr(current, 'lineno', 0)}"
                )

    return PythonCapabilitySource(
        identity=identity,
        module=identity.module,
        source=source,
        definition_kind=kind,
        definition_name=definition_name,
        line=getattr(node, "lineno", 0),
        requirements=requirements,
        dynamic=tuple(dynamic),
        conditional=tuple(conditional),
    )


@dataclass(frozen=True)
class CapabilityDisposition:
    identity: CapabilityIdentity
    state: str
    detail: str = ""


@dataclass
class CollapseResult:
    dispositions: dict[CapabilityIdentity, CapabilityDisposition]
    blockers: dict[CapabilityIdentity, tuple[CapabilityIdentity, ...]]

    @property
    def ready(self) -> bool:
        return not self.blockers

    def causal_blockers(
        self,
        identity: CapabilityIdentity,
    ) -> tuple[CapabilityIdentity, ...]:
        """Return terminal causal blockers reachable from identity."""
        terminal: set[CapabilityIdentity] = set()
        visiting: set[CapabilityIdentity] = set()

        def walk(current: CapabilityIdentity) -> None:
            if current in visiting:
                terminal.add(current)
                return
            children = self.blockers.get(current)
            if children is None:
                return
            if not children:
                terminal.add(current)
                return
            visiting.add(current)
            for child in children:
                walk(child)
            visiting.remove(current)

        walk(identity)
        return tuple(
            sorted(terminal, key=lambda item: item.canonical)
        )


LeafResolver = Callable[[CapabilityIdentity], CapabilityDisposition]


def collapse_capability_graph(
    graph: CapabilityGraph,
    resolve_leaf: LeafResolver,
) -> CollapseResult:
    dispositions: dict[CapabilityIdentity, CapabilityDisposition] = {}
    blockers: dict[CapabilityIdentity, tuple[CapabilityIdentity, ...]] = {}

    ordered = sorted(
        graph.nodes.values(),
        key=lambda node: (-node.first_tier, node.identity.canonical),
    )

    # Repeatedly settle nodes whose children are already settled. Cycles that
    # cannot be independently proven remain explicit blockers.
    pending = {node.identity: node for node in ordered}

    progressed = True
    while pending and progressed:
        progressed = False
        for identity in sorted(
            tuple(pending), key=lambda item: item.canonical
        ):
            node = pending[identity]
            unresolved_children = [
                child for child in node.requires
                if child in pending
            ]
            if unresolved_children:
                continue

            failed_children = [
                child for child in node.requires
                if child in blockers
            ]
            if failed_children:
                blockers[identity] = tuple(
                    sorted(failed_children, key=lambda item: item.canonical)
                )
                dispositions[identity] = CapabilityDisposition(
                    identity,
                    "blocked",
                    "required capability blocked",
                )
            else:
                disposition = resolve_leaf(identity)
                dispositions[identity] = disposition
                if disposition.state == "blocked":
                    blockers[identity] = ()
            del pending[identity]
            progressed = True

    for identity in sorted(pending, key=lambda item: item.canonical):
        dispositions[identity] = CapabilityDisposition(
            identity,
            "blocked",
            "cyclic capability group lacks independent proof",
        )
        blockers[identity] = tuple(
            sorted(
                (
                    child for child in pending[identity].requires
                    if child in pending
                ),
                key=lambda item: item.canonical,
            )
        )

    return CollapseResult(dispositions, blockers)


@dataclass(frozen=True)
class CapabilityUsageDiscovery:
    requirements: tuple[CapabilityRequirement, ...]
    blockers: tuple[str, ...] = ()


def discover_capability_usage(source: str) -> CapabilityUsageDiscovery:
    tree = ast.parse(source)
    requirements = discover_used_capabilities(source)
    identities = {item.identity for item in requirements}
    suppressed: set[CapabilityIdentity] = set()
    blockers: set[str] = set()

    bindings = import_namespace_bindings(tree)

    # Parent relationships let us distinguish a bounded member access from
    # an unbounded namespace escape. Import statements themselves do not
    # contain load-context Name nodes, so they need no special suppression.
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    for current in ast.walk(tree):
        if not isinstance(current, ast.Name):
            continue
        if not isinstance(current.ctx, ast.Load):
            continue

        binding = bindings.get(current.id)
        if binding is None:
            continue

        parent = parents.get(current)

        # name.foo is statically bounded and is already canonicalized by
        # discover_used_capabilities.
        if (
            isinstance(parent, ast.Attribute)
            and parent.value is current
        ):
            continue

        # getattr(name, member) is classified below because a constant member
        # can narrow exactly while a runtime-selected member must block.
        if (
            isinstance(parent, ast.Call)
            and isinstance(parent.func, ast.Name)
            and parent.func.id == "getattr"
            and parent.args
            and parent.args[0] is current
        ):
            continue

        identity = CapabilityIdentity(
            binding.module,
            binding.members,
        )

        # `from module import object` binds an exact capability identity.
        # Passing/storing that object bare does not widen its dependency
        # surface. A bare module namespace from `import module` remains
        # unbounded and must block.
        if binding.members:
            identities.add(identity)
            continue

        suppressed.add(identity)
        identities.discard(identity)
        blockers.add(
            "bound namespace escapes static capability surface"
            f"@{getattr(current, 'lineno', 0)}"
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any(alias.name == "*" for alias in node.names):
                blockers.add(
                    f"unbounded star import@{getattr(node, 'lineno', 0)}"
                )

        if not isinstance(node, ast.Call):
            continue

        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
        ):
            target = node.args[0]
            member = node.args[1]

            if isinstance(target, ast.Name):
                binding = bindings.get(target.id)
                if binding is not None:
                    suppressed.add(
                        CapabilityIdentity(
                            binding.module,
                            binding.members,
                        )
                    )
                    if (
                        isinstance(member, ast.Constant)
                        and isinstance(member.value, str)
                        and member.value.isidentifier()
                    ):
                        identities.add(
                            CapabilityIdentity(
                                binding.module,
                                binding.members + (member.value,),
                            )
                        )
                    else:
                        blockers.add(
                            "dynamic getattr on bound namespace"
                            f"@{getattr(node, 'lineno', 0)}"
                        )

        dynamic_import = False
        argument: ast.AST | None = None

        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
        ):
            dynamic_import = True
            argument = node.args[0] if node.args else None
        elif (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
        ):
            chain = _attribute_chain(node.func)
            if chain is not None and chain[0] == "importlib":
                dynamic_import = True
                argument = node.args[0] if node.args else None

        if dynamic_import and not (
            isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value
        ):
            blockers.add(
                f"dynamic import identity@{getattr(node, 'lineno', 0)}"
            )

    identities.difference_update(suppressed)
    existing = {
        item.identity: item
        for item in requirements
        if item.identity not in suppressed
    }
    for identity in identities:
        existing.setdefault(
            identity,
            CapabilityRequirement(identity, 0, 0),
        )

    return CapabilityUsageDiscovery(
        requirements=tuple(
            sorted(existing.values(), key=lambda item: item.identity.canonical)
        ),
        blockers=tuple(sorted(blockers)),
    )
