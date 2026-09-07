from __future__ import annotations

import sys
from pathlib import Path

from .ir.source_facts import project_source_facts
from .emit.source_facts_qps import (
    emit_source_facts_qps,
)


def _load(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".py":
        from .sources.python_source import load_python
        return load_python(path)

    if suffix in {
        ".cpp",
        ".cc",
        ".cxx",
        ".hpp",
        ".h",
    }:
        from .sources.cpp_source import load_cpp
        return load_cpp(path)

    if suffix == ".json":
        from .sources.json_source import load_json
        return load_json(path)

    if suffix in {".yaml", ".yml"}:
        from .sources.yaml_source import load_yaml
        return load_yaml(path)

    raise RuntimeError(
        "Cipher source adapter does not recognize "
        f"source type: {suffix}"
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: python3 -m "
            "Engineering.py.cipher.source_adapter "
            "<source>",
            file=sys.stderr,
        )
        return 1

    source = Path(sys.argv[1])

    document = _load(source)
    facts = project_source_facts(document)

    sys.stdout.write(
        emit_source_facts_qps(facts)
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
