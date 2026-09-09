from qps.cipher.ir.nodes import DependencyRef
from qps.cipher.foreign.dependency_role import (
    classify_dependency_role,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    dataclass_role = classify_dependency_role(
        DependencyRef(
            package="dataclasses",
            module="dataclasses",
            symbol="dataclass",
        )
    )

    require(
        dataclass_role.role == "source-only",
        repr(dataclass_role),
    )

    field_role = classify_dependency_role(
        DependencyRef(
            package="dataclasses",
            module="dataclasses",
            symbol="field",
        )
    )

    require(
        field_role.role == "source-only",
        repr(field_role),
    )

    any_role = classify_dependency_role(
        DependencyRef(
            package="typing",
            module="typing",
            symbol="Any",
        )
    )

    require(
        any_role.role == "source-only",
        repr(any_role),
    )

    occ_role = classify_dependency_role(
        DependencyRef(
            package="OCC",
            module="OCC.Core.BRepPrimAPI",
            symbol="BRepPrimAPI_MakeCylinder",
        )
    )

    require(
        occ_role.role == "library",
        repr(occ_role),
    )

    print("CIPHER_DEPENDENCY_ROLE=PASS")


if __name__ == "__main__":
    main()
