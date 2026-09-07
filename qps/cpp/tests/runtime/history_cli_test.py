#!/usr/bin/env python3

import subprocess
import sys
import tempfile
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(qps: Path, cwd: Path, *args):
    return subprocess.run(
        [str(qps), *map(str, args)],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: history_cli_test.py <qps>"
        )

    qps = Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        write(
            root / "_index.qps",
            "History_Test_Root.\n",
        )

        write(
            root / "history.qps",
            '''
CE_OS_History.

entries: (

h_1: (
timestamp- "2026-09-06T01:00:00-05:00";
identity- "cipher.dependency_closure";

scope: (
path_1- "Engineering/py/cipher";
path_2- "qps/qps/cipher.qps";
);

summary- "Cipher dependency closure proven.";
);

h_2: (
timestamp- "2026-09-06T02:00:00-05:00";
identity- "workbench.render";

scope: (
path_1- "UI/Workbench";
);

summary- "Workbench rendering proven.";
);

h_3: (
timestamp- "2026-09-06T03:00:00-05:00";
identity- "qps.function_defaults";

scope: (
path_1- "qps/cpp";
path_2- "Engineering/py/cipher";
);

summary- "QPS function defaults proven.";
);

);
''',
        )

        root_view = run(
            qps,
            root,
            "history",
        )

        require(
            root_view.returncode == 0,
            root_view.stderr,
        )

        require(
            "cipher.dependency_closure"
            in root_view.stdout,
            root_view.stdout,
        )
        require(
            "workbench.render"
            in root_view.stdout,
            root_view.stdout,
        )
        require(
            "qps.function_defaults"
            in root_view.stdout,
            root_view.stdout,
        )

        cipher_view = run(
            qps,
            root,
            "history",
            "Engineering/py/cipher",
        )

        require(
            cipher_view.returncode == 0,
            cipher_view.stderr,
        )

        require(
            "cipher.dependency_closure"
            in cipher_view.stdout,
            cipher_view.stdout,
        )
        require(
            "qps.function_defaults"
            in cipher_view.stdout,
            cipher_view.stdout,
        )
        require(
            "workbench.render"
            not in cipher_view.stdout,
            cipher_view.stdout,
        )

        engineering_view = run(
            qps,
            root,
            "history",
            "Engineering",
        )

        require(
            "cipher.dependency_closure"
            in engineering_view.stdout,
            engineering_view.stdout,
        )
        require(
            "qps.function_defaults"
            in engineering_view.stdout,
            engineering_view.stdout,
        )
        require(
            "workbench.render"
            not in engineering_view.stdout,
            engineering_view.stdout,
        )

        workbench_view = run(
            qps,
            root,
            "history",
            "UI/Workbench",
        )

        require(
            "workbench.render"
            in workbench_view.stdout,
            workbench_view.stdout,
        )
        require(
            "cipher.dependency_closure"
            not in workbench_view.stdout,
            workbench_view.stdout,
        )

        # Narrow child query must not inherit broad parent history.
        narrow = run(
            qps,
            root,
            "history",
            "qps/cpp/runtime",
        )

        require(
            "qps.function_defaults"
            not in narrow.stdout,
            narrow.stdout,
        )

    print("qps history CLI: PASS")


if __name__ == "__main__":
    main()
