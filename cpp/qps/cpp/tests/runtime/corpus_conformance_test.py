#!/usr/bin/env python3

from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(os.environ.get("CEOS_ROOT", str(Path.home() / "ce-os")))
QPS = Path(
    os.environ.get(
        "QPS_EXECUTABLE",
        str(ROOT / "cpp/qps/cpp/build-pixel/qps"),
    )
)
CORPUS = ROOT / "Engineering/qps"

if not QPS.is_file():
    print(f"ERROR: qps executable missing: {QPS}")
    sys.exit(2)

documents = sorted(
    p for p in CORPUS.rglob("*.qps")
    if "Archive" not in p.parts
)

if not documents:
    print("ERROR: no active Engineering QPS documents found")
    sys.exit(3)

failures = []

for path in documents:
    proc = subprocess.run(
        [str(QPS), str(path), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    rel = path.relative_to(ROOT)

    if proc.returncode == 0:
        print(f"PASS {rel}")
    else:
        print(f"FAIL {rel}")
        failures.append(
            (
                rel,
                proc.returncode,
                proc.stdout.strip(),
                proc.stderr.strip(),
            )
        )

print()
print(f"documents={len(documents)}")
print(f"passed={len(documents) - len(failures)}")
print(f"failed={len(failures)}")

if failures:
    print()
    for rel, rc, out, err in failures:
        print(f"=== {rel} rc={rc} ===")
        if out:
            print(out)
        if err:
            print(err)
    sys.exit(1)

print("QPS ACTIVE CORPUS CONFORMANCE OK")
