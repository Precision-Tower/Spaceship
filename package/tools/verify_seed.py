#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True)
    a = ap.parse_args()

    seed = Path(a.seed).resolve()
    metadata = seed / "metadata"
    payload = seed / "payload"

    required = [
        metadata / "identity.json",
        metadata / "copied.json",
        metadata / "deferred.json",
        metadata / "SHA256SUMS",
    ]

    for p in required:
        if not p.is_file():
            raise SystemExit(f"MISSING_METADATA={p}")

    identity = json.loads((metadata / "identity.json").read_text())
    copied = json.loads((metadata / "copied.json").read_text())
    deferred = json.loads((metadata / "deferred.json").read_text())

    for key in (
        "schema_version",
        "git_commit",
        "git_branch",
        "git_status_porcelain",
        "source_root",
        "mode",
    ):
        if key not in identity:
            raise SystemExit(f"MISSING_IDENTITY_FIELD={key}")

    expected = {}
    for line in (metadata / "SHA256SUMS").read_text().splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        expected[rel] = digest

    if len(expected) != len(copied):
        raise SystemExit("CHECKSUM_COUNT_MISMATCH")

    for item in copied:
        rel = "payload/" + item["path"]
        path = seed / rel

        if not path.is_file():
            raise SystemExit(f"MISSING_PAYLOAD={rel}")

        digest = sha256(path)

        if digest != item["sha256"]:
            raise SystemExit(f"COPIED_METADATA_HASH_MISMATCH={rel}")

        if expected.get(rel) != digest:
            raise SystemExit(f"SHA256SUMS_MISMATCH={rel}")

    seen = set()
    for item in copied:
        path = item["path"]
        if path in seen:
            raise SystemExit(f"DUPLICATE_COPIED_PATH={path}")
        seen.add(path)

    for item in deferred:
        path = item.get("path")
        if not path:
            raise SystemExit("DEFERRED_ENTRY_MISSING_PATH")
        if path in seen:
            raise SystemExit(f"COPIED_AND_DEFERRED_CONFLICT={path}")

    print(f"VERIFIED_FILES={len(copied)}")
    print(f"DEFERRED_FILES={len(deferred)}")
    print(f"GIT_COMMIT={identity['git_commit']}")
    print(f"GIT_DIRTY_ENTRIES={len(identity['git_status_porcelain'])}")
    print("SEED_INTEGRITY=PASS")

if __name__ == "__main__":
    main()
