#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: source_execution_cli_test.py <qps-executable>"
        )

    qps = pathlib.Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        executable = root / "executable.qps"
        executable.write_text(
            """{Process_Probe:
-process(
program- "printf";
arg_0- "QPS_SOURCE_EXECUTION_OK";
);
}

{>Process_Probe:
}
""",
            encoding="utf-8",
        )

        result = subprocess.run(
            [str(qps), str(executable)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        require(
            result.returncode == 0,
            "executable QPS source failed:\n"
            + result.stdout
            + result.stderr,
        )

        # The process primitive currently captures child stdout rather
        # than forwarding it. The important CLI contract here is that
        # the definition/call executes successfully rather than merely
        # printing an AST.
        require(
            "AST Representation" not in result.stdout
            and "AST Representation" not in result.stderr,
            "executable QPS source was only AST-printed",
        )

        structural = root / "structural.qps"
        structural.write_text(
            """probe.
value- "still structural";
""",
            encoding="utf-8",
        )

        structural_result = subprocess.run(
            [str(qps), str(structural)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        require(
            structural_result.returncode == 0,
            "structural QPS source failed",
        )

        structural_output = (
            structural_result.stdout
            + structural_result.stderr
        )

        require(
            "AST Representation" in structural_output,
            "non-executable QPS source no longer preserves AST behavior",
        )

    print("QPS source execution CLI: PASS")


if __name__ == "__main__":
    main()
