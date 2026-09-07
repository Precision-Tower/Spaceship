from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Engineering.py.cipher.ir.nodes import DependencyRef
from .native_binary import (
    NativeBinaryCapability,
    resolve_native_binary_capability,
)


@dataclass(frozen=True)
class NativeLibraryMapping:
    dependency: DependencyRef
    capability_identity: str
    native_symbol: str


PYTHON_NATIVE_MAPPINGS = {
    (
        "OCC.Core.BRepPrimAPI",
        "BRepPrimAPI_MakeCylinder",
    ): (
        "construct.cylinder",
        "BRepPrimAPI_MakeCylinder",
    ),

    (
        "OCC.Core.BRepPrimAPI",
        "BRepPrimAPI_MakeBox",
    ): (
        "construct.box",
        "BRepPrimAPI_MakeBox",
    ),
}


def mapped_native_capability(
    dependency: DependencyRef,
    search_roots: list[str | Path],
) -> NativeBinaryCapability | None:
    module = (
        dependency.module
        or dependency.package
        or ""
    )

    key = (
        module,
        dependency.symbol,
    )

    mapping = PYTHON_NATIVE_MAPPINGS.get(key)

    if mapping is None:
        return None

    identity, native_symbol = mapping

    return resolve_native_binary_capability(
        identity=identity,
        symbol_name=native_symbol,
        search_roots=search_roots,
    )
