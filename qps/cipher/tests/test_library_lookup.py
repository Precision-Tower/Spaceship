from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.ir.nodes import DependencyRef
from qps.cipher.foreign.indexed_lookup import (
    lookup_python_library,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        write(
            root / "libs/Python/_index.qps",
            '''
Python.

surface: (
OCC- "OCC/_index.qps";
);
''',
        )

        write(
            root / "libs/Python/OCC/_index.qps",
            '''
OCC.

surface: (
Core- "Core/_index.qps";
);
''',
        )

        write(
            root / "libs/Python/OCC/Core/_index.qps",
            '''
Core.

surface: (
BRepPrimAPI- "BRepPrimAPI/_index.qps";
);
''',
        )

        write(
            root
            / "libs/Python/OCC/Core/BRepPrimAPI/_index.qps",
            '''
BRepPrimAPI.

surface: (
BRepPrimAPI_MakeCylinder- "BRepPrimAPI_MakeCylinder.qps";
);
''',
        )

        write(
            root
            / "libs/Python/OCC/Core/BRepPrimAPI"
            / "BRepPrimAPI_MakeCylinder.qps",
            'Cylinder_Library_Symbol.\n',
        )

        cylinder = lookup_python_library(
            DependencyRef(
                package="OCC",
                module="OCC.Core.BRepPrimAPI",
                symbol="BRepPrimAPI_MakeCylinder",
            ),
            root,
        )

        require(
            cylinder.state == "library-resolved",
            repr(cylinder),
        )

        require(
            cylinder.symbol_path is not None
            and cylinder.symbol_path.name
            == "BRepPrimAPI_MakeCylinder.qps",
            repr(cylinder),
        )

        missing_symbol = lookup_python_library(
            DependencyRef(
                package="OCC",
                module="OCC.Core.BRepPrimAPI",
                symbol="BRepPrimAPI_MakeBox",
            ),
            root,
        )

        require(
            missing_symbol.state == "library-missing",
            repr(missing_symbol),
        )

        missing_namespace = lookup_python_library(
            DependencyRef(
                package="numpy",
                module="numpy.linalg",
                symbol="norm",
            ),
            root,
        )

        require(
            missing_namespace.state == "library-missing",
            repr(missing_namespace),
        )

    print("CIPHER_LIBRARY_LOOKUP=PASS")


if __name__ == "__main__":
    main()
