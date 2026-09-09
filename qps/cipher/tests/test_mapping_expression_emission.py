from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / "mapping.py"

        source.write_text(
            'inputs = {\n'
            '    "mass_kg": 2,\n'
            '    "gravity_m_s2": 9.81,\n'
            '}\n',
            encoding="utf-8",
        )

        document = load_python(source)
        report = inspect_support(document)

        require(
            report.status == "ready",
            repr(report),
        )

        qps = emit_qps(document)

        require(
            "inputs: (" in qps,
            qps,
        )
        require(
            "mass_kg- 2;" in qps,
            qps,
        )
        require(
            "gravity_m_s2- 9.81;" in qps,
            qps,
        )
        require(
            "record(" not in qps,
            qps,
        )

        print(
            "CIPHER_MAPPING_NATIVE_TERM_EMISSION=PASS"
        )


if __name__ == "__main__":
    main()
