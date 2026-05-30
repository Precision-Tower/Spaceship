from pathlib import Path
from runtime.paths import PATCH_DIR


def run(args):
    latest = PATCH_DIR / "latest.diff"
    archive = PATCH_DIR / "latest.diff.tombstone"
    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    print("CLEAR_LATEST_DIFF")
    if not latest.exists():
        print("status: missing")
        print("reason: latest.diff not found")
        return

    if archive.exists():
        archive.unlink()

    latest.replace(archive)
    print("status: archived")
    print(f"patch: {archive}")
