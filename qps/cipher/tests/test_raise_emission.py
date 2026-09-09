import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


with TemporaryDirectory() as temp:
    root = Path(temp)

    literal = root / "literal.py"
    literal.write_text(
        "def fail():\n"
        '    raise ValueError("bad input")\n',
        encoding="utf-8",
    )

    document = load_python(literal)
    report = inspect_support(document)

    assert report.status == "ready", report

    candidate = emit_qps(document)

    assert '-raise "bad input"/a;' in candidate or '-raise "bad input";' in candidate

    output = root / "literal.qps"
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

    unsupported = root / "bare.py"
    unsupported.write_text(
        "def fail():\n"
        "    raise\n",
        encoding="utf-8",
    )

    unsupported_report = inspect_support(
        load_python(unsupported)
    )

    assert unsupported_report.status == "partial"

print("CIPHER_RAISE_EMISSION=PASS")
