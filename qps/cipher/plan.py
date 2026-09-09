from __future__ import annotations

from dataclasses import dataclass, field
import os
import subprocess
import tempfile
from pathlib import Path

from qps.cipher.graph.dependency_closure import (
    build_dependency_closure,
    project_dependency_destinations,
    resolve_local_import,
)
from qps.cipher.support import (
    dependency_key,
    inspect_support,
)
from qps.cipher.foreign.dependency_role import (
    classify_dependency_role,
)
from qps.cipher.foreign.indexed_native_binding import (
    resolve_indexed_native_binding,
)


@dataclass(frozen=True)
class PlannedUnit:
    source: Path
    destination: Path
    status: str
    detail: str = ""
    candidate: str | None = None


def _qps_executable() -> Path:
    configured = os.environ.get(
        "QPS_EXECUTABLE"
    )

    if configured:
        path = Path(configured).resolve()

        if path.exists():
            return path

    candidate = (
        Path.cwd()
        / "qps/cpp/build-pixel/qps"
    ).resolve()

    if candidate.exists():
        return candidate

    raise RuntimeError(
        "QPS executable not found; set QPS_EXECUTABLE"
    )


def _validate_candidate_qps(
    candidate: str,
) -> None:
    qps = _qps_executable()

    tmp_root = os.environ.get("TMPDIR")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".qps",
        prefix="ceos-cipher-test.",
        dir=tmp_root,
        encoding="utf-8",
        delete=False,
    ) as handle:
        staged = Path(handle.name)
        handle.write(candidate)

    try:
        result = subprocess.run(
            [
                str(qps),
                str(staged),
                "--check",
            ],
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or "QPS validation failed"
            )

            raise RuntimeError(detail)

    finally:
        try:
            staged.unlink()
        except FileNotFoundError:
            pass


@dataclass
class ConversionPlan:
    source: Path
    destination: Path | None
    units: list[PlannedUnit] = field(default_factory=list)
    foreign: list[str] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.blockers and all(
            unit.status == "ready"
            for unit in self.units
        )


def _destination_for_file(
    source: Path,
    destination: Path | None,
) -> Path:
    if destination is None:
        return source.with_suffix(".qps")
    return destination


def _destination_for_directory(
    source_root: Path,
    destination_root: Path | None,
    source: Path,
) -> Path:
    if destination_root is None:
        return source.with_suffix(".qps")

    relative = source.relative_to(source_root)
    return (destination_root / relative).with_suffix(".qps")


def _local_closure_type_facts(
    closure,
    closure_root: Path,
):
    from qps.cipher.cipher import (
        prepare_document,
    )
    from qps.cipher.graph.dependency_closure import (
        resolve_local_import,
    )
    from qps.cipher.type_facts import (
        explicit_type_facts,
    )

    provider_facts = {}

    for provider in closure.units:
        provider_document = (
            prepare_document(
                provider
            )
        )

        provider_facts[
            provider
        ] = explicit_type_facts(
            provider_document
        )

    result = {}

    for source, unit in closure.units.items():
        function_returns = {}
        definition_fields = {}

        for dependency in unit.imports:
            provider = resolve_local_import(
                source,
                dependency,
                closure_root,
            )

            if (
                provider is None
                or provider not in provider_facts
                or not dependency.symbol
            ):
                continue

            facts = provider_facts[
                provider
            ]

            local_name = (
                dependency.local_name
            )

            if (
                dependency.symbol
                in facts.function_returns
            ):
                return_type = (
                    facts.function_returns[
                        dependency.symbol
                    ]
                )

                function_returns[
                    local_name
                ] = return_type

                # A locally imported function may explicitly return a
                # definition owned by the same provider module. Preserve that
                # authored definition field surface with the return identity;
                # the consumer does not need a redundant class import.
                if (
                    return_type
                    in facts.definition_fields
                ):
                    definition_fields[
                        return_type
                    ] = dict(
                        facts.definition_fields[
                            return_type
                        ]
                    )

            if (
                dependency.symbol
                in facts.definition_fields
            ):
                definition_fields[
                    local_name
                ] = dict(
                    facts.definition_fields[
                        dependency.symbol
                    ]
                )

        result[source] = (
            function_returns,
            definition_fields,
        )

    return result



def _inspect_unit_with_type_facts(
    source: Path,
    destination: Path,
    *,
    workspace_root: Path | None = None,
    resolved_dependencies=None,
    imported_function_returns=None,
    imported_definition_fields=None,
) -> PlannedUnit:
    """Call the current inspection boundary without breaking narrow test doubles.

    Production _inspect_unit owns the explicit imported type-fact parameters.
    Older focused tests replace _inspect_unit with a deliberately smaller
    callable to observe topology/projection behavior. Those doubles are not
    type-fact consumers and must not become an accidental API authority.
    """
    import inspect

    parameters = inspect.signature(
        _inspect_unit
    ).parameters

    kwargs = {
        "workspace_root": workspace_root,
        "resolved_dependencies":
            resolved_dependencies,
    }

    if (
        "imported_function_returns"
        in parameters
    ):
        kwargs[
            "imported_function_returns"
        ] = imported_function_returns

    if (
        "imported_definition_fields"
        in parameters
    ):
        kwargs[
            "imported_definition_fields"
        ] = imported_definition_fields

    return _inspect_unit(
        source,
        destination,
        **kwargs,
    )


def _inspect_unit(
    source: Path,
    destination: Path,
    *,
    workspace_root: Path | None = None,
    resolved_dependencies=None,
    imported_function_returns=None,
    imported_definition_fields=None,
) -> PlannedUnit:
    # Lazy import avoids cipher.py -> plan.py -> cipher.py
    # initialization recursion.
    from qps.cipher.cipher import (
        emit_prepared_document,
        prepare_document,
    )
    if destination.exists():
        return PlannedUnit(
            source=source,
            destination=destination,
            status="blocked",
            detail="destination exists",
        )

    try:
        # Prepare once. Support inspection and candidate emission
        # must consume this exact lowered document.
        document = prepare_document(
            source
        )

        if source.suffix.lower() == ".py":
            from qps.cipher.type_facts import (
                enrich_explicit_local_types,
            )

            enrich_explicit_local_types(
                document,
                imported_function_returns=(
                    imported_function_returns
                    or {}
                ),
                imported_definition_fields=(
                    imported_definition_fields
                    or {}
                ),
            )

        support = inspect_support(
            document,
            resolved_dependencies=(
                resolved_dependencies
                or set()
            ),
        )

    except Exception as exc:
        return PlannedUnit(
            source=source,
            destination=destination,
            status="blocked",
            detail=str(exc),
        )

    if support.status != "ready":
        return PlannedUnit(
            source=source,
            destination=destination,
            status=support.status,
            detail="; ".join(support.reasons),
        )

    candidate = None

    try:
        # Emit only after the exact prepared document passes support.
        candidate = emit_prepared_document(
            document,
            workspace_root=workspace_root,
        )

        _validate_candidate_qps(
            candidate
        )
    except Exception as exc:
        return PlannedUnit(
            source=source,
            destination=destination,
            status="blocked",
            detail=(
                "generated QPS failed validation: "
                f"{exc}"
            ),
            candidate=candidate,
        )

    return PlannedUnit(
        source=source,
        destination=destination,
        status="ready",
        candidate=candidate,
    )


def build_conversion_plan(
    source: str | Path,
    destination: str | Path | None = None,
    *,
    workspace_root: str | Path | None = None,
) -> ConversionPlan:
    # These helpers live in cipher.py today, but importing them only
    # when planning executes keeps module initialization acyclic.
    from qps.cipher.cipher import directory_sources, is_supported
    source = Path(source).resolve()
    destination = (
        Path(destination).resolve()
        if destination is not None
        else None
    )

    plan = ConversionPlan(
        source=source,
        destination=destination,
    )

    if not source.exists():
        plan.blockers.append(
            f"source does not exist: {source}"
        )
        return plan

    if source.is_file():
        if not is_supported(source):
            plan.blockers.append(
                f"unsupported source type: {source.suffix}"
            )
            return plan

        target = _destination_for_file(
            source,
            destination,
        )

        if target.exists() and target.is_dir():
            plan.blockers.append(
                f"file destination is a directory: {target}"
            )
            return plan

        if source.suffix.lower() == ".py":
            root = (
                Path(workspace_root).resolve()
                if workspace_root is not None
                else Path.cwd().resolve()
            )

            closure_root = (
                root
                if source.is_relative_to(root)
                else source.parent
            )

            try:
                closure = build_dependency_closure(
                    source,
                    closure_root,
                )

                local_type_facts = (
                    _local_closure_type_facts(
                        closure,
                        closure_root,
                    )
                )

                projection = (
                    project_dependency_destinations(
                        closure,
                        target,
                    )
                )

                # Every local source unit gets its own translated
                # destination. Dependency discovery does not
                # authorize flattening or consolidation.
                for unit_source in sorted(
                    closure.units,
                    key=lambda path: str(path),
                ):
                    resolved_dependencies = set()

                    source_unit = closure.units[
                        unit_source
                    ]

                    for binding in source_unit.imports:
                        local_source = resolve_local_import(
                            unit_source,
                            binding,
                            closure_root,
                        )

                        if (
                            local_source is not None
                            and local_source in closure.units
                        ):
                            resolved_dependencies.add(
                                (
                                    binding.module,
                                    binding.symbol,
                                    binding.alias,
                                )
                            )

                    imported_function_returns, (
                        imported_definition_fields
                    ) = local_type_facts.get(
                        unit_source,
                        ({}, {}),
                    )

                    plan.units.append(
                        _inspect_unit_with_type_facts(
                            unit_source,
                            projection[unit_source],
                            workspace_root=root,
                            resolved_dependencies=(
                                resolved_dependencies
                            ),
                            imported_function_returns=(
                                imported_function_returns
                            ),
                            imported_definition_fields=(
                                imported_definition_fields
                            ),
                        )
                    )

                # External dependency truth belongs to the complete
                # closure, not only the entry source.
                for dependency in sorted(
                    closure.external,
                    key=lambda item: (
                        item.module,
                        item.symbol or "",
                        item.alias or "",
                        item.level,
                    ),
                ):
                    role = classify_dependency_role(
                        dependency
                    )

                    if role.role == "source-only":
                        continue

                    identity = (
                        f"{dependency.module}."
                        f"{dependency.symbol or '*'}"
                        + (
                            f" as {dependency.alias}"
                            if dependency.alias
                            else ""
                        )
                    )

                    binding = (
                        resolve_indexed_native_binding(
                            dependency,
                            root,
                        )
                    )

                    if (
                        binding.state
                        == "library-resolved"
                    ):
                        plan.libraries.append(
                            f"{identity} -> "
                            f"{binding.identity or 'unknown'} "
                            f"[{binding.library or 'unknown'}]"
                        )
                    else:
                        plan.foreign.append(
                            identity
                        )

            except Exception as exc:
                plan.blockers.append(
                    f"dependency closure failed: {exc}"
                )

        else:
            plan.units.append(
                _inspect_unit(
                    source,
                    target,
                    workspace_root=(
                        Path(workspace_root).resolve()
                        if workspace_root is not None
                        else Path.cwd().resolve()
                    ),
                )
            )

    elif source.is_dir():
        source_root = source.resolve()
        requested_root = (
            Path(workspace_root).resolve()
            if workspace_root is not None
            else source_root
        )
        root = (
            requested_root
            if source_root.is_relative_to(requested_root)
            else source_root
        )
        destination_root = (
            destination.resolve()
            if destination is not None
            else source_root
        )

        directory_python = {
            path.resolve()
            for path in directory_sources(source_root)
            if path.suffix.lower() == ".py"
        }
        covered_python: set[Path] = set()

        for entry in sorted(
            directory_python,
            key=lambda path: str(path),
        ):
            if entry in covered_python:
                continue

            try:
                closure = build_dependency_closure(
                    entry,
                    root,
                )

                local_type_facts = (
                    _local_closure_type_facts(
                        closure,
                        root,
                    )
                )
            except Exception as exc:
                plan.blockers.append(
                    f"dependency closure failed for "
                    f"{entry}: {exc}"
                )
                covered_python.add(entry)
                continue

            for unit_source in sorted(
                closure.units,
                key=lambda path: str(path),
            ):
                try:
                    relative = unit_source.relative_to(
                        source_root
                    )
                except ValueError:
                    continue

                if unit_source not in directory_python:
                    continue

                covered_python.add(unit_source)

                resolved_dependencies = set()
                source_unit = closure.units[unit_source]

                for binding in source_unit.imports:
                    local_source = resolve_local_import(
                        unit_source,
                        binding,
                        root,
                    )

                    if (
                        local_source is not None
                        and local_source in closure.units
                    ):
                        resolved_dependencies.add(
                            (
                                binding.module,
                                binding.symbol,
                                binding.alias,
                            )
                        )

                imported_function_returns, (
                    imported_definition_fields
                ) = local_type_facts.get(
                    unit_source,
                    ({}, {}),
                )

                target = _destination_for_directory(
                    source_root,
                    destination_root,
                    unit_source,
                )

                if not any(
                    planned.source == unit_source
                    for planned in plan.units
                ):
                    plan.units.append(
                        _inspect_unit_with_type_facts(
                            unit_source,
                            target,
                            workspace_root=root,
                            resolved_dependencies=(
                                resolved_dependencies
                            ),
                            imported_function_returns=(
                                imported_function_returns
                            ),
                            imported_definition_fields=(
                                imported_definition_fields
                            ),
                        )
                    )

            for dependency in sorted(
                closure.external,
                key=lambda item: (
                    item.module,
                    item.symbol or "",
                    item.alias or "",
                    item.level,
                ),
            ):
                role = classify_dependency_role(
                    dependency
                )

                if role.role == "source-only":
                    continue

                identity = (
                    f"{dependency.module}."
                    f"{dependency.symbol or '*'}"
                    + (
                        f" as {dependency.alias}"
                        if dependency.alias
                        else ""
                    )
                )

                binding = resolve_indexed_native_binding(
                    dependency,
                    root,
                )

                if binding.state == "library-resolved":
                    library = (
                        f"{identity} -> "
                        f"{binding.identity or 'unknown'} "
                        f"[{binding.library or 'unknown'}]"
                    )
                    if library not in plan.libraries:
                        plan.libraries.append(library)
                elif identity not in plan.foreign:
                    plan.foreign.append(identity)

        for unit_source in directory_sources(source_root):
            unit_source = unit_source.resolve()

            if unit_source.suffix.lower() == ".py":
                continue

            target = _destination_for_directory(
                source_root,
                destination_root,
                unit_source,
            )
            plan.units.append(
                _inspect_unit(
                    unit_source,
                    target,
                    workspace_root=root,
                )
            )

    else:
        plan.blockers.append(
            f"source is neither file nor directory: {source}"
        )

    for unit in plan.units:
        if unit.status != "ready":
            plan.blockers.append(
                f"{unit.source}: {unit.detail}"
            )

    if not plan.units and not plan.blockers:
        plan.blockers.append(
            "no supported source units discovered"
        )

    return plan
