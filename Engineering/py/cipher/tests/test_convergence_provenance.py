from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.emit.convergence_qps import (
    emit_convergence_qps,
)
from Engineering.py.cipher.sources.cpp_source import (
    load_cpp,
)
from Engineering.py.cipher.sources.python_source import (
    load_python,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        py = root / "cylinder.py"

        py.write_text(
            "from OCC.Core.BRepPrimAPI import "
            "BRepPrimAPI_MakeCylinder\n"
            "\n"
            "def build(radius, height):\n"
            "    return "
            "BRepPrimAPI_MakeCylinder(radius, height)\n",
            encoding="utf-8",
        )

        py_output = emit_convergence_qps(
            load_python(py),
            workspace_root=root,
        )

        require(
            'family- "Python";'
            in py_output,
            py_output,
        )

        require(
            'path- "cylinder.py";'
            in py_output,
            py_output,
        )

        require(
            'extension- ".py";'
            in py_output,
            py_output,
        )

        require(
            str(root)
            not in py_output,
            "Python convergence leaked absolute path:\n"
            + py_output,
        )

        cpp = root / "geometry.cpp"

        cpp.write_text(
            "#include <BRepPrimAPI_MakeCylinder.hxx>\n"
            "\n"
            "void build() {\n"
            "    BRepPrimAPI_MakeCylinder "
            "cylinder(10.0, 20.0);\n"
            "}\n",
            encoding="utf-8",
        )

        cpp_output = emit_convergence_qps(
            load_cpp(cpp),
            workspace_root=root,
        )

        require(
            'family- "C++";'
            in cpp_output,
            cpp_output,
        )

        require(
            'path- "geometry.cpp";'
            in cpp_output,
            cpp_output,
        )

        require(
            'extension- ".cpp";'
            in cpp_output,
            cpp_output,
        )

        require(
            str(root)
            not in cpp_output,
            "C++ convergence leaked absolute path:\n"
            + cpp_output,
        )

    print(
        "CIPHER_CONVERGENCE_PROVENANCE=PASS"
    )


if __name__ == "__main__":
    main()
