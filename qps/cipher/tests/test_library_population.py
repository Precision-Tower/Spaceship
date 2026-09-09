from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.ir.nodes import DependencyRef
from qps.cipher.foreign.population import (
    plan_python_library_symbol,
)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


def write(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        text,
        encoding="utf-8",
    )


def apply_plan(plan) -> None:
    for write_item in plan.writes:
        write_item.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        write_item.path.write_text(
            write_item.content,
            encoding="utf-8",
        )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        python_index = (
            root
            / "libs/Python/_index.qps"
        )

        write(
            python_index,
            '''
Python.

surface: (
);
''',
        )

        cylinder_dependency = DependencyRef(
            package="OCC",
            module="OCC.Core.BRepPrimAPI",
            symbol="BRepPrimAPI_MakeCylinder",
        )

        cylinder_plan = (
            plan_python_library_symbol(
                cylinder_dependency,
                root,
                "Cylinder.\n",
            )
        )

        paths = {
            item.path.relative_to(root).as_posix()
            for item in cylinder_plan.writes
        }

        require(
            len(paths) == len(cylinder_plan.writes),
            "population plan contains duplicate write paths",
        )

        require(
            "libs/Python/_index.qps"
            in paths,
            repr(paths),
        )

        require(
            "libs/Python/OCC/_index.qps"
            in paths,
            repr(paths),
        )

        require(
            "libs/Python/OCC/Core/_index.qps"
            in paths,
            repr(paths),
        )

        require(
            "libs/Python/OCC/Core/"
            "BRepPrimAPI/_index.qps"
            in paths,
            repr(paths),
        )

        require(
            "libs/Python/OCC/Core/"
            "BRepPrimAPI/"
            "BRepPrimAPI_MakeCylinder.qps"
            in paths,
            repr(paths),
        )

        # Planning itself must not mutate disk.
        require(
            not (
                root
                / "libs/Python/OCC"
            ).exists(),
            "population planning mutated disk",
        )

        apply_plan(cylinder_plan)

        make_box_dependency = DependencyRef(
            package="OCC",
            module="OCC.Core.BRepPrimAPI",
            symbol="BRepPrimAPI_MakeBox",
        )

        box_plan = plan_python_library_symbol(
            make_box_dependency,
            root,
            "Box.\n",
        )

        box_paths = {
            item.path.relative_to(root).as_posix()
            for item in box_plan.writes
        }

        # All namespace directories/indexes must be reused.
        require(
            box_paths
            == {
                "libs/Python/OCC/Core/"
                "BRepPrimAPI/_index.qps",
                "libs/Python/OCC/Core/"
                "BRepPrimAPI/"
                "BRepPrimAPI_MakeBox.qps",
            },
            repr(box_paths),
        )

        # Asking for Cylinder again must require no writes.
        reused = plan_python_library_symbol(
            cylinder_dependency,
            root,
            "Cylinder should not be duplicated.\n",
        )

        require(
            reused.writes == [],
            repr(reused.writes),
        )

        require(
            any(
                path.name
                == "BRepPrimAPI_MakeCylinder.qps"
                for path in reused.reused
            ),
            repr(reused.reused),
        )

    print(
        "CIPHER_LIBRARY_POPULATION_PLAN=PASS"
    )


if __name__ == "__main__":
    main()
