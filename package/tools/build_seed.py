#!/usr/bin/env python3
import argparse, csv, hashlib, json, shutil, subprocess
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def git(root, *args):
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True
    ).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-copy-bytes", type=int, default=32 * 1024 * 1024)
    a = ap.parse_args()

    root = Path(a.root).resolve()
    audit = Path(a.audit).resolve()
    out = Path(a.output).resolve()

    if root == out or root in out.parents is False:
        if not str(out).startswith(str(root / "trash" / "tmp")):
            raise SystemExit("output must remain under repository trash/tmp")

    if out.exists():
        shutil.rmtree(out)

    payload = out / "payload"
    metadata = out / "metadata"
    payload.mkdir(parents=True)
    metadata.mkdir(parents=True)

    rows = list(csv.DictReader(audit.open(encoding="utf-8"), delimiter="\t"))
    copied = []
    deferred = []

    for row in rows:
        if row["inclusion"] != "seed":
            continue

        rel = row["path"]
        src = root / rel
        if not src.is_file():
            continue

        size = int(row["size_bytes"])

        if size > a.max_copy_bytes:
            deferred.append({
                "path": rel,
                "size_bytes": size,
                "class": row["class"],
                "reason": "proof builder defers large payload while preserving manifest intent",
            })
            continue

        dst = payload / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        copied.append({
            "path": rel,
            "size_bytes": size,
            "sha256": sha256(dst),
            "class": row["class"],
        })

    identity = {
        "schema_version": 1,
        "git_commit": git(root, "rev-parse", "HEAD"),
        "git_branch": git(root, "branch", "--show-current"),
        "git_status_porcelain": subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
        ).splitlines(),
        "source_root": str(root),
        "mode": "proof",
        "large_payload_copy_limit_bytes": a.max_copy_bytes,
    }

    (metadata / "identity.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    (metadata / "copied.json").write_text(
        json.dumps(copied, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    (metadata / "deferred.json").write_text(
        json.dumps(deferred, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with (metadata / "SHA256SUMS").open("w", encoding="utf-8") as f:
        for item in sorted(copied, key=lambda x: x["path"]):
            f.write(f'{item["sha256"]}  payload/{item["path"]}\n')

    print(f"COPIED_FILES={len(copied)}")
    print(f"DEFERRED_LARGE_FILES={len(deferred)}")
    print(f"GIT_COMMIT={identity['git_commit']}")
    print(f"GIT_DIRTY_ENTRIES={len(identity['git_status_porcelain'])}")

if __name__ == "__main__":
    main()
