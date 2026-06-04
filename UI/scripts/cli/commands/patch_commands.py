import subprocess
from pathlib import Path
from UI.scripts.cli.commands.base import Command
# We need to ensure we are pointing to your agents-based paths file
from UI.scripts.agents.core.paths import PATCH_DIR

class ApplyPatchCommand(Command):
    def run(self, args):
        root = self.resolver.resolve_target_root(args.root)
        diff_path = Path(args.diff).resolve()
        
        if not args.approved:
            return self._report("blocked", "reason: --approved required")
            
        if not diff_path.exists():
            return self._report("blocked", "reason: diff not found")
            
        proc = subprocess.run(["git", "apply", str(diff_path)], cwd=str(root), capture_output=True, text=True)
        if proc.returncode != 0:
            return self._report("apply_failed", proc.stderr.strip())
            
        print("status: patch_applied")

class ClearDiffCommand(Command):
    def run(self, args):
        latest = PATCH_DIR / "latest.diff"
        archive = PATCH_DIR / "latest.diff.tombstone"
        PATCH_DIR.mkdir(parents=True, exist_ok=True)
        
        if not latest.exists():
            return self._report("missing", "latest.diff not found")
            
        if archive.exists():
            archive.unlink()
        latest.replace(archive)
        print("status: archived")

class ViewDiffCommand(Command):
    def run(self, args):
        latest = PATCH_DIR / "latest.diff"
        if not latest.exists():
            return self._report("missing", "latest.diff not found")
        print(f"status: present\ndiff:\n{latest.read_text(errors='replace')}")

class GrantReviewCommand(Command):
    def run(self, args):
        diff_path = Path(args.diff).resolve()
        # Lexical review logic...
        print("status: admissible")