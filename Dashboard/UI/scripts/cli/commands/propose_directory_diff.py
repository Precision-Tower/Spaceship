from pathlib import Path
from runtime.paths import resolve_target_root, scan_files, PATCH_DIR
import difflib, datetime

def find_directory(root: Path):
    for rel in ["Models/Shared/Directory.yaml", "Shared/Directory.yaml", "Directory.yaml"]:
        p = root / rel
        if p.exists():
            return p
    matches = list(root.rglob("Directory.yaml"))
    return matches[0] if matches else None

def run(args):
    root = resolve_target_root(args.root)
    files = scan_files(root)
    target = find_directory(root)
    PATCH_DIR.mkdir(parents=True, exist_ok=True)
    latest = PATCH_DIR / "latest.diff"
    print("PROPOSE_DIRECTORY_DIFF")
    print(f"root: {root}")
    if target is None:
        latest.write_text("# blocked: no Directory.yaml found\\n", encoding="utf-8")
        print("status: blocked_no_directory_found")
        print(f"patch: {latest}")
        return
    original = target.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    addition = [
        "\\n",
        "# --- DashBoard candidate scan note ---\\n",
        f"# created_at: {stamp}\\n",
        "# status: candidate_note_not_authority\\n",
        f"# files_detected: {len(files)}\\n",
        "# rule: review_before_promotion\\n",
        "# --- end DashBoard candidate scan note ---\\n",
    ]
    rel = target.relative_to(root).as_posix()
    diff = difflib.unified_diff(original, original + addition, fromfile=rel, tofile=rel, lineterm="")
    latest.write_text("\\n".join(diff) + "\\n", encoding="utf-8")
    print("status: diff_prepared")
    print(f"target: {target}")
    print(f"patch: {latest}")
    print("authority: propose_only")
