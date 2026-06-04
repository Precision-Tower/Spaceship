from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_ROOT = UI_ROOT.parent
CORE_ROOT = DASHBOARD_ROOT.parent
DEFAULT_TARGET_ROOT = CORE_ROOT / "Engineering"
PATCH_DIR = UI_ROOT / "scripts" / "patches"
LOG_DIR = UI_ROOT / "scripts" / "logs"
SESSION_DIR = UI_ROOT / "scripts" / "sessions"

def resolve_target_root(root_arg=None) -> Path:
    root = Path(root_arg).resolve() if root_arg else DEFAULT_TARGET_ROOT.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Target root not found: {root}")
    return root

def scan_files(root: Path):
    ignored = {".git", "__pycache__", ".venv", "node_modules", ".godot"}
    files = []
    for p in root.rglob("*"):
        if any(part in ignored for part in p.parts):
            continue
        if p.is_file():
            files.append(p.relative_to(root).as_posix())
    return sorted(files)

