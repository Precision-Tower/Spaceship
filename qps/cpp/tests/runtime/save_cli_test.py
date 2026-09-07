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


def source_root_for(qps: Path) -> Path:
    for parent in qps.parents:
        if (parent / "qps/qps/save.qps").is_file():
            return parent

    raise AssertionError(
        f"could not resolve CE-OS source root from qps executable: {qps}"
    )


def install_authorities(qps: Path, root: Path):
    source_root = source_root_for(qps)

    write(
        root / "_authority/_index.qps",
        "Authority.\n",
    )

    write(
        root / "_authority/save.qps",
        (source_root / "qps/qps/save.qps").read_text(
            encoding="utf-8"
        ),
    )

    write(
        root / "_authority/checklist.qps",
        (source_root / "qps/qps/checklist.qps").read_text(
            encoding="utf-8"
        ),
    )


def completed_task(identity="test.saved_capability"):
    return (
        'task_1: (\n'
        f'identity- "{identity}";\n'
        'summary- "A capability was proven";\n'
        'meaning- "This is the semantic meaning";\n'
        'state- "complete";\n'
        '\n'
        'scope: (\n'
        'path_1- "A";\n'
        'path_2- "qps/qps";\n'
        ');\n'
        '\n'
        'proof: (\n'
        'focused- "PASS";\n'
        ');\n'
        '\n'
        'relevant: (\n'
        'path_1- "A/checklist.qps";\n'
        ');\n'
        '\n'
        'remaining: (\n'
        'item_1- "Future work remains";\n'
        ');\n'
        '\n'
        'documentation: (\n'
        'required- false;\n'
        'state- "complete";\n'
        ');\n'
        ');\n'
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: save_cli_test.py <qps>"
        )

    qps = Path(sys.argv[1]).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        install_authorities(qps, root)

        write(
            root / "_index.qps",
            (
                "Save_Test_Root.\n"
                "\n"
                "qps: (\n"
                'checklist_authority- "_authority/checklist.qps";\n'
                'save_authority- "_authority/save.qps";\n'
                ");\n"
            ),
        )

        write(
            root / "history.qps",
            (
                "CE_OS_History.\n"
                "\n"
                "entries: (\n"
                ");\n"
            ),
        )

        write(
            root / "A/_index.qps",
            "A.\n",
        )

        checklist = root / "A/checklist.qps"

        write(
            checklist,
            (
                "current_work: (\n"
                "tasks: (\n"
                + completed_task()
                + "\n"
                "task_2: (\n"
                'identity- "test.unrelated";\n'
                'summary- "Unrelated";\n'
                'state- "waiting";\n'
                ");\n"
                ");\n"
                ");\n"
            ),
        )

        listing = run(
            qps,
            root,
            "checklist",
        )

        require(
            listing.returncode == 0,
            listing.stderr,
        )

        require(
            "1.task_1   complete" in listing.stdout,
            listing.stdout,
        )

        require(
            "test.saved_capability" in listing.stdout,
            listing.stdout,
        )

        before_history = (
            root / "history.qps"
        ).read_bytes()

        first = run(
            qps,
            root,
            "save",
            "1",
            "1",
        )

        require(
            first.returncode == 0,
            first.stderr,
        )

        require(
            "SAVE=PASS" in first.stdout,
            first.stdout,
        )

        after_checklist = checklist.read_text(
            encoding="utf-8"
        )

        require(
            'identity- "test.saved_capability";'
            not in after_checklist,
            after_checklist,
        )

        require(
            'identity- "test.unrelated";'
            in after_checklist,
            after_checklist,
        )

        after_history = (
            root / "history.qps"
        ).read_text(encoding="utf-8")

        require(
            'identity- "test.saved_capability";'
            in after_history,
            after_history,
        )

        require(
            'summary- "A capability was proven";'
            in after_history,
            after_history,
        )

        require(
            after_history.encode("utf-8") !=
            before_history,
            "Successful Save did not mutate History",
        )

        history = run(
            qps,
            root,
            "history",
            "A",
        )

        require(
            history.returncode == 0,
            history.stderr,
        )

        require(
            "test.saved_capability" in history.stdout,
            history.stdout,
        )

        # After task_1 is removed, task_2 remains authored as task_2.
        # Reusing the old indexed address must not modify either file.
        before_stale_history = (
            root / "history.qps"
        ).read_bytes()

        before_stale_checklist = (
            checklist.read_bytes()
        )

        stale = run(
            qps,
            root,
            "save",
            "1",
            "1",
        )

        require(
            stale.returncode != 0,
            "Stale indexed Save unexpectedly succeeded",
        )

        require(
            before_stale_history ==
            (root / "history.qps").read_bytes(),
            "Stale Save modified History",
        )

        require(
            before_stale_checklist ==
            checklist.read_bytes(),
            "Stale Save modified Checklist",
        )

        # True duplicate semantic identity: a completed task still exists,
        # but History already owns that semantic identity. Save must reject
        # before publication and preserve both authorities byte-for-byte.
        duplicate_root = root / "duplicate"
        install_authorities(qps, duplicate_root)

        write(
            duplicate_root / "_index.qps",
            (
                "Save_Test_Root.\n"
                "\n"
                "qps: (\n"
                'checklist_authority- "_authority/checklist.qps";\n'
                'save_authority- "_authority/save.qps";\n'
                ");\n"
            ),
        )

        write(
            duplicate_root / "A/_index.qps",
            "A.\n",
        )

        duplicate_checklist = duplicate_root / "A/checklist.qps"
        write(
            duplicate_checklist,
            (
                "current_work: (\n"
                "tasks: (\n"
                + completed_task("test.duplicate_identity")
                + ");\n"
                ");\n"
            ),
        )

        write(
            duplicate_root / "history.qps",
            (
                "CE_OS_History.\n"
                "\n"
                "entries: (\n"
                "h_existing: (\n"
                'timestamp- "2026-01-01T00:00:00Z";\n'
                'identity- "test.duplicate_identity";\n'
                'summary- "Already accepted";\n'
                'meaning- "Existing accepted semantic identity";\n'
                "scope: (\n"
                'path_1- "A";\n'
                ");\n"
                "proof: (\n"
                'focused- "PASS";\n'
                ");\n"
                "relevant: (\n"
                'path_1- "A/checklist.qps";\n'
                ");\n"
                "remaining: (\n"
                'item_1- "None";\n'
                ");\n"
                'source_checklist- "A/checklist.qps";\n'
                'backing_state- "";\n'
                ");\n"
                ");\n"
            ),
        )

        before_duplicate_history = (
            duplicate_root / "history.qps"
        ).read_bytes()
        before_duplicate_checklist = (
            duplicate_checklist.read_bytes()
        )

        duplicate = run(
            qps,
            duplicate_root,
            "save",
            "1",
            "1",
        )

        require(
            duplicate.returncode != 0,
            "True duplicate semantic identity Save unexpectedly succeeded",
        )
        require(
            before_duplicate_history ==
            (duplicate_root / "history.qps").read_bytes(),
            "Duplicate semantic identity modified History",
        )
        require(
            before_duplicate_checklist ==
            duplicate_checklist.read_bytes(),
            "Duplicate semantic identity modified Checklist",
        )

        # Saving authored task_2 must fail because it is incomplete.
        before_incomplete_history = (
            root / "history.qps"
        ).read_bytes()

        before_incomplete_checklist = (
            checklist.read_bytes()
        )

        incomplete = run(
            qps,
            root,
            "save",
            "1",
            "2",
        )

        require(
            incomplete.returncode != 0,
            "Incomplete Save unexpectedly succeeded",
        )

        require(
            before_incomplete_history ==
            (root / "history.qps").read_bytes(),
            "Incomplete Save modified History",
        )

        require(
            before_incomplete_checklist ==
            checklist.read_bytes(),
            "Incomplete Save modified Checklist",
        )

        # Malformed public addresses fail before authority mutation.
        for args in (
            ("save", "0", "1"),
            ("save", "1", "0"),
            ("save", "x", "1"),
            ("save", "1", "x"),
            ("save", "1"),
        ):
            before_history_bytes = (
                root / "history.qps"
            ).read_bytes()

            before_checklist_bytes = (
                checklist.read_bytes()
            )

            result = run(
                qps,
                root,
                *args,
            )

            require(
                result.returncode != 0,
                f"Malformed Save unexpectedly succeeded: {args}",
            )

            require(
                before_history_bytes ==
                (root / "history.qps").read_bytes(),
                f"Malformed Save modified History: {args}",
            )

            require(
                before_checklist_bytes ==
                checklist.read_bytes(),
                f"Malformed Save modified Checklist: {args}",
            )

    print(
        "qps save CLI indexed lifecycle: PASS"
    )


if __name__ == "__main__":
    main()
