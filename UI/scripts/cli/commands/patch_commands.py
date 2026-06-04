import subprocess
from pathlib import Path

from UI.scripts.cli.commands.base import Command


class ApplyPatchCommand(Command):
    def run(self, args):
        root = self.resolver.resolve_target_root(getattr(args, "root", None))
        diff_path = Path(args.diff).resolve()

        if not getattr(args, "approved", False):
            return self._report("blocked", "reason: --approved required")

        if not diff_path.exists():
            return self._report("blocked", "reason: diff not found")

        proc = subprocess.run(
            ["git", "apply", str(diff_path)],
            cwd=str(root),
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            return self._report("apply_failed", proc.stderr.strip())

        print("status: patch_applied")
        print(f"root: {root}")
        print(f"diff: {diff_path}")


class ClearDiffCommand(Command):
    def run(self, args):
        patch_dir = self.resolver.ui_root / "scripts" / "patches"
        latest = patch_dir / "latest.diff"
        archive = patch_dir / "latest.diff.tombstone"

        patch_dir.mkdir(parents=True, exist_ok=True)

        if not latest.exists():
            return self._report("missing", "latest.diff not found")

        if archive.exists():
            archive.unlink()

        latest.replace(archive)

        print("status: archived")
        print(f"from: {latest}")
        print(f"to: {archive}")


class ViewDiffCommand(Command):
    def run(self, args):
        patch_dir = self.resolver.ui_root / "scripts" / "patches"
        latest = patch_dir / "latest.diff"

        if not latest.exists():
            return self._report("missing", "latest.diff not found")

        print("status: present")
        print(f"path: {latest}")
        print(f"diff:\n{latest.read_text(encoding='utf-8', errors='replace')}")


class GrantReviewCommand(Command):
    def run(self, args):
        diff_path = Path(args.diff).resolve()

        if not diff_path.exists():
            return self._report("missing", f"diff not found: {diff_path}")

        # Lexical review placeholder.
        # This is review surface only, not approval authority.
        print("status: admissible")
        print(f"diff: {diff_path}")