from __future__ import annotations

import os
from pathlib import Path

from Engineering.py.cipher.ir.nodes import DependencyRef
from Engineering.py.cipher.libs.native_mapping import (
    mapped_native_capability,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    home = Path.home()

    occt_root = (
        home / "ce-os-occt-probe"
    )

    cylinder = mapped_native_capability(
        DependencyRef(
            package="OCC",
            module="OCC.Core.BRepPrimAPI",
            symbol="BRepPrimAPI_MakeCylinder",
        ),
        [occt_root],
    )

    require(
        cylinder is not None,
        "Cylinder mapping missing",
    )

    require(
        cylinder.state == "resolved",
        repr(cylinder),
    )

    require(
        cylinder.binary is not None
        and cylinder.binary.name == "libTKPrim.so",
        repr(cylinder),
    )

    require(
        cylinder.architecture == "AArch64",
        repr(cylinder),
    )

    require(
        any(
            "BRepPrimAPI_MakeCylinder"
            in symbol
            for symbol in cylinder.symbols
        ),
        repr(cylinder.symbols),
    )

    box = mapped_native_capability(
        DependencyRef(
            package="OCC",
            module="OCC.Core.BRepPrimAPI",
            symbol="BRepPrimAPI_MakeBox",
        ),
        [occt_root],
    )

    require(
        box is not None
        and box.state == "resolved",
        repr(box),
    )

    print(
        "CIPHER_NATIVE_BINARY_RESOLUTION=PASS"
    )


if __name__ == "__main__":
    main()
