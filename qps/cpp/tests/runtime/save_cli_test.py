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
        raise SystemExit("usage: save_cli_test.py <qps>")

    qps = Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        write(
            root / "_index.qps",
            "Save_Test_Root.\n",
        )

        write(
            root / "history.qps",
            '''
CE_OS_History.

entries: (
);
''',
        )

        checklist = root / "qps/qps/checklist.qps"

        write(
            checklist,
            '''
current_work: (

history_candidate: (
ready- true;
state- "ready";
history_identity- "";
history_timestamp- "";
identity- "test.saved_capability";
summary- "A capability was proven";
meaning- "This is the semantic meaning";

scope: (
path_1- "qps/qps";
path_2- "qps/cpp";
);

proof: (
focused- "PASS";
);

relevant: (
path_1- "qps/qps/checklist.qps";
);

remaining: (
item_1- "Future work remains";
);

tasks: (
task_1- "test.task";
);
);

tasks: (
task_1: (
identity- "test.task";
summary- "Test task";
state- "complete";
);
);

);
''',
        )

        first = run(
            qps,
            root,
            "save",
            checklist,
        )

        require(
            first.returncode == 0,
            first.stderr,
        )

        require(
            "SAVE=PASS"
            in first.stdout,
            first.stdout,
        )

        history = run(
            qps,
            root,
            "history",
            "qps/qps",
        )

        require(
            history.returncode == 0,
            history.stderr,
        )

        require(
            "test.saved_capability"
            in history.stdout,
            history.stdout,
        )

        require(
            "A capability was proven"
            in history.stdout,
            history.stdout,
        )

        saved_checklist = checklist.read_text(
            encoding="utf-8"
        )

        require(
            "ready- false;"
            in saved_checklist,
            saved_checklist,
        )

        require(
            'state- "saved";'
            in saved_checklist,
            saved_checklist,
        )

        require(
            'history_identity- "test.saved_capability";'
            in saved_checklist,
            saved_checklist,
        )

        require(
            'identity- "test.task";\n'
            'summary- "Test task";\n'
            'state- "saved";'
            in saved_checklist,
            saved_checklist,
        )

        before_duplicate = (
            root / "history.qps"
        ).read_text(encoding="utf-8")

        duplicate = run(
            qps,
            root,
            "save",
            checklist,
        )

        require(
            duplicate.returncode != 0,
            "Duplicate save unexpectedly succeeded",
        )

        require(
            "not ready"
            in duplicate.stderr,
            duplicate.stderr,
        )

        after_duplicate = (
            root / "history.qps"
        ).read_text(encoding="utf-8")

        require(
            before_duplicate == after_duplicate,
            "Duplicate save modified history.qps",
        )

        blocked = root / "blocked/checklist.qps"

        write(
            blocked,
            '''
current_work: (
history_candidate: (
ready- false;
identity- "test.blocked";
summary- "Blocked";
meaning- "Not ready";
scope: (
path_1- "blocked";
);
proof: (
status- "FAIL";
);
relevant: (
path_1- "blocked/checklist.qps";
);
remaining: (
item_1- "Not ready";
);
);
);
''',
        )

        before_blocked = (
            root / "history.qps"
        ).read_text(encoding="utf-8")

        blocked_result = run(
            qps,
            root,
            "save",
            blocked,
        )

        require(
            blocked_result.returncode != 0,
            "Unready save unexpectedly succeeded",
        )

        require(
            before_blocked ==
            (root / "history.qps").read_text(
                encoding="utf-8"
            ),
            "Unready save modified history.qps",
        )

    print("qps save CLI: PASS")


if __name__ == "__main__":
    main()
