import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


with TemporaryDirectory() as temp:
    root = Path(temp)

    source = root / "plan.py"

    source.write_text(
        "from dataclasses import dataclass, field\n"
        "\n"
        "@dataclass\n"
        "class ConversionPlan:\n"
        "    units: list[int] = field(default_factory=list)\n"
        "\n"
        "def build_conversion_plan() -> ConversionPlan:\n"
        "    return ConversionPlan(units=[1, 2, 3])\n"
        "\n"
        "def probe():\n"
        "    plan = build_conversion_plan()\n"
        "    return len(plan.units)\n",
        encoding="utf-8",
    )

    document = load_python(source)

    report = inspect_support(document)

    assert report.status == "ready", report

    candidate = emit_qps(document)

    assert (
        "sequence_size(value- plan.units)"
        in candidate
    ), candidate

    output = root / "plan.qps"

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
    "CIPHER_NATIVE_DEFINITION_FIELD_LEN=PASS"
)
