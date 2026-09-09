from pathlib import Path
import tempfile

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def prepare(source_text):
    temporary = tempfile.TemporaryDirectory()
    path = Path(temporary.name) / "source.py"

    path.write_text(
        source_text,
        encoding="utf-8",
    )

    document = load_python(path)

    return temporary, document


def main():
    temporary, document = prepare(
        "\n".join([
            "def subtract(a, b):",
            "    return a - b",
            "",
            "result = subtract(b=4, a=9)",
            "",
        ])
    )

    try:
        support = inspect_support(document)

        reasons = " | ".join(
            support.reasons
        )

        require(
            "keyword call arguments are not emitted"
            not in reasons,
            reasons,
        )

        candidate = emit_qps(document)

        require(
            "subtract(b- 4, a- 9)"
            in candidate,
            candidate,
        )

        require(
            "record(" not in candidate,
            candidate,
        )
    finally:
        temporary.cleanup()

    temporary, document = prepare(
        "\n".join([
            "def subtract(a, b):",
            "    return a - b",
            "",
            "result = subtract(9, b=4)",
            "",
        ])
    )

    try:
        candidate = emit_qps(document)

        require(
            "subtract(9, b- 4)"
            in candidate,
            candidate,
        )
    finally:
        temporary.cleanup()

    print(
        "CIPHER_KEYWORD_CALL_EMISSION=PASS"
    )


if __name__ == "__main__":
    main()
