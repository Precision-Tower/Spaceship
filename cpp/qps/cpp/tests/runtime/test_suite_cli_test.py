#!/usr/bin/env python3

from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(os.environ.get("CEOS_ROOT", str(Path.home() / "ce-os")))
QPS = Path(
    os.environ.get(
        "QPS_EXECUTABLE",
        str(ROOT / "cpp/qps/cpp/build-pixel/qps"),
    )
)


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def require(condition, message):
    if not condition:
        fail(message)


def write_qps(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def run_qps_test(target):
    return subprocess.run(
        [str(QPS), "test", str(target)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def require_process(proc, returncode, stdout, stderr, label):
    require(
        proc.returncode == returncode,
        f"{label}: expected return code {returncode}, got {proc.returncode}; "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}",
    )
    require(
        proc.stdout == stdout,
        f"{label}: unexpected stdout {proc.stdout!r}, expected {stdout!r}",
    )
    require(
        proc.stderr == stderr,
        f"{label}: unexpected stderr {proc.stderr!r}, expected {stderr!r}",
    )


def main():
    require(QPS.is_file(), f"qps executable missing: {QPS}")

    tmp_parent = Path.home() / "tmp"
    tmp_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="qps_test_suite_cli_",
        dir=tmp_parent,
    ) as tmp_name:
        root = Path(tmp_name)

        no_tests = root / "no_tests.qps"
        write_qps(
            no_tests,
            [
                "example.",
                'value- "valid qps";',
            ],
        )
        require_process(
            run_qps_test(no_tests),
            0,
            f"{no_tests}: PASS\n",
            "",
            "valid qps without embedded tests passes",
        )

        single_pass = root / "single_pass.qps"
        write_qps(
            single_pass,
            [
                "tests.",
                "truth: -test {",
                "-assert true;",
                "};",
            ],
        )
        require_process(
            run_qps_test(single_pass),
            0,
            f"{single_pass}: PASS\n",
            "",
            "single file success is quiet",
        )

        rich_pass = root / "rich_pass.qps"
        write_qps(
            rich_pass,
            [
                "-func add(",
                "left-/n;",
                "right-/n;",
                ") {",
                "%sum: left + right",
                "-return sum;",
                "}",
                "",
                "tests.",
                "math: -test {",
                "%answer: add(2, 3)",
                "-assert answer == 5;",
                "};",
                "raises: -test {",
                "-raises \"Undefined execution value\" {",
                "-assert missing == 1;",
                "};",
                "};",
            ],
        )
        require_process(
            run_qps_test(rich_pass),
            0,
            f"{rich_pass}: PASS\n",
            "",
            "calculations functions and raises pass quietly",
        )

        single_fail = root / "single_fail.qps"
        write_qps(
            single_fail,
            [
                "tests.",
                "bad: -test {",
                "-assert false;",
                "};",
            ],
        )
        require_process(
            run_qps_test(single_fail),
            1,
            f"{single_fail}: FAIL\n{single_fail}:3 assertion failed\n",
            "",
            "single file failure reports exact line",
        )

        success_dir = root / "success_dir"
        success_a = success_dir / "a.qps"
        success_b = success_dir / "nested" / "b.qps"
        write_qps(
            success_a,
            [
                "tests.",
                "a: -test {",
                "-assert true;",
                "};",
            ],
        )
        write_qps(
            success_b,
            [
                "tests.",
                "b: -test {",
                "%answer: 2 + 2",
                "-assert answer == 4;",
                "};",
            ],
        )
        require_process(
            run_qps_test(success_dir),
            0,
            f"{success_dir}: PASS (2 files)\n",
            "",
            "folder success collapses to one summary line",
        )

        mixed_dir = root / "mixed_dir"
        mixed_pass = mixed_dir / "a_pass.qps"
        mixed_fail = mixed_dir / "z_fail.qps"
        write_qps(
            mixed_pass,
            [
                "tests.",
                "ok: -test {",
                "-assert true;",
                "};",
            ],
        )
        write_qps(
            mixed_fail,
            [
                "tests.",
                "bad: -test {",
                "-fail \"folder failure\";",
                "};",
            ],
        )
        require_process(
            run_qps_test(mixed_dir),
            1,
            f"{mixed_fail}:3 folder failure\n"
            f"{mixed_dir}: FAIL\n",
            "",
            "folder failure reports only failing files plus folder summary",
        )

    print("PASS qps testSuite CLI")


if __name__ == "__main__":
    main()
