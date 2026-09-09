from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qps.cipher.ir.nodes import DependencyRef
from qps.cipher.foreign.indexed_lookup import _parse_surface


@dataclass(frozen=True)
class PlannedLibraryWrite:
    path: Path
    content: str
    kind: str


@dataclass
class LibraryPopulationPlan:
    dependency: DependencyRef
    writes: list[PlannedLibraryWrite] = field(
        default_factory=list
    )
    reused: list[Path] = field(
        default_factory=list
    )

    @property
    def changes_required(self) -> bool:
        return bool(self.writes)


def _module_parts(
    dependency: DependencyRef,
) -> list[str]:
    module = (
        dependency.module
        or dependency.package
        or ""
    )

    return [
        part
        for part in module.split(".")
        if part
    ]


def _index_identity(
    path: Path,
) -> str:
    name = path.parent.name or "Library"
    safe = "".join(
        character
        if character.isalnum() or character == "_"
        else "_"
        for character in name
    )

    return safe or "Library"


def _render_index(
    index_path: Path,
    surface: dict[str, str],
) -> str:
    identity = _index_identity(index_path)

    lines = [
        f"{identity}.",
        "",
        'purpose: def"',
        "Canonical Cipher-managed external library namespace.",
        '";',
        "",
        "scope: (",
        f'root- "{index_path.parent.as_posix()}";',
        'ownership- "immediate_children_only";',
        ");",
        "",
        "surface: (",
    ]

    for key in sorted(surface):
        lines.append(
            f'{key}- "{surface[key]}";'
        )

    lines.extend(
        [
            ");",
            "",
            "rules: (",
            'generated_by- "Cipher";',
            'ownership- "immediate_children_only";',
            ");",
            "",
        ]
    )

    return "\n".join(lines)


def plan_python_library_symbol(
    dependency: DependencyRef,
    workspace_root: str | Path,
    symbol_qps: str,
) -> LibraryPopulationPlan:
    root = Path(workspace_root).resolve()

    python_root = (
        root
        / "libs"
        / "Python"
    )

    root_index = python_root / "_index.qps"

    if not root_index.exists():
        raise RuntimeError(
            "Python library root is not indexed: "
            f"{root_index}"
        )

    symbol = dependency.symbol

    if not symbol:
        raise ValueError(
            "Library symbol population requires "
            "a canonical imported symbol."
        )

    if not symbol_qps.strip():
        raise ValueError(
            "Library symbol QPS candidate is empty."
        )

    plan = LibraryPopulationPlan(
        dependency=dependency
    )

    module_parts = _module_parts(dependency)

    current_dir = python_root
    current_index = root_index

    for part in module_parts:
        existing_surface = (
            _parse_surface(current_index)
            if current_index.exists()
            else {}
        )

        expected_relative = (
            f"{part}/_index.qps"
        )

        child_value = existing_surface.get(part)

        if child_value is not None:
            child_index = (
                current_dir / child_value
            ).resolve()

            if child_index.is_dir():
                child_index = (
                    child_index / "_index.qps"
                )

            if not child_index.exists():
                raise RuntimeError(
                    "Indexed library namespace target "
                    "does not exist: "
                    f"{child_index}"
                )

            plan.reused.append(
                child_index
            )

            current_dir = child_index.parent
            current_index = child_index
            continue

        # Parent index needs exactly one immediate child.
        updated_surface = dict(existing_surface)
        updated_surface[part] = expected_relative

        plan.writes.append(
            PlannedLibraryWrite(
                path=current_index,
                content=_render_index(
                    current_index,
                    updated_surface,
                ),
                kind="index-update",
            )
        )

        child_dir = current_dir / part
        child_index = child_dir / "_index.qps"

        plan.writes.append(
            PlannedLibraryWrite(
                path=child_index,
                content=_render_index(
                    child_index,
                    {},
                ),
                kind="index-create",
            )
        )

        current_dir = child_dir
        current_index = child_index

    # Resolve the effective final module index from any prior planned
    # write rather than requiring it to exist on disk.
    final_surface: dict[str, str] = {}

    planned_current = next(
        (
            write
            for write in reversed(plan.writes)
            if write.path == current_index
        ),
        None,
    )

    if planned_current is not None:
        # The freshly-created final module index is empty.
        final_surface = {}
    elif current_index.exists():
        final_surface = _parse_surface(
            current_index
        )

    existing_symbol = final_surface.get(symbol)

    if existing_symbol is not None:
        symbol_path = (
            current_dir / existing_symbol
        ).resolve()

        if not symbol_path.exists():
            raise RuntimeError(
                "Indexed library symbol target "
                "does not exist: "
                f"{symbol_path}"
            )

        plan.reused.append(symbol_path)
        return plan

    symbol_filename = f"{symbol}.qps"
    final_surface[symbol] = symbol_filename

    # Replace any planned creation of the final index with the
    # populated version, otherwise add an index update.
    replaced = False
    new_writes: list[PlannedLibraryWrite] = []

    for write in plan.writes:
        if write.path == current_index:
            new_writes.append(
                PlannedLibraryWrite(
                    path=current_index,
                    content=_render_index(
                        current_index,
                        final_surface,
                    ),
                    kind=write.kind,
                )
            )
            replaced = True
        else:
            new_writes.append(write)

    plan.writes = new_writes

    if not replaced:
        plan.writes.append(
            PlannedLibraryWrite(
                path=current_index,
                content=_render_index(
                    current_index,
                    final_surface,
                ),
                kind="index-update",
            )
        )

    plan.writes.append(
        PlannedLibraryWrite(
            path=current_dir / symbol_filename,
            content=symbol_qps,
            kind="symbol-create",
        )
    )

    # A population transaction carries one final candidate state per
    # filesystem path. During planning a newly-created namespace may
    # first receive an empty index and later receive its first child.
    # Collapse those intermediate states to the final authored file.
    normalized: dict[Path, PlannedLibraryWrite] = {}

    for write in plan.writes:
        previous = normalized.get(write.path)

        if previous is None:
            normalized[write.path] = write
            continue

        kind = (
            "index-create"
            if previous.kind == "index-create"
            else write.kind
        )

        normalized[write.path] = PlannedLibraryWrite(
            path=write.path,
            content=write.content,
            kind=kind,
        )

    plan.writes = list(normalized.values())

    return plan


def plan_python_library_capability(
    dependency: DependencyRef,
    workspace_root: Path,
    capability_members: tuple[str, ...],
    capability_qps: str,
) -> LibraryPopulationPlan:
    if not capability_members:
        raise ValueError("capability materialization requires an exact member identity")

    # The resolver owns the module/member split. Materialization receives that
    # exact split and must not reinterpret dotted member paths as modules.
    symbol = ".".join(capability_members)
    exact_dependency = DependencyRef(
        package=dependency.package,
        module=dependency.module,
        symbol=symbol,
        alias=dependency.alias,
        version=dependency.version,
        semantic_identity=dependency.semantic_identity,
        source=dependency.source,
    )
    return plan_python_library_symbol(
        exact_dependency,
        workspace_root,
        capability_qps,
    )


def merge_library_population_plans(
    plans: list[LibraryPopulationPlan],
) -> LibraryPopulationPlan:
    if not plans:
        raise ValueError("at least one library population plan is required")

    merged = LibraryPopulationPlan(dependency=plans[0].dependency)
    final_writes: dict[Path, PlannedLibraryWrite] = {}

    for plan in plans:
        merged.reused.extend(plan.reused)
        for write in plan.writes:
            path = write.path.resolve()
            previous = final_writes.get(path)
            if previous is None:
                final_writes[path] = write
                continue

            if previous.content == write.content:
                continue

            # Multiple independently planned capabilities can update the same
            # generated index. Merge only the immediate-child surface; never
            # choose one candidate over another.
            if (
                previous.kind.startswith("index-")
                and write.kind.startswith("index-")
            ):
                left = _parse_surface_text(previous.content)
                right = _parse_surface_text(write.content)
                combined = dict(left)
                for key, value in right.items():
                    existing = combined.get(key)
                    if existing is not None and existing != value:
                        raise RuntimeError(
                            f"conflicting indexed identity {key}: "
                            f"{existing} != {value}"
                        )
                    combined[key] = value
                kind = (
                    "index-create"
                    if previous.kind == "index-create"
                    or write.kind == "index-create"
                    else "index-update"
                )
                final_writes[path] = PlannedLibraryWrite(
                    path=previous.path,
                    content=_render_index(previous.path, combined),
                    kind=kind,
                )
                continue

            raise RuntimeError(
                f"conflicting capability materialization target: {path}"
            )

    merged.writes = list(final_writes.values())
    merged.reused = list(dict.fromkeys(merged.reused))
    return merged


def _parse_surface_text(content: str) -> dict[str, str]:
    import re

    match = re.search(
        r"(?ms)^surface:\s*\(\s*(.*?)^\);\s*$",
        content,
    )
    if match is None:
        return {}

    surface: dict[str, str] = {}
    for key, value in re.findall(
        r'(?m)^\s*([A-Za-z0-9_.]+)-\s*"([^"]+)";\s*$',
        match.group(1),
    ):
        surface[key] = value
    return surface
