from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / "lists.py"
        source.write_text(
            'empty = []\n'
            '\n'
            'one = [1]\n'
            '\n'
            'mixed = [1, "two", [3, "four"]]\n'
        )

        document = load_python(source)
        report = inspect_support(document)

        reasons = " | ".join(report.reasons)
        require(
            "list expressions are not emitted" not in reasons,
            reasons,
        )

        candidate = emit_qps(document)

        require(
            "sequence()" in candidate,
            candidate,
        )
        require(
            "sequence(1)" in candidate,
            candidate,
        )
        require(
            'sequence(1, "two", sequence(3, "four"))'
            in candidate,
            candidate,
        )
        require(
            "[1" not in candidate and '["' not in candidate,
            "Python list syntax leaked into QPS candidate:\n" + candidate,
        )

        print("CIPHER_LIST_EXPRESSION_EMISSION=PASS")


if __name__ == "__main__":
    main()
