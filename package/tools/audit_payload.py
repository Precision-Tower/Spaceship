#!/usr/bin/env python3
import argparse, csv, json, os, subprocess
from pathlib import Path

LARGE = 100 * 1024 * 1024
REBUILD_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".gradle", ".cache", "node_modules", "build", "build-pixel",
    "build-debug", "build-release", "dist", "target",
}
REBUILD_SUFFIX = {".pyc", ".pyo", ".o", ".obj", ".a", ".so", ".class"}
LOCAL_PARTS = {"local", ".ssh", ".gnupg"}
LOCAL_NAMES = {"default.env", ".env", "tailscale-auth.key"}

def git_set(root, args):
    p = subprocess.run(
        ["git", *args], cwd=root, check=True, text=True,
        stdout=subprocess.PIPE
    )
    return {x for x in p.stdout.splitlines() if x}

def classify(rel, tracked, ignored):
    p = Path(rel)
    parts = p.parts
    name = p.name.lower()

    if parts and parts[0] == "trash":
        return "excluded", "omit", "repository-local disposable trash"

    if rel == ".git" or rel.startswith(".git/"):
        return "reconstructable", "rebuild", "raw Git storage; preserve history through explicit portable artifact"

    if rel in tracked:
        return "required", "seed", "tracked CE-OS authority or source"

    if any(x in LOCAL_PARTS for x in parts):
        return "machine_local", "preserve_separately", "host-specific local state"

    if (
        p.name in LOCAL_NAMES
        or name.endswith(".key")
        or name.endswith(".pem")
        or "secret" in name
        or "credential" in name
        or "token" in name
    ):
        return "machine_local", "preserve_separately", "potential host credential or enrollment state"

    if any(x in REBUILD_DIRS for x in parts) or p.suffix in REBUILD_SUFFIX:
        return "reconstructable", "rebuild", "generated build, cache, bytecode, or dependency output"

    if rel in ignored:
        return "optional", "seed", "ignored non-disposable payload preserved by default"

    return "optional", "seed", "untracked non-disposable payload preserved by default"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--large", required=True)
    a = ap.parse_args()

    root = Path(a.root).resolve()
    tracked = git_set(root, ["ls-files"])
    ignored = git_set(root, ["ls-files", "--others", "--ignored", "--exclude-standard"])

    rows = []
    counts = {}
    bytes_by_class = {}

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current = Path(dirpath)
        rel_dir = current.relative_to(root)

        if rel_dir.parts and rel_dir.parts[0] == "trash":
            dirnames[:] = []
            filenames[:] = []
            if str(rel_dir) == "trash":
                rows.append({
                    "path": "trash/",
                    "class": "excluded",
                    "inclusion": "omit",
                    "reason": "repository-local disposable trash subtree",
                    "size_bytes": 0,
                    "tracked_state": "policy",
                })
            continue

        for name in filenames:
            full = current / name
            rel = full.relative_to(root).as_posix()

            try:
                size = full.lstat().st_size
            except OSError:
                size = 0

            cls, inclusion, reason = classify(rel, tracked, ignored)

            if rel in tracked:
                state = "tracked"
            elif rel in ignored:
                state = "ignored"
            elif rel.startswith(".git/"):
                state = "git_internal"
            else:
                state = "untracked"

            rows.append({
                "path": rel,
                "class": cls,
                "inclusion": inclusion,
                "reason": reason,
                "size_bytes": size,
                "tracked_state": state,
            })

    rows.sort(key=lambda r: r["path"])

    for r in rows:
        cls = r["class"]
        counts[cls] = counts.get(cls, 0) + 1
        bytes_by_class[cls] = bytes_by_class.get(cls, 0) + int(r["size_bytes"])

    large = [r for r in rows if int(r["size_bytes"]) >= LARGE]
    large.sort(key=lambda r: int(r["size_bytes"]), reverse=True)

    fields = [
        "path", "class", "inclusion", "reason",
        "size_bytes", "tracked_state",
    ]

    with open(a.output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    with open(a.large, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(large)

    summary = {
        "schema_version": 1,
        "file_count": len(rows),
        "large_threshold_bytes": LARGE,
        "large_file_count": len(large),
        "classes": {
            cls: {
                "count": counts.get(cls, 0),
                "size_bytes": bytes_by_class.get(cls, 0),
            }
            for cls in [
                "required", "reconstructable", "optional",
                "excluded", "machine_local",
            ]
        },
    }

    Path(a.summary).write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"PAYLOAD_FILES={len(rows)}")
    print(f"LARGE_FILE_COUNT={len(large)}")
    for cls in summary["classes"]:
        print(f"{cls.upper()}_COUNT={summary['classes'][cls]['count']}")

if __name__ == "__main__":
    main()
