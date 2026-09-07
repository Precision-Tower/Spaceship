#!/usr/bin/env python3
import os

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

        semantic = pathlib.Path(tmp) / "semantic.qps"
        semantic.write_text(
            "Probe.\n"
            "system: (\n"
            "shaft_torque- 10/n;\n"
            "nested: (\n"
            "speed- 20/n;\n"
            ");\n"
            ");\n"
        )

        result = run(
            qps,
            "probe",
            str(semantic),
            "Probe.system.shaft_torque-",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        lines = result.stdout.splitlines()

        require(
            lines[0].endswith("semantic.qps:3"),
            f"semantic probe header mismatch: {lines[0]!r}",
        )

        require(
            lines[1:] == ["3: shaft_torque- 10/n;"],
            f"semantic probe body mismatch: {lines[1:]!r}",
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


        key_span_root = tempfile.mkdtemp(
            prefix="qps-key-span-"
        )
        key_span_source = os.path.join(
            key_span_root,
            "key-span.qps",
        )

        with open(
            key_span_source,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                "alpha.\n"
                "item- 1;\n"
                "\n"
                "beta.\n"
                "item- 2;\n"
            )

        key_span = run(
            qps,
            "probe",
            str(key_span_source),
            "alpha",
        )

        require(
            key_span.returncode == 0,
            "probe Key span failed:\n"
            + key_span.stderr,
        )

        require(
            "item- 1;" in key_span.stdout,
            "probe Key span omitted owned content",
        )

        require(
            "beta." not in key_span.stdout,
            "probe Key span crossed paragraph boundary",
        )

        structural_source = os.path.join(
            key_span_root,
            "structural-span.qps",
        )

        with open(
            structural_source,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                "alpha.\n"
                "dimensions: (\n"
                "radius- 5/in;\n"
                "width- 8/in;\n"
                ");\n"
                "material- \"steel\";\n"
                "\n"
                "beta.\n"
                "item- 2;\n"
            )

        term_span = run(
            qps,
            "probe",
            structural_source,
            "alpha.dimensions",
        )

        require(
            term_span.returncode == 0,
            "probe Term span failed:\n"
            + term_span.stderr,
        )

        require(
            "dimensions: (" in term_span.stdout
            and "radius- 5/in;" in term_span.stdout
            and "width- 8/in;" in term_span.stdout
            and ");" in term_span.stdout,
            "probe Term span omitted owned source",
        )

        require(
            'material- "steel";' not in term_span.stdout,
            "probe Term span crossed its terminator",
        )

        item_span = run(
            qps,
            "probe",
            structural_source,
            "alpha.dimensions.radius-",
        )

        require(
            item_span.returncode == 0,
            "probe Item span failed:\n"
            + item_span.stderr,
        )

        require(
            "radius- 5/in;" in item_span.stdout,
            "probe Item span omitted owned source",
        )

        require(
            "width- 8/in;" not in item_span.stdout,
            "probe Item span crossed its terminator",
        )

    print("qps probe CLI: PASS")


if __name__ == "__main__":
    main()
