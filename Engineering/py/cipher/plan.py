from __future__ import annotations

from dataclasses import dataclass, field
import os
import subprocess
import tempfile
from pathlib import Path

from .graph.dependency_closure import (
    build_dependency_closure,
    resolve_local_import,
)
from .support import (
    dependency_key,
    inspect_support,
)
from .libs.dependency_role import (
    classify_dependency_role,
)
from .libs.indexed_native_binding import (
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


def _inspect_unit(
    source: Path,
    destination: Path,
    *,
    converge: bool,
    resolved_dependencies=None,
) -> PlannedUnit:
    # Lazy import avoids cipher.py -> plan.py -> cipher.py
    # initialization recursion.
    from .cipher import (
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

    try:
        # Emit only after the exact prepared document passes support.
        candidate = emit_prepared_document(
            document,
            converge,
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
    converge: bool = True,
    workspace_root: str | Path | None = None,
) -> ConversionPlan:
    # These helpers live in cipher.py today, but importing them only
    # when planning executes keeps module initialization acyclic.
    from .cipher import directory_sources, is_supported
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

        resolved_dependencies = set()

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

                # A local import whose source unit belongs to this
                # conversion closure is already satisfied by the
                # repository-preserving ConversionPlan.
                entry_unit = closure.units.get(
                    source.resolve()
                )

                if entry_unit is not None:
                    for binding in entry_unit.imports:
                        local_source = resolve_local_import(
                            source.resolve(),
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

                for dependency in closure.external:
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
                        resolved_dependencies.add(
                            dependency_key(
                                dependency
                            )
                        )

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

        plan.units.append(
            _inspect_unit(
                source,
                target,
                converge=converge,
                resolved_dependencies=(
                    resolved_dependencies
                ),
            )
        )

    elif source.is_dir():
        for unit_source in directory_sources(source):
            target = _destination_for_directory(
                source,
                destination,
                unit_source,
            )

            plan.units.append(
                _inspect_unit(
                    unit_source,
                    target,
                    converge=converge,
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
