from pathlib import Path

from runtime.git_tools import run_git
from runtime.paths import PATCH_DIR, UI_ROOT, resolve_target_root


def _latest_diff_state() -> str:
    latest = PATCH_DIR / "latest.diff"
    if not latest.exists():
        return "missing"
    if latest.stat().st_size == 0:
        return "empty"
    return "present"


def _git_dirty_state(root: Path) -> str:
    try:
        code, out, err = run_git(root, ["status", "--short"])
    except OSError as exc:
        print(f"git_status_error: {exc}")
        return "unknown"
    if code != 0:
        print("git_status_error: " + err.strip())
        return "unknown"
    return "true" if out.strip() else "false"


def _packets_pending_state() -> str:
    packet_root = UI_ROOT / "Packets"
    if not packet_root.exists():
        return "unknown"
    packets = [p for p in packet_root.rglob("*") if p.is_file() and p.name != ".keep"]
    return str(len(packets))


def run(args):
    root = resolve_target_root(args.root)
    print("RUNTIME_STATE")
    print("status: observed")
    print(f"current_root: {root}")
    print("dashboard_boot: observed_from_refresh_request")
    print(f"latest_diff: {_latest_diff_state()}")
    print(f"git_dirty: {_git_dirty_state(root)}")
    print(f"packets_pending: {_packets_pending_state()}")
    print("boundary: runtime_state_reports_observation_only")
