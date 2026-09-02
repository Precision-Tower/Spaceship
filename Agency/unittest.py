#!/usr/bin/env python3
"""
Agency validation entrypoint.

Canonical repository validation command:

    python Agency/unittest.py

This intentionally standardizes on Python's built-in unittest
framework rather than pytest.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def run(command: list[str], *, required: bool = True) -> bool:
    print()
    print("$", " ".join(command))
    rc = subprocess.run(command, cwd=ROOT).returncode
    if rc != 0:
        print(f"\nFAILED ({rc})")
        if required:
            raise SystemExit(rc)
        return False
    return True


def main() -> int:
    print("Agency Validation")
    print("-----------------")
    print("Framework : unittest")
    print(f"Repository: {ROOT}")

    banner("Compile Python")
    run([sys.executable, "-m", "compileall", "-q", "Agency"])

    banner("Repository sanity")
    if shutil.which("git"):
        run(["git", "diff", "--check"])

    banner("Core test suite")
    run([
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "Agency/Core",
        "-p",
        "test*.py",
        "-v",
    ])

    banner("Validation complete")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
