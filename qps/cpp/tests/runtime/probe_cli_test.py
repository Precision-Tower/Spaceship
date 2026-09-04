#!/usr/bin/env python3

import pathlib
import subprocess
import sys
import tempfile


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def run(qps, *args):
    return subprocess.run(
        [qps, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main():
    qps = sys.argv[1]

    with tempfile.TemporaryDirectory() as tmp:
        source = pathlib.Path(tmp) / "probe.txt"

        source.write_text(
            "".join(
                f"line {i}\n"
                for i in range(1, 31)
            )
        )

        result = run(
            qps,
            "probe",
            str(source),
            "15",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        lines = result.stdout.splitlines()

        require(
            lines[0].endswith("probe.txt:5-25"),
            f"default probe header mismatch: {lines[0]!r}",
        )

        require(
            lines[1] == "5: line 5",
            f"default probe first line mismatch: {lines[1]!r}",
        )

        require(
            lines[-1] == "25: line 25",
            f"default probe last line mismatch: {lines[-1]!r}",
        )

        result = run(
            qps,
            "probe",
            str(source),
            "15",
            "2",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        lines = result.stdout.splitlines()

        require(
            lines[0].endswith("probe.txt:13-17"),
            f"radius probe header mismatch: {lines[0]!r}",
        )

        require(
            lines[1:] == [
                "13: line 13",
                "14: line 14",
                "15: line 15",
                "16: line 16",
                "17: line 17",
            ],
            f"radius probe body mismatch: {lines[1:]!r}",
        )

        result = run(
            qps,
            "probe",
            str(source),
            "1",
            "3",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        lines = result.stdout.splitlines()

        require(
            lines[0].endswith("probe.txt:1-4"),
            f"lower-bound probe mismatch: {lines[0]!r}",
        )

        result = run(
            qps,
            "probe",
            str(source),
            "31",
        )

        require(
            result.returncode != 0,
            "out-of-range probe unexpectedly succeeded",
        )

    print("qps probe CLI: PASS")


if __name__ == "__main__":
    main()
