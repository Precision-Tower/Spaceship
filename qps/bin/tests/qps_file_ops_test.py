#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
QPS = ROOT / "qps" / "cpp" / "build-pixel" / "qps"
QPS_FILE = Path(os.environ.get("QPS_FILE_OPS_COMMAND", str(ROOT / "qps" / "bin" / "qps-file")))
TMP_ROOT = ROOT / "trash" / "tmp"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["QPS"] = str(QPS)
    return subprocess.run(
        [str(QPS_FILE), *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_qps(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["QPS"] = str(QPS)
    return subprocess.run(
        [str(QPS), *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def qps_doc(name: str = "Doc") -> str:
    return f"{name}.\n\nvalue- \"ok\";\n"


def make_repo(name: str) -> Path:
    root = TMP_ROOT / f"qps-file-ops-{name}-{os.getpid()}"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    require(git(root, "init").returncode == 0, "git init failed")
    require(git(root, "config", "user.email", "test@example.invalid").returncode == 0, "git config email failed")
    require(git(root, "config", "user.name", "QPS File Ops Test").returncode == 0, "git config name failed")
    write(root / "_index.qps", "ROOT.\n\nqps- \"qps/_index.qps\";\n")
    write(root / "qps" / "_index.qps", "QPS.\n\ncheck- \"ok\";\n")
    return root


def commit_all(root: Path) -> None:
    require(git(root, "add", ".").returncode == 0, "git add failed")
    result = git(root, "commit", "-m", "baseline")
    require(result.returncode == 0, result.stderr)


def check_command_test() -> None:
    root = make_repo("check")
    try:
        write(root / "valid.qps", qps_doc("Valid"))
        write(root / "invalid.qps", ")\n")

        result = run(root, "check", "valid.qps")
        require(result.returncode == 0, result.stderr)
        require("CHECK=PASS" in result.stdout, result.stdout)
        require("surface=qps <file.qps> --check" in result.stdout, result.stdout)

        result = run(root, "check", "invalid.qps")
        require(result.returncode != 0, "invalid QPS unexpectedly passed")
        require("CHECK=FAIL" in result.stderr, result.stderr)

        result = run(root, "check", "missing.qps")
        require(result.returncode != 0, "missing QPS unexpectedly passed")
        require("check target not found" in result.stderr, result.stderr)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def qps_dispatch_smoke_test() -> None:
    root = make_repo("dispatch")
    try:
        write(root / "valid.qps", qps_doc("Valid"))
        write(root / "index.qps", "Index.\n\nref- \"valid.qps\";\n")

        result = run_qps(root, "check", "valid.qps")
        require(result.returncode == 0, result.stderr)
        require("CHECK=PASS" in result.stdout, result.stdout)

        result = run_qps(root, "refs", "valid.qps")
        require(result.returncode == 0, result.stderr)
        require("REFS=PASS" in result.stdout, result.stdout)
        require("count=1" in result.stdout, result.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def tracked_move_test() -> None:
    root = make_repo("tracked")
    try:
        write(root / "docs" / "old.qps", "Old.\n\nself- \"docs/old.qps\";\n")
        write(root / "docs" / "_index.qps", "Docs.\n\nsurface: (\nlocal- \"old.qps\";\nphrase- \"old.qps is not exact\";\n);\n")
        write(
            root / "index.qps",
            "Index.\n\nrefs: (\nprimary- \"docs/old.qps\";\nsimilar- \"docs/old.qps.bak\";\nchild- \"docs/old.qps/child\";\nprefix- \"prefixdocs/old.qps\";\n);\n",
        )
        write(root / "notes.md", "see docs/old.qps\n")
        write(root / "unrelated.txt", "original\n")
        commit_all(root)
        write(root / "unrelated.txt", "user change survives\n")

        result = run(root, "refs", "docs/old.qps")
        require(result.returncode == 0, result.stderr)
        require("count=4" in result.stdout, result.stdout)
        require("docs/old.qps.bak" not in result.stdout, result.stdout)
        require("prefixdocs/old.qps" not in result.stdout, result.stdout)
        require("old.qps is not exact" not in result.stdout, result.stdout)

        cached_before = git(root, "diff", "--cached", "--name-status").stdout
        result = run(root, "move", "docs/old.qps", "docs/new.qps")
        require(result.returncode == 0, result.stdout + result.stderr)
        require("MOVE=PASS" in result.stdout, result.stdout)
        require("source_state=tracked" in result.stdout, result.stdout)
        require("index=unchanged" in result.stdout, result.stdout)
        require("references_updated=4" in result.stdout, result.stdout)
        require(cached_before == git(root, "diff", "--cached", "--name-status").stdout, "Git index changed")

        require(not (root / "docs" / "old.qps").exists(), "old file still exists")
        require((root / "docs" / "new.qps").is_file(), "new file missing")
        index = (root / "index.qps").read_text(encoding="utf-8")
        notes = (root / "notes.md").read_text(encoding="utf-8")
        docs_index = (root / "docs" / "_index.qps").read_text(encoding="utf-8")
        moved = (root / "docs" / "new.qps").read_text(encoding="utf-8")
        require('primary- "docs/new.qps";' in index, index)
        require('similar- "docs/old.qps.bak";' in index, index)
        require('child- "docs/old.qps/child";' in index, index)
        require('prefix- "prefixdocs/old.qps";' in index, index)
        require("see docs/new.qps" in notes, notes)
        require('local- "new.qps";' in docs_index, docs_index)
        require('phrase- "old.qps is not exact";' in docs_index, docs_index)
        require('self- "docs/new.qps";' in moved, moved)
        require((root / "unrelated.txt").read_text(encoding="utf-8") == "user change survives\n", "unrelated change lost")

        result = run(root, "refs", "--absent", "docs/old.qps")
        require(result.returncode == 0, result.stderr)
        require("count=0" in result.stdout, result.stdout)

        status = git(root, "status", "--short").stdout
        require(" M unrelated.txt" in status, status)
        require(" D docs/old.qps" in status, status)
        require("?? docs/new.qps" in status, status)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def untracked_move_test() -> None:
    root = make_repo("untracked")
    try:
        write(root / "index.qps", "Index.\n\nref- \"scratch/old.qps\";\n")
        commit_all(root)
        write(root / "scratch" / "old.qps", qps_doc("Old"))

        result = run(root, "move", "scratch/old.qps", "scratch/new.qps")
        require(result.returncode == 0, result.stdout + result.stderr)
        require("source_state=untracked" in result.stdout, result.stdout)
        require("references_updated=1" in result.stdout, result.stdout)
        require(not (root / "scratch" / "old.qps").exists(), "untracked old file still exists")
        require((root / "scratch" / "new.qps").is_file(), "untracked new file missing")
        require('ref- "scratch/new.qps";' in (root / "index.qps").read_text(encoding="utf-8"), "reference not updated")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def failure_tests() -> None:
    root = make_repo("failures")
    try:
        write(root / "docs" / "old.qps", qps_doc("Old"))
        write(root / "docs" / "exists.qps", qps_doc("Exists"))
        commit_all(root)
        old_before = (root / "docs" / "old.qps").read_text(encoding="utf-8")
        existing_before = (root / "docs" / "exists.qps").read_text(encoding="utf-8")

        result = run(root, "move", "docs/missing.qps", "docs/new.qps")
        require(result.returncode != 0, "missing source unexpectedly moved")
        require("move source not found" in result.stderr, result.stderr)
        require(not (root / "docs" / "new.qps").exists(), "missing-source failure created destination")

        result = run(root, "move", "docs/old.qps", "docs/exists.qps")
        require(result.returncode != 0, "existing destination unexpectedly overwritten")
        require("move destination already exists" in result.stderr, result.stderr)
        require((root / "docs" / "old.qps").read_text(encoding="utf-8") == old_before, "source changed after destination failure")
        require((root / "docs" / "exists.qps").read_text(encoding="utf-8") == existing_before, "destination changed after destination failure")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    require(QPS_FILE.is_file(), f"missing qps-file command: {QPS_FILE}")
    require(QPS.is_file(), f"missing qps binary: {QPS}")
    check_command_test()
    qps_dispatch_smoke_test()
    tracked_move_test()
    untracked_move_test()
    failure_tests()
    print("qps/bin qps-file operations: PASS")


if __name__ == "__main__":
    main()
