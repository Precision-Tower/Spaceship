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
        "def render(name: str, mass: float, count: int):\n"
        '    value = f"name={name} mass={mass} count={count}"\n'
        "    return value\n",
        encoding="utf-8",
    )

    document = load_python(supported)
    report = inspect_support(document)

    assert report.status == "ready", report

    candidate = emit_qps(document)

    assert 'string(name)' in candidate
    assert 'string(mass)' in candidate
    assert 'string(count)' in candidate

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
        "def render(name):\n"
        '    return f"name={name}"\n',
        encoding="utf-8",
    )

    unknown_report = inspect_support(
        load_python(unknown)
    )

    assert unknown_report.status == "partial"
    assert any(
        "interpolation value type is not proven"
        in reason
        for reason in unknown_report.reasons
    )

    special = root / "special.py"
    special.write_text(
        "def render(name: str):\n"
        '    return f"{name!r}"\n',
        encoding="utf-8",
    )

    special_report = inspect_support(
        load_python(special)
    )

    assert special_report.status == "partial"
    assert any(
        "formatted interpolation conversion/spec"
        in reason
        for reason in special_report.reasons
    )

print("CIPHER_INTERPOLATION_PROVEN_TYPES=PASS")
