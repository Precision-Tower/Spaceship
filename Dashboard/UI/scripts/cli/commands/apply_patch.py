from pathlib import Path
from runtime.paths import resolve_target_root
from runtime.git_tools import run_git
import subprocess

def run(args):
    root = resolve_target_root(args.root)
    diff_path = Path(args.diff).resolve()
    print("APPLY_PATCH")
    print(f"root: {root}")
    print(f"diff: {diff_path}")
    if not args.approved:
        print("status: blocked")
        print("reason: --approved required")
        print("files_changed: none_claimed")
        return
    if not diff_path.exists():
        print("status: blocked")
        print("reason: diff not found")
        print("files_changed: none_claimed")
        return
    proc = subprocess.run(["git", "apply", str(diff_path)], cwd=str(root), text=True, capture_output=True)
    if proc.returncode != 0:
        print("status: apply_failed")
        print(proc.stderr.strip())
        print("files_changed: none_claimed")
        return
    _, out, _ = run_git(root, ["status", "--short"])
    print("status: patch_applied")
    print("git_status:")
    print(out.strip() or "(no changes reported)")
