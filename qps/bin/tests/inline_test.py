#!/usr/bin/env python3

from __future__ import annotations

import os
import pathlib
import sys
import shutil


ROOT = pathlib.Path(__file__).resolve().parents[3]
INLINE = ROOT / "qps" / "bin" / "inline"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_inline():
    sys.path.insert(0, str(ROOT / "qps" / "bin"))
    try:
        import inline_lib
        return inline_lib
    finally:
        sys.path.pop(0)


def extraction_tests() -> None:
    inline = load_inline()

    require(
        inline.extract_source('[< probe. value- "ok";]') ==
        ' probe. value- "ok";',
        "single-line extraction failed",
    )

    require(
        inline.extract_source(
            '[<\nprobe.\nvalue- "multi";\n]'
        ) == '\nprobe.\nvalue- "multi";\n',
        "multiline extraction failed",
    )

    require(
        inline.extract_source(
            '[< probe. value- "] literal";]'
        ) == ' probe. value- "] literal";',
        "quoted closing bracket terminated surface",
    )

    require(
        inline.extract_source(
            '[< probe. values- [1, 2, 3];]'
        ) == ' probe. values- [1, 2, 3];',
        "nested QPS container terminated surface",
    )

    require(
        inline.extract_source(
            '[< {Probe:\n-return "ok";\n}\n]'
        ) == ' {Probe:\n-return "ok";\n}\n',
        "execution braces terminated surface",
    )

    for bad in (
        'probe. value- "x";]',
        '[< probe. value- "x";',
        '[< probe. value- "x";] trailing',
    ):
        try:
            inline.extract_source(bad)
        except inline.InlineError:
            pass
        else:
            raise AssertionError(f"expected boundary rejection: {bad!r}")


def run_inline(
    cwd: pathlib.Path,
    surface: str,
    env: dict[str, str],
    name: str,
) -> tuple[int, str, str]:
    stdout_path = cwd / f"{name}.stdout"
    stderr_path = cwd / f"{name}.stderr"

    pid = os.fork()

    if pid == 0:
        try:
            os.chdir(cwd)

            stdout_fd = os.open(
                stdout_path,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )
            stderr_fd = os.open(
                stderr_path,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )

            os.dup2(stdout_fd, 1)
            os.dup2(stderr_fd, 2)

            os.close(stdout_fd)
            os.close(stderr_fd)

            child_env = os.environ.copy()
            child_env.update(env)

            os.execve(
                str(INLINE),
                [str(INLINE), surface],
                child_env,
            )
        except BaseException:
            os._exit(127)

    _, status = os.waitpid(pid, 0)
    returncode = os.waitstatus_to_exitcode(status)

    stdout = (
        stdout_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        if stdout_path.exists()
        else ""
    )

    stderr = (
        stderr_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        if stderr_path.exists()
        else ""
    )

    return returncode, stdout, stderr


def execution_tests() -> None:
    cwd = ROOT / "trash" / "tmp" / (
        "qps-inline-test-" + str(os.getpid())
    )

    shutil.rmtree(cwd, ignore_errors=True)
    cwd.mkdir(parents=True)

    try:
        env = {
            "QPS": str(
                ROOT / "qps" / "cpp" / "build-pixel" / "qps"
            )
        }

        surface = """[<
{Inline_Probe:
-process(
program- "sh";
arg_0- "-c";
arg_1- "pwd > inline-cwd.txt";
);
}

{>Inline_Probe:
}
]"""

        rc, stdout, stderr = run_inline(
            cwd,
            surface,
            env,
            "good",
        )

        require(
            rc == 0,
            "inline execution failed:\n"
            + stdout
            + stderr,
        )

        witness = cwd / "inline-cwd.txt"

        require(
            witness.is_file(),
            "inline process did not run",
        )

        require(
            pathlib.Path(
                witness.read_text().strip()
            ) == cwd,
            "inline execution did not inherit terminal cwd",
        )

        require(
            not list(cwd.glob(".qps-inline-*.qps")),
            "transient QPS source leaked into cwd",
        )

        boundary_rc, boundary_stdout, boundary_stderr = (
            run_inline(
                cwd,
                '[< {Broken: ]',
                env,
                "boundary",
            )
        )

        require(
            boundary_rc != 0,
            "inline boundary failure status did not propagate",
        )

        require(
            "QPS_INLINE=FAIL" in boundary_stderr,
            "inline boundary failure did not reach stderr:\n"
            + boundary_stdout
            + boundary_stderr,
        )

        parse_rc, parse_stdout, parse_stderr = run_inline(
            cwd,
            "[< ) ]",
            env,
            "parse",
        )

        require(
            parse_rc != 0,
            "QPS parse failure status did not propagate",
        )

        require(
            "Parsing Error" in (
                parse_stdout + parse_stderr
            ),
            "QPS parser failure evidence missing:\n"
            + parse_stdout
            + parse_stderr,
        )

        require(
            "QPS_INLINE=FAIL" not in (
                parse_stdout + parse_stderr
            ),
            "parser-owned failure was intercepted by bridge",
        )

        require(
            not list(cwd.glob(".qps-inline-*.qps")),
            "failed transient QPS source leaked into cwd",
        )
    finally:
        shutil.rmtree(cwd, ignore_errors=True)


def main() -> None:
    extraction_tests()
    execution_tests()
    print("QPS INLINE CORE TESTS: PASS")


if __name__ == "__main__":
    main()
