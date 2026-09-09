from __future__ import annotations

from qps.cipher.ir.nodes import DependencyRef
from qps.cipher.foreign.python_source_resolver import (
    resolve_python_foreign_source,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def resolve(module: str, symbol: str | None = None):
    return resolve_python_foreign_source(
        DependencyRef(
            package=module.split(".", 1)[0],
            module=module,
            symbol=symbol,
        )
    )


def main() -> None:
    dataclasses = resolve("dataclasses", "dataclass")
    require(dataclasses.state == "resolved", repr(dataclasses))
    require(
        dataclasses.source_kind in {"python", "frozen"},
        repr(dataclasses),
    )
    require(
        dataclasses.provenance in {"stdlib", "frozen"},
        repr(dataclasses),
    )
    require(
        dataclasses.distribution is None,
        repr(dataclasses),
    )

    statistics = resolve("statistics")
    require(statistics.state == "resolved", repr(statistics))
    require(statistics.source_kind == "python", repr(statistics))
    require(statistics.provenance == "stdlib", repr(statistics))
    require(statistics.distribution is None, repr(statistics))

    sniffio = resolve("sniffio")
    require(sniffio.state == "resolved", repr(sniffio))
    require(sniffio.source_kind == "python", repr(sniffio))
    require(
        sniffio.provenance == "external-distribution",
        repr(sniffio),
    )
    require(sniffio.distribution == "sniffio", repr(sniffio))
    require(sniffio.package_locations, repr(sniffio))

    sys_module = resolve("sys")
    require(sys_module.state == "resolved", repr(sys_module))
    require(sys_module.source_kind == "built-in", repr(sys_module))
    require(sys_module.provenance == "built-in", repr(sys_module))

    missing = resolve("definitely_missing_ceos_package", "missing")
    require(missing.state == "missing", repr(missing))
    require(missing.provenance == "missing", repr(missing))

    print("CIPHER_PYTHON_FOREIGN_SOURCE=PASS")


if __name__ == "__main__":
    main()
