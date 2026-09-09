from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path
import sysconfig

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
    provenance: str
    distribution: str | None = None
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

    if suffix == ".pyi":
        return path, "python-stub"

    return path, "other"


def _under(
    path: Path,
    root: Path | None,
) -> bool:
    if root is None:
        return False
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _environment_roots() -> tuple[
    tuple[Path, ...],
    tuple[Path, ...],
]:
    paths = sysconfig.get_paths()

    stdlib = tuple(
        dict.fromkeys(
            Path(value).resolve()
            for key in ("stdlib", "platstdlib")
            if (value := paths.get(key))
        )
    )

    external = tuple(
        dict.fromkeys(
            Path(value).resolve()
            for key in ("purelib", "platlib")
            if (value := paths.get(key))
        )
    )

    return stdlib, external


def _top_level_module(module: str) -> str:
    return module.split(".", 1)[0]


def _distribution_owner(
    module: str,
) -> str | None:
    owners = metadata.packages_distributions().get(
        _top_level_module(module),
        (),
    )
    if not owners:
        return None
    return sorted(owners)[0]


def _classify_provenance(
    module: str,
    origin: Path | None,
    package_locations: tuple[Path, ...],
    source_kind: str,
) -> tuple[str, str | None]:
    if source_kind == "built-in":
        return "built-in", None

    if source_kind == "frozen":
        return "frozen", None

    distribution = _distribution_owner(module)
    stdlib_roots, external_roots = _environment_roots()

    evidence = tuple(
        path
        for path in (
            (origin,) + package_locations
        )
        if path is not None
    )

    # Distribution ownership is stronger than a broad stdlib path:
    # site-packages commonly lives beneath the interpreter lib root.
    if distribution is not None:
        return "external-distribution", distribution

    if any(
        _under(path, root)
        for path in evidence
        for root in external_roots
    ):
        return "external-unowned", None

    if any(
        _under(path, root)
        for path in evidence
        for root in stdlib_roots
    ):
        return "stdlib", None

    if source_kind == "namespace":
        return "namespace", None

    return "environment-other", None


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
            provenance="unresolved",
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
            provenance="unresolved",
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
            provenance="missing",
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

    provenance, distribution = _classify_provenance(
        module,
        origin,
        package_locations,
        source_kind,
    )

    return PythonForeignSource(
        dependency=dependency,
        module=module,
        symbol=dependency.symbol,
        state="resolved",
        origin=origin,
        package_locations=package_locations,
        source_kind=source_kind,
        provenance=provenance,
        distribution=distribution,
    )
