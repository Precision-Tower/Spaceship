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


def source_root_for(qps: Path) -> Path:
    for parent in qps.parents:
        if (parent / "qps/qps/checklist.qps").is_file():
            return parent

    raise AssertionError(
        f"could not resolve CE-OS source root from qps executable: {qps}"
    )


def install_authored_checklist(qps: Path, root: Path):
    source_root = source_root_for(qps)
    checklist_authority = source_root / "qps/qps/checklist.qps"

    write(root / "_authority/_index.qps", "Authority.\n")
    write(
        root / "_authority/policy.qps",
        checklist_authority.read_text(encoding="utf-8"),
    )


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
            "usage: checklist_cli_test.py <qps>"
        )

    qps = Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        write(
            root / "_index.qps",
            '''\
Test_Root.

qps: (
checklist_authority- "_authority/policy.qps";
);
''',
        )
        install_authored_checklist(qps, root)

        for module in ("A", "B", "C", "legacy"):
            write(root / module / "_index.qps", f"{module}.\n")

        write(
            root / "A/checklist.qps",
            '''\
current_work: (
tasks: (
task_1: (
identity- "a.active";
summary- "Active A task";
state- "active";
);

task_2: (
identity- "a.saved";
summary- "Saved A task";
state- "saved";
);
);
);
''',
        )

        write(
            root / "B/checklist.qps",
            '''\
current_work: (
tasks: (
task_1: (
identity- "b.complete";
summary- "Complete B task";
state- "complete";
);
);
);
''',
        )

        write(
            root / "C/checklist.qps",
            '''\
current_work: (
tasks: (
task_1: (
identity- "c.waiting";
summary- "Waiting C task";
state- "waiting";
);

task_2: (
identity- "c.blocked";
summary- "Blocked C task";
state- "blocked";
);
);
);
''',
        )

        # Checklist with no canonical task surface still consumes an index.
        write(
            root / "legacy/checklist.qps",
            '''\
current_work: (
goal- "Legacy work";
);
''',
        )

        result = run(
            qps,
            root,
            "checklist",
        )

        require(
            result.returncode == 0,
            result.stderr,
        )

        require("1.task_1   active" in result.stdout, result.stdout)
        require("A/checklist.qps" in result.stdout, result.stdout)
        require("a.active" in result.stdout, result.stdout)
        require("Active A task" in result.stdout, result.stdout)

        require("2.task_1   complete" in result.stdout, result.stdout)
        require("B/checklist.qps" in result.stdout, result.stdout)
        require("b.complete" in result.stdout, result.stdout)
        require("Complete B task" in result.stdout, result.stdout)

        require("3.task_1   waiting" in result.stdout, result.stdout)
        require("3.task_2   blocked" in result.stdout, result.stdout)
        require("C/checklist.qps" in result.stdout, result.stdout)
        require("Waiting C task" in result.stdout, result.stdout)
        require("Blocked C task" in result.stdout, result.stdout)

        require("4   DONE   legacy/checklist.qps" in result.stdout, result.stdout)
        require("Saved A task" not in result.stdout, result.stdout)
        require("Legacy work" not in result.stdout, result.stdout)

        selected_checklist = run(
            qps,
            root,
            "checklist",
            "1",
        )

        require(
            selected_checklist.returncode == 0,
            selected_checklist.stderr,
        )
        require("1.task_1   active" in selected_checklist.stdout, selected_checklist.stdout)
        require("Active A task" in selected_checklist.stdout, selected_checklist.stdout)
        require("Complete B task" not in selected_checklist.stdout, selected_checklist.stdout)
        require("Waiting C task" not in selected_checklist.stdout, selected_checklist.stdout)

        selected_task = run(
            qps,
            root,
            "checklist",
            "3",
            "2",
        )

        require(
            selected_task.returncode == 0,
            selected_task.stderr,
        )
        require("3.task_2   C/checklist.qps:" in selected_task.stdout, selected_task.stdout)
        require('identity- "c.blocked";' in selected_task.stdout, selected_task.stdout)
        require('summary- "Blocked C task";' in selected_task.stdout, selected_task.stdout)
        require('state- "blocked";' in selected_task.stdout, selected_task.stdout)

    print("qps checklist CLI: PASS")


if __name__ == "__main__":
    main()
