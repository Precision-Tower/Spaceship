from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .emit.qps_emitter import emit_qps
from .emit.convergence_qps import emit_convergence_qps
from .reports.report import summarize


def load_source(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".json":
        from .sources.json_source import load_json
        return load_json(path)

    if suffix in {".yaml", ".yml"}:
        from .sources.yaml_source import load_yaml
        return load_yaml(path)

    if suffix == ".py":
        from .sources.python_source import load_python
        return load_python(path)

    if suffix in {".cpp", ".cc", ".cxx", ".hpp", ".h"}:
        from .sources.cpp_source import load_cpp
        return load_cpp(path)

    raise SystemExit(
        f"Cipher source type not yet supported: {suffix}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--report", action="store_true")
    parser.add_argument(
        "--converge",
        action="store_true",
        help="emit semantic convergence QPS",
    )
    args = parser.parse_args()

    path = Path(args.source)
    document = load_source(path)

    if args.converge:
        print(emit_convergence_qps(document), end="")
    else:
        print(emit_qps(document), end="")

    if args.report:
        print(summarize(document), file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
