from __future__ import annotations

from qps.cipher.ir.nodes import DependencyRef
from qps.cipher.foreign.python_source_resolver import (
    resolve_python_foreign_source,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    dataclasses = resolve_python_foreign_source(
        DependencyRef(
            package="dataclasses",
            module="dataclasses",
            symbol="dataclass",
        )
    )

    require(
        dataclasses.state == "resolved",
        repr(dataclasses),
    )

    require(
        dataclasses.source_kind
        in {
            "python",
            "frozen",
        },
        repr(dataclasses),
    )

    missing = resolve_python_foreign_source(
        DependencyRef(
            package="definitely_missing_ceos_package",
            module="definitely_missing_ceos_package",
            symbol="missing",
        )
    )

    require(
        missing.state == "missing",
        repr(missing),
    )

    print("CIPHER_PYTHON_FOREIGN_SOURCE=PASS")


if __name__ == "__main__":
    main()
