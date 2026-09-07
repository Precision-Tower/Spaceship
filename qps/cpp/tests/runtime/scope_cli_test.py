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
        source = pathlib.Path(tmp) / "scope.qps"

        source.write_text(
            "Root.\n"
            "system: (\n"
            "first- 1/n;\n"
            "nested: (\n"
            "inside- 2/n;\n"
            ");\n"
            "second- 3/n;\n"
            ");\n"
        )

        result = run(
            qps,
            "scope",
            str(source),
            "Root.system",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        lines = result.stdout.splitlines()

        require(
            lines[0].endswith("scope.qps:2-8"),
            f"scope header mismatch: {lines[0]!r}",
        )

        require(
            lines[1:] == [
                "2: system: (",
                "3: first- 1/n;",
                "4: nested: (",
                "5: inside- 2/n;",
                "6: );",
                "7: second- 3/n;",
                "8: );",
            ],
            f"scope owned span mismatch: {lines[1:]!r}",
        )

        # Scope renders the complete physical source owned by the
        # selected structural address. Nested authored source therefore
        # remains visible when it lies inside that owned span.
        require(
            "5: inside- 2/n;" in result.stdout,
            "scope omitted nested source owned by selected Term",
        )

        # Item targets have no structural children.
        result = run(
            qps,
            "scope",
            str(source),
            "Root.system.first-",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        lines = result.stdout.splitlines()

        require(
            lines[0].endswith("scope.qps:3"),
            f"item scope header mismatch: {lines[0]!r}",
        )

        require(
            lines[1:] == ["3: first- 1/n;"],
            f"item scope body mismatch: {lines[1:]!r}",
        )

        # Missing structural coordinates fail explicitly.
        result = run(
            qps,
            "scope",
            str(source),
            "Root.system.missing-",
        )

        require(
            result.returncode != 0,
            "missing scope path unexpectedly succeeded",
        )

        # Scope is parser-aware and QPS-specific.
        plain = pathlib.Path(tmp) / "plain.txt"
        plain.write_text("hello\n")

        result = run(
            qps,
            "scope",
            str(plain),
            "anything",
        )

        require(
            result.returncode != 0,
            "non-QPS scope unexpectedly succeeded",
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
            "scope",
            str(key_span_source),
            "alpha",
        )

        require(
            key_span.returncode == 0,
            "scope Key span failed:\n"
            + key_span.stderr,
        )

        require(
            "item- 1;" in key_span.stdout,
            "scope Key span omitted owned content",
        )

        require(
            "beta." not in key_span.stdout,
            "scope Key span crossed paragraph boundary",
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
            "scope",
            structural_source,
            "alpha.dimensions",
        )

        require(
            term_span.returncode == 0,
            "scope Term span failed:\n"
            + term_span.stderr,
        )

        require(
            "dimensions: (" in term_span.stdout
            and "radius- 5/in;" in term_span.stdout
            and "width- 8/in;" in term_span.stdout
            and ");" in term_span.stdout,
            "scope Term span omitted owned source",
        )

        require(
            'material- "steel";' not in term_span.stdout,
            "scope Term span crossed its terminator",
        )

        item_span = run(
            qps,
            "scope",
            structural_source,
            "alpha.dimensions.radius-",
        )

        require(
            item_span.returncode == 0,
            "scope Item span failed:\n"
            + item_span.stderr,
        )

        require(
            "radius- 5/in;" in item_span.stdout,
            "scope Item span omitted owned source",
        )

        require(
            "width- 8/in;" not in item_span.stdout,
            "scope Item span crossed its terminator",
        )

    print("qps scope CLI: PASS")


if __name__ == "__main__":
    main()
