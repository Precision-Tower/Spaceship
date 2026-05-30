from pathlib import Path
from runtime.paths import PATCH_DIR


def run(args):
    latest = PATCH_DIR / "latest.diff"
    print("VIEW_LATEST_DIFF")
    if not latest.exists():
        print("status: missing")
        print("reason: latest.diff not found")
        return

    text = latest.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        print("status: empty")
        return

    print("status: present")
    print(f"patch: {latest}")
    print("diff:")
    print(text.rstrip("\n"))
