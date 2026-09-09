import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


with TemporaryDirectory() as temp:
    root = Path(temp)

    typed = root / "typed.py"
    typed.write_text(
        "def fail(detail: str):\n"
        "    raise RuntimeError(detail)\n",
        encoding="utf-8",
    )

    document = load_python(typed)
    report = inspect_support(document)

    assert report.status == "ready", report

    candidate = emit_qps(document)

    assert "-raise detail;" in candidate, candidate

    output = root / "typed.qps"
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

    unknown = root / "unknown.py"
    unknown.write_text(
        "def fail(detail):\n"
        "    raise RuntimeError(detail)\n",
        encoding="utf-8",
    )

    unknown_report = inspect_support(
        load_python(unknown)
    )

    assert unknown_report.status == "partial"

print("CIPHER_TYPED_STRING_RAISE=PASS")
