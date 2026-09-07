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
        root = pathlib.Path(tmp) / "module"
        root.mkdir()

        (root / "_index.qps").write_text(
            'Index.\n'
            'purpose- "fixture";\n'
        )

        (root / "alpha.qps").write_text(
            "Alpha.\n"
            "target: (\n"
            "value- 1/n;\n"
            ");\n"
        )

        (root / "beta.qps").write_text(
            "Beta.\n"
            "other- 2/n;\n"
        )

        # This contains the same text but not the same structural identity.
        (root / "text_only.qps").write_text(
            'TextOnly.\n'
            'description- "target";\n'
        )

        # Child module must remain outside this scout boundary.
        child = root / "child"
        child.mkdir()

        (child / "_index.qps").write_text(
            "ChildIndex.\n"
        )

        (child / "hidden.qps").write_text(
            "Hidden.\n"
            "target: (\n"
            "value- 99/n;\n"
            ");\n"
        )

        result = run(
            qps,
            "scout",
            str(root),
            "target",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        lines = result.stdout.splitlines()

        require(
            len(lines) == 2,
            f"unexpected scout output: {lines!r}",
        )

        require(
            lines[0] == "alpha.qps:2",
            f"scout path mismatch: {lines[0]!r}",
        )

        require(
            lines[1] == "2: target: (",
            f"scout source mismatch: {lines[1]!r}",
        )

        require(
            "hidden.qps" not in result.stdout,
            "scout descended into child module",
        )

        require(
            "text_only.qps" not in result.stdout,
            "scout used textual rather than structural matching",
        )

        # Named execution definitions own authored structural identity.
        (root / "execution.qps").write_text(
            "{Fixture_Execution:\n"
            "}\n"
        )

        result = run(
            qps,
            "scout",
            str(root),
            "Fixture_Execution",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            result.stdout.splitlines() == [
                "execution.qps:1",
                "1: {Fixture_Execution:",
            ],
            f"execution-definition scout mismatch: {result.stdout!r}",
        )

        # A parser-incompatible sibling must not erase valid structural
        # evidence from other documents in the same indexed module.
        (root / "broken.qps").write_text(
            "{Broken:\n"
            "-while thing {\n"
            "}\n"
            "}\n"
        )

        result = run(
            qps,
            "scout",
            str(root),
            "target",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            "alpha.qps:2" in result.stdout,
            f"broken sibling erased valid scout result: {result.stdout!r}",
        )

        require(
            "broken.qps" not in result.stdout,
            "broken document leaked into source evidence",
        )

        # _index.qps itself is not part of qpsFiles(module).
        result = run(
            qps,
            "scout",
            str(root),
            "purpose",
        )

        require(
            result.returncode != 0,
            "scout unexpectedly searched _index.qps",
        )

        # The module's _index.qps is also accepted as the boundary handle.
        result = run(
            qps,
            "scout",
            str(root / "_index.qps"),
            "target",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            "alpha.qps:2" in result.stdout,
            "index-file module handle failed",
        )

        # Document structure may be searched recursively because the
        # indexed module already bounded which physical documents scout
        # is allowed to inspect.
        (root / "nested.qps").write_text(
            "Nested.\n"
            "outer: (\n"
            "deep- 7/n;\n"
            ");\n"
        )

        result = run(
            qps,
            "scout",
            str(root),
            "deep",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            "nested.qps:3" in result.stdout,
            f"nested structural identity missing: {result.stdout!r}",
        )

        require(
            "3: deep- 7/n;" in result.stdout,
            f"nested structural source missing: {result.stdout!r}",
        )

    print("qps scout CLI: PASS")


if __name__ == "__main__":
    main()
