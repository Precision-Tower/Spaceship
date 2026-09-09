from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ImportBinding:
    module: str
    symbol: str | None
    alias: str | None
    level: int = 0

    @property
    def local_name(self) -> str:
        if self.alias:
            return self.alias
        if self.symbol:
            return self.symbol
        return self.module.rsplit(".", 1)[-1]


@dataclass
class SourceUnit:
    path: Path
    imports: list[ImportBinding] = field(default_factory=list)


@dataclass
class DependencyClosure:
    entry: Path
    units: dict[Path, SourceUnit] = field(default_factory=dict)
    external: set[ImportBinding] = field(default_factory=set)


def _imports(path: Path) -> list[ImportBinding]:
    tree = ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )

    result: list[ImportBinding] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for name in node.names:
                result.append(
                    ImportBinding(
                        module=name.name,
                        symbol=None,
                        alias=name.asname,
                    )
                )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for name in node.names:
                result.append(
                    ImportBinding(
                        module=module,
                        symbol=name.name,
                        alias=name.asname,
                        level=node.level,
                    )
                )

    return result


def _module_file(
    module: str,
    workspace_root: Path,
) -> Path | None:
    if not module:
        return None

    candidate = workspace_root.joinpath(
        *module.split(".")
    )

    source = candidate.with_suffix(".py")
    if source.is_file():
        return source.resolve()

    package = candidate / "__init__.py"
    if package.is_file():
        return package.resolve()

    return None


def _relative_module_file(
    source: Path,
    binding: ImportBinding,
) -> Path | None:
    if binding.level <= 0:
        return None

    base = source.parent

    # level=1 means current package; each additional dot
    # moves one package upward.
    for _ in range(binding.level - 1):
        base = base.parent

    if binding.module:
        candidate = base.joinpath(
            *binding.module.split(".")
        )
    else:
        candidate = base

    source_candidate = candidate.with_suffix(".py")
    if source_candidate.is_file():
        return source_candidate.resolve()

    package_candidate = candidate / "__init__.py"
    if package_candidate.is_file():
        return package_candidate.resolve()

    # "from . import foo" can identify a sibling module.
    if not binding.module and binding.symbol:
        sibling = base / f"{binding.symbol}.py"
        if sibling.is_file():
            return sibling.resolve()

    return None


def resolve_local_import(
    source: Path,
    binding: ImportBinding,
    workspace_root: Path,
) -> Path | None:
    if binding.level:
        resolved = _relative_module_file(
            source,
            binding,
        )
    else:
        resolved = _module_file(
            binding.module,
            workspace_root,
        )

    if resolved is None:
        return None

    try:
        resolved.relative_to(workspace_root)
    except ValueError:
        return None

    return resolved


def build_dependency_closure(
    entry: str | Path,
    workspace_root: str | Path,
) -> DependencyClosure:
    root = Path(workspace_root).resolve()
    entry_path = Path(entry).resolve()

    entry_path.relative_to(root)

    closure = DependencyClosure(entry=entry_path)
    pending = [entry_path]

    while pending:
        source = pending.pop()

        if source in closure.units:
            continue

        imports = _imports(source)
        closure.units[source] = SourceUnit(
            path=source,
            imports=imports,
        )

        for binding in imports:
            dependency = resolve_local_import(
                source,
                binding,
                root,
            )

            if dependency is None:
                closure.external.add(binding)
                continue

            if dependency not in closure.units:
                pending.append(dependency)

    return closure


def project_dependency_destinations(
    closure: DependencyClosure,
    entry_destination: str | Path,
) -> dict[Path, Path]:
    """Project a local closure around the exact entry destination.

    The requested destination owns the entry file identity. Every
    other local source is projected by its relative filesystem
    relationship to the entry source, preserving source topology
    without flattening or renaming the requested entry.
    """
    destination = Path(entry_destination)
    entry = closure.entry.resolve()

    unit_paths = [
        path.resolve()
        for path in closure.units
    ]

    if not unit_paths:
        return {}

    common_source_root = Path(
        __import__("os").path.commonpath(
            [str(path.parent) for path in unit_paths]
        )
    )

    entry_relative = entry.relative_to(
        common_source_root
    )

    # Map the source common root onto the destination tree by
    # aligning the entry source parent with the requested entry
    # destination parent. The filename itself must never move the
    # destination root upward.
    destination_root = destination.parent

    for _ in entry_relative.parent.parts:
        destination_root = destination_root.parent

    projected: dict[Path, Path] = {}

    for source in unit_paths:
        if source == entry:
            target = destination
        else:
            relative = source.relative_to(
                common_source_root
            )

            target = destination_root / relative

            if target.name == "__init__.py":
                target = target.with_name(
                    "_index.qps"
                )
            else:
                target = target.with_suffix(
                    ".qps"
                )

        projected[source] = target

    return projected
