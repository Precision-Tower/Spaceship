from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from Engineering.py.cipher.ir.nodes import DependencyRef
from .indexed_lookup import lookup_python_library
from .native_binary import resolve_native_binary_capability


@dataclass(frozen=True)
class IndexedNativeBinding:
    dependency: DependencyRef
    state: str
    identity: str | None
    leaf: Path | None
    library: str | None
    native_lookup: str | None
    binary: Path | None
    architecture: str | None
    detail: str = ""


def _section(text: str, name: str) -> str | None:
    marker = f"{name}: ("
    start = text.find(marker)

    if start < 0:
        return None

    open_pos = text.find("(", start)
    depth = 0
    quoted = False
    escaped = False

    for index in range(open_pos, len(text)):
        character = text[index]

        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue

        if character == '"':
            quoted = True
            continue

        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1

            if depth == 0:
                return text[open_pos + 1:index]

    return None


def _scalar(text: str, key: str) -> str | None:
    match = re.search(
        rf'(?m)^\s*{re.escape(key)}-\s*"([^"]*)";\s*$',
        text,
    )

    return match.group(1) if match else None


def _search_roots(
    workspace_root: Path,
) -> list[Path]:
    roots: list[Path] = []

    configured = os.environ.get(
        "CEOS_NATIVE_LIBRARY_PATH"
    )

    if configured:
        for value in configured.split(
            os.pathsep
        ):
            if value:
                roots.append(
                    Path(value).expanduser().resolve()
                )

    # Current Pixel host discovery surface.
    pixel_probe = (
        Path.home()
        / "ce-os-occt-probe"
    )

    if pixel_probe.exists():
        roots.append(
            pixel_probe.resolve()
        )

    # Repository-local host artifacts may also be supplied later.
    repo_native = (
        workspace_root
        / "qps"
        / "native"
    )

    if repo_native.exists():
        roots.append(
            repo_native.resolve()
        )

    result = []

    for root in roots:
        if root not in result:
            result.append(root)

    return result


def resolve_indexed_native_binding(
    dependency: DependencyRef,
    workspace_root: str | Path,
) -> IndexedNativeBinding:
    root = Path(workspace_root).resolve()

    lookup = lookup_python_library(
        dependency,
        root,
    )

    if (
        lookup.state != "library-resolved"
        or lookup.symbol_path is None
    ):
        return IndexedNativeBinding(
            dependency=dependency,
            state=lookup.state,
            identity=None,
            leaf=lookup.symbol_path,
            library=None,
            native_lookup=None,
            binary=None,
            architecture=None,
            detail=lookup.detail,
        )

    leaf = lookup.symbol_path.resolve()
    text = leaf.read_text(
        encoding="utf-8"
    )

    identity = _scalar(
        text,
        "identity",
    )

    implementation = _section(
        text,
        "implementation",
    )

    if implementation is None:
        return IndexedNativeBinding(
            dependency=dependency,
            state="library-invalid",
            identity=identity,
            leaf=leaf,
            library=None,
            native_lookup=None,
            binary=None,
            architecture=None,
            detail=(
                "Indexed library leaf has no "
                "implementation surface"
            ),
        )

    family = _scalar(
        implementation,
        "family",
    )

    resolver = _scalar(
        implementation,
        "resolver",
    )

    library = _scalar(
        implementation,
        "library",
    )

    native_lookup = _scalar(
        implementation,
        "native_lookup",
    )

    if (
        family != "native-binary"
        or resolver != "host-native-binary"
        or not library
        or not native_lookup
    ):
        return IndexedNativeBinding(
            dependency=dependency,
            state="library-invalid",
            identity=identity,
            leaf=leaf,
            library=library,
            native_lookup=native_lookup,
            binary=None,
            architecture=None,
            detail=(
                "Indexed library implementation "
                "is not a complete host-native binding"
            ),
        )

    roots = _search_roots(root)

    for search_root in roots:
        candidates = sorted(
            path
            for path in search_root.rglob(
                library
            )
            if path.is_file()
        )

        for candidate in candidates:
            capability = (
                resolve_native_binary_capability(
                    identity=identity or "",
                    symbol_name=native_lookup,
                    search_roots=[
                        candidate.parent
                    ],
                )
            )

            if (
                capability.state == "resolved"
                and capability.binary is not None
                and capability.binary.name
                == library
            ):
                return IndexedNativeBinding(
                    dependency=dependency,
                    state="library-resolved",
                    identity=identity,
                    leaf=leaf,
                    library=library,
                    native_lookup=native_lookup,
                    binary=capability.binary,
                    architecture=capability.architecture,
                )

    return IndexedNativeBinding(
        dependency=dependency,
        state="library-host-missing",
        identity=identity,
        leaf=leaf,
        library=library,
        native_lookup=native_lookup,
        binary=None,
        architecture=None,
        detail=(
            f"{library} is indexed but no current "
            "host binary exports "
            f"{native_lookup}"
        ),
    )
