import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support
from qps.cipher.type_facts import (
    enrich_explicit_local_types,
)


with TemporaryDirectory() as temp:
    root = Path(temp)
    source = root / "probe.py"

    source.write_text(
        "def probe(values: list[int]):\n"
        '    message = f"count={len(values)}"\n'
        "    return message\n",
        encoding="utf-8",
    )

    document = load_python(source)

    enrich_explicit_local_types(
        document
    )

    report = inspect_support(document)

    assert report.status == "ready", report

    candidate = emit_qps(document)

    assert (
        "string(sequence_size("
        in candidate
    ), candidate

    output = root / "probe.qps"

    output.write_text(
        candidate,
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "qps",
            str(output),
            "--check",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, (
        result.stderr
        or result.stdout
    )

print(
    "CIPHER_LEN_INTERPOLATION_EMISSION=PASS"
)
