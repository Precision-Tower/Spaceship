import json
from pathlib import Path
from Agency.Core.interfaces.cli.commands.base import Command

class RefsCommand(Command):
    """
    Search for bounded string references inside the Dashboard workspace.

    This is filesystem observation, not validation.
    """

    DEFAULT_ROOTS = ["Agency", "UI", "Engineering", "run.py"]

    IGNORE_PARTS = {
        ".git",
        ".godot",
        "__pycache__",
        "Chroma",
        "sessions",
        "actions",
        "memory",
        "Archive",
        "archive",
        "Datasets",
        "output",
        "history",
        "node_modules",
    }

    IGNORE_SUFFIXES = {
        ".zip",
        ".sqlite",
        ".sqlite3",
        ".parquet",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".exe",
        ".dll",
        ".so",
        ".bin",
        ".gguf",
        ".pth",
        ".pt",
    }

    def run(self, args):
        query = args.query
        raw = getattr(args, "raw", False)
        requested_root = getattr(args, "root", None)
        max_files = max(1, int(getattr(args, "max_files", 500)))
        max_matches = max(1, int(getattr(args, "max_matches", 80)))
        max_bytes = max(1024, int(getattr(args, "max_bytes", 1_000_000)))

        dashboard_root = self.resolver.dashboard_root

        if requested_root:
            candidate = (dashboard_root / requested_root).resolve()

            try:
                candidate.relative_to(dashboard_root)
            except ValueError:
                print("ERR: root outside dashboard workspace")
                return 2

            search_roots = [candidate]
        else:
            search_roots = [
                (dashboard_root / name).resolve()
                for name in self.DEFAULT_ROOTS
            ]

        matches = []
        files_scanned = 0
        files_skipped = 0
        truncated = False

        for root in search_roots:
            if root.is_file():
                candidates = [root]
            elif root.exists():
                candidates = root.rglob("*")
            else:
                continue

            for path in candidates:
                if files_scanned >= max_files:
                    truncated = True
                    break

                if not path.is_file():
                    continue

                try:
                    relative_parts = path.relative_to(dashboard_root).parts
                except ValueError:
                    files_skipped += 1
                    continue

                if any(part in self.IGNORE_PARTS for part in relative_parts):
                    files_skipped += 1
                    continue

                if ".bak_" in path.name or path.suffix.lower() in self.IGNORE_SUFFIXES:
                    files_skipped += 1
                    continue

                try:
                    if path.stat().st_size > max_bytes:
                        files_skipped += 1
                        continue
                except OSError:
                    files_skipped += 1
                    continue

                files_scanned += 1

                try:
                    text = path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                except Exception:
                    files_skipped += 1
                    continue

                for idx, line in enumerate(text.splitlines(), start=1):
                    if query not in line:
                        continue

                    matches.append({
                        "path": str(path.relative_to(dashboard_root)),
                        "line": idx,
                        "text": line.strip(),
                    })

                    if len(matches) >= max_matches:
                        truncated = True
                        break

                if len(matches) >= max_matches:
                    break

            if files_scanned >= max_files or len(matches) >= max_matches:
                break

        payload = {
            "query": query,
            "root": requested_root or "default_roots",
            "matches": matches,
            "count": len(matches),
            "files_scanned": files_scanned,
            "files_skipped": files_skipped,
            "max_files": max_files,
            "max_matches": max_matches,
            "truncated": truncated,
            "authority": "filesystem_scan_not_validation",
        }

        if raw:
            print(json.dumps(payload, indent=2))
            return 0

        print(f"References for: {query}")
        print(f"root: {payload['root']}")
        print(f"count: {len(matches)}")
        print(f"files_scanned: {files_scanned}")
        print(f"files_skipped: {files_skipped}")
        print(f"truncated: {str(truncated).lower()}")

        for match in matches:
            print(
                f"- {match['path']}:{match['line']} "
                f"{match['text']}"
            )

        print("authority: filesystem_scan_not_validation")
        return 0


class TreeCommand(Command):
    """
    Analyze the directory tree, counting files and detecting legacy paths.
    """
    def run(self, args):
        path_text = args.path
        raw = getattr(args, "raw", False)
        dashboard_root = self.resolver.dashboard_root
        target = (dashboard_root / path_text).resolve()

        try:
            target.relative_to(dashboard_root)
        except ValueError:
            print("ERR: path outside dashboard workspace")
            return

        if not target.exists() or not target.is_dir():
            print(f"ERR: directory not found: {path_text}")
            return

        buckets = {}
        file_count = 0
        stale_refs = []

        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or "Chroma" in path.parts:
                continue

            file_count += 1
            rel = path.relative_to(target)
            bucket = rel.parts[0] if len(rel.parts) > 1 else "."
            buckets[bucket] = buckets.get(bucket, 0) + 1

            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                if "res://screen" in text:
                    stale_refs.append(str(path.relative_to(dashboard_root)))
            except Exception:
                pass

        payload = {
            "path": str(target.relative_to(dashboard_root)),
            "file_count": file_count,
            "buckets": buckets,
            "stale_res_screen_refs": stale_refs,
            "authority": "filesystem_scan_not_validation",
        }

        if raw:
            print(json.dumps(payload, indent=2))
            return

        print(f"Tree analysis: {payload['path']}")
        print(f"files: {file_count}")
        print("buckets:")
        for name, count in sorted(buckets.items()):
            print(f"  - {name}: {count}")
        print(f"stale res://screen refs: {len(stale_refs)}")
        for ref in stale_refs[:40]:
            print(f"  - {ref}")
        print("authority: filesystem_scan_not_validation")
