import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


with TemporaryDirectory() as temp:
    root = Path(temp)

    supported = root / "supported.py"
    supported.write_text(
        "def second(values: list[int]):\n"
        "    return values[1]\n",
        encoding="utf-8",
    )

    document = load_python(supported)
    report = inspect_support(document)

    assert report.status == "ready", report

    candidate = emit_qps(document)

    assert (
        "sequence_at(value- values, index- 1)"
        in candidate
    ), candidate

    output = root / "supported.qps"
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
        "def second(values):\n"
        "    return values[1]\n",
        encoding="utf-8",
    )

    unknown_report = inspect_support(
        load_python(unknown)
    )

    assert unknown_report.status == "partial"
    assert any(
        "subscript base is not proven QPS SEQUENCE"
        in reason
        for reason in unknown_report.reasons
    )

print(
    "CIPHER_TYPED_SEQUENCE_SUBSCRIPT=PASS"
)
