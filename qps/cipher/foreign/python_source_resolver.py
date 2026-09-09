from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from qps.cipher.ir.nodes import DependencyRef


@dataclass(frozen=True)
class PythonForeignSource:
    dependency: DependencyRef
    module: str
    symbol: str | None
    state: str
    origin: Path | None
    package_locations: tuple[Path, ...]
    source_kind: str
    detail: str = ""


def _classify_origin(
    origin: str | None,
) -> tuple[Path | None, str]:
    if not origin:
        return None, "namespace"

    if origin in {
        "built-in",
        "frozen",
    }:
        return None, origin

    path = Path(origin).resolve()
    suffix = path.suffix.lower()

    if suffix == ".py":
        return path, "python"

    if suffix in {
        ".so",
        ".pyd",
        ".dll",
        ".dylib",
    }:
        return path, "native-extension"

    if suffix in {
        ".pyi",
    }:
        return path, "python-stub"

    return path, "other"


def resolve_python_foreign_source(
    dependency: DependencyRef,
) -> PythonForeignSource:
    module = (
        dependency.module
        or dependency.package
        or ""
    )

    if not module:
        return PythonForeignSource(
            dependency=dependency,
            module="",
            symbol=dependency.symbol,
            state="unresolved",
            origin=None,
            package_locations=(),
            source_kind="unknown",
            detail="dependency has no module identity",
        )

    try:
        spec = find_spec(module)
    except Exception as exc:
        return PythonForeignSource(
            dependency=dependency,
            module=module,
            symbol=dependency.symbol,
            state="unresolved",
            origin=None,
            package_locations=(),
            source_kind="unknown",
            detail=str(exc),
        )

    if spec is None:
        return PythonForeignSource(
            dependency=dependency,
            module=module,
            symbol=dependency.symbol,
            state="missing",
            origin=None,
            package_locations=(),
            source_kind="missing",
            detail="Python importlib could not resolve module",
        )

    origin, source_kind = _classify_origin(
        spec.origin
    )

    package_locations = tuple(
        Path(location).resolve()
        for location in (
            spec.submodule_search_locations
            or ()
        )
    )

    return PythonForeignSource(
        dependency=dependency,
        module=module,
        symbol=dependency.symbol,
        state="resolved",
        origin=origin,
        package_locations=package_locations,
        source_kind=source_kind,
    )
