import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


with TemporaryDirectory() as temp:
    root = Path(temp)
    source = root / "tuple_value.py"

    source.write_text(
        "def pair(a, b):\n"
        "    value = (a, b)\n"
        "    return value\n",
        encoding="utf-8",
    )

    document = load_python(source)
    report = inspect_support(document)

    assert report.status == "ready", report

    candidate = emit_qps(document)

    assert "sequence(a, b)" in candidate, candidate

    output = root / "tuple_value.qps"
    output.write_text(
        candidate,
        encoding="utf-8",
    )

    result = subprocess.run(
        ["qps", str(output), "--check"],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, (
        result.stderr or result.stdout
    )

print("CIPHER_TUPLE_VALUE_SEQUENCE_EMISSION=PASS")
