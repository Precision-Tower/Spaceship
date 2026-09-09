#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: geminigo_cli_test.py <qps>")

qps = Path(sys.argv[1]).resolve()

def run(*args):
    return subprocess.run(
        [str(qps), *args],
        text=True,
        capture_output=True,
    )

check = run("GeminiGo", "check")
assert check.returncode == 0, check.stderr
assert "GeminiGo" in check.stdout
assert "Thing 1" in check.stdout
assert "Thing 2" in check.stdout
assert "api_key" not in check.stdout.lower()

thing = run("GeminiGo", "thing", "1")
assert thing.returncode == 0, thing.stderr
assert '"credential_slot": "primary"' in thing.stdout

work = run("GeminiGo", "work")
assert work.returncode == 0, work.stderr
assert '"assignment"' in work.stdout

status = run("GeminiGo", "status", "--json")
assert status.returncode == 0, status.stderr
assert '"thing_1"' in status.stdout
assert '"thing_2"' in status.stdout

lower = run("geminigo", "check")
assert lower.returncode == 0, lower.stderr
assert "Thing 1" in lower.stdout
