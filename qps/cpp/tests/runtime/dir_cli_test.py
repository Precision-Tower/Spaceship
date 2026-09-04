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
        root = pathlib.Path(tmp) / "surface"
        root.mkdir()

        (root / "alpha.txt").write_text("a")
        (root / "zeta.txt").write_text("z")

        child = root / "child"
        child.mkdir()
        (child / "beta.txt").write_text("b")

        grand = child / "grand"
        grand.mkdir()
        (grand / "gamma.txt").write_text("g")

        result = run(qps, "dir", str(root), "0")

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            result.stdout == "surface.\n\n",
            f"depth 0 mismatch: {result.stdout!r}",
        )

        result = run(qps, "dir", str(root), "1")

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            result.stdout ==
            "surface.\n"
            "alpha.txt-;"
            "child:()"
            "zeta.txt-;\n\n",
            f"depth 1 mismatch: {result.stdout!r}",
        )

        result = run(qps, "dir", str(root), "2")

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            result.stdout ==
            "surface.\n"
            "alpha.txt-;"
            "child:("
            "beta.txt-;"
            "grand:()"
            ")"
            "zeta.txt-;\n\n",
            f"depth 2 mismatch: {result.stdout!r}",
        )

        result = run(qps, "dir", str(root))

        require(
            result.returncode == 0,
            result.stderr,
        )

        require(
            result.stdout ==
            "surface.\n"
            "alpha.txt-;"
            "child:("
            "beta.txt-;"
            "grand:("
            "gamma.txt-;"
            ")"
            ")"
            "zeta.txt-;\n\n",
            f"full tree mismatch: {result.stdout!r}",
        )

        result = run(
            qps,
            "dir",
            str(root / "missing"),
        )

        require(
            result.returncode != 0,
            "missing directory unexpectedly succeeded",
        )

    print("qps dir CLI: PASS")


if __name__ == "__main__":
    main()
