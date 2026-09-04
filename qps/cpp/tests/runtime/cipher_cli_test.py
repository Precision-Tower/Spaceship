#!/usr/bin/env python3

import subprocess
import sys
import tempfile
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: cipher_cli_test.py <qps>")

    qps = Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "occt_probe.py"

        source.write_text(
            "from OCC.Core.BRepPrimAPI import "
            "BRepPrimAPI_MakeCylinder\n"
            "from OCC.Core.BRepAlgoAPI import "
            "BRepAlgoAPI_Cut as Cut\n"
            "\n"
            "def build(radius, height, left, right):\n"
            "    solid = BRepPrimAPI_MakeCylinder(radius, height)\n"
            "    return Cut(solid, right)\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [str(qps), "cipher", str(source)],
            text=True,
            capture_output=True,
        )

        require(result.returncode == 0, result.stderr)

        require(
            'semantic_identity- "construct.cylinder";'
            in result.stdout,
            result.stdout,
        )

        require(
            'semantic_identity- "boolean.cut";'
            in result.stdout,
            result.stdout,
        )

        require(
            'implementation_symbol- "BRepPrimAPI_MakeCylinder";'
            in result.stdout,
            result.stdout,
        )

        require(
            'implementation_symbol- "BRepAlgoAPI_Cut";'
            in result.stdout,
            result.stdout,
        )

        require(
            'convergence_state- "candidate";'
            in result.stdout,
            result.stdout,
        )

        report = subprocess.run(
            [str(qps), "cipher", str(source), "--report"],
            text=True,
            capture_output=True,
        )

        require(report.returncode == 0, report.stderr)
        require(
            report.stdout.startswith("Cipher_Convergence:"),
            report.stdout,
        )
        require(
            "'mapped':" in report.stderr,
            "Cipher report did not use stderr:\n" + report.stderr,
        )

    print("qps cipher CLI: PASS")


if __name__ == "__main__":
    main()
