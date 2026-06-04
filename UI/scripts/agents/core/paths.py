"""
Cali Path Discovery Engine (paths.py)
-------------------------------------
Handles case-insensitive paths validation, layouts adjustments,
and model workspace discoveries across Linux (flat layout) and Windows (nested layout).
"""

from pathlib import Path

# Use your existing logic, but ENSURE these names are exactly as they appear here
_base = Path(__file__).resolve().parent.parent.parent.parent 

UI_ROOT = _base / "UI" / "scripts"
DASHBOARD_ROOT = _base / "UI"
# Add scan_files if it is needed by observation_commands
def scan_files(root: Path):
    ignored = {".git", "__pycache__", ".venv", "node_modules", ".godot"}
    files = []
    for p in root.rglob("*"):
        if any(part in ignored for part in p.parts):
            continue
        if p.is_file():
            files.append(p.relative_to(root).as_posix())
    return sorted(files)

# Add this line so other files can find the patch directory
PATCH_DIR = Path(__file__).resolve().parent.parent.parent.parent / "patches"
class PathResolver:
    """Intelligently resolves workspace roots, tool locations, and model paths."""
    def __init__(self):
        self.script_dir = Path(__file__).resolve().parent

        # Derive roots from UI.scriptss file's actual package location:
        # Dashboard/UI/scripts/agents/core/paths.py
        self.ui_root, self.dashboard_root, self.root_resolution_method = self._resolve_roots()
        self.spaceship_root = self.dashboard_root

        self.cli_path, self.resolution_method = self._resolve_cli_path()

        # Model path resolution
        self.model_path = self.dashboard_root / "Models" / "local" / "Phi-3-mini-4k-instruct"

    def _resolve_roots(self):
        """Finds UI and Dashboard roots without relying on a parent directory name."""
        ancestors = (self.script_dir, *self.script_dir.parents)

        for candidate in ancestors:
            if candidate.name.lower() != "ui":
                continue

            expected_core = candidate / "scripts" / "agents" / "core"
            if expected_core.resolve() == self.script_dir:
                return candidate, candidate.parent, "Derived from UI.scriptsnts/core location"

            cli_candidate = candidate / "scripts" / "cli" / "dashboard_cli.py"
            if cli_candidate.exists():
                return candidate, candidate.parent, "Derived from UI.scriptsancestor with CLI"

        for base in ancestors:
            ui_candidate = self._resolve_case_insensitive(base, ["UI"])
            if not ui_candidate:
                continue

            cli_candidate = self._resolve_case_insensitive(
                ui_candidate,
                ["scripts", "cli", "dashboard_cli.py"]
            )
            if cli_candidate:
                return ui_candidate, ui_candidate.parent, "Case-insensitive UI fallback"

        fallback_ui = self.script_dir.parents[2] if len(self.script_dir.parents) > 2 else self.script_dir
        return fallback_ui, fallback_ui.parent, "Fallback from UI.scriptsrent file layout"

    def _resolve_case_insensitive(self, base_path, parts):
        """Resolves path segments case-insensitively to prevent Linux file-system failures."""
        current = Path(base_path)
        for part in parts:
            if not current.is_dir():
                return None
            match = None
            try:
                for entry in current.iterdir():
                    if entry.name.lower() == part.lower():
                        match = entry
                        break
            except Exception:
                return None
            if match is None:
                return None
            current = match
        return current

    def _resolve_cli_path(self):
        """Discovers dashboard_cli.py across both flat and nested structures."""
        primary = self.ui_root / "scripts" / "cli" / "dashboard_cli.py"
        if primary.exists():
            return primary, "Derived UI Root Match"

        # Fallback A: Flat Layout (UI directory matches directly inside dashboard_root)
        direct_resolved = self._resolve_case_insensitive(
            self.dashboard_root,
            ["UI", "scripts", "cli", "dashboard_cli.py"]
        )
        if direct_resolved and direct_resolved.exists():
            return direct_resolved, "Direct UI Layout Match"

        # Fallback B: Nested Layout (UI directory matches inside Dashboard directory)
        nested_resolved = self._resolve_case_insensitive(
            self.dashboard_root,
            ["Dashboard", "UI", "scripts", "cli", "dashboard_cli.py"]
        )
        if nested_resolved and nested_resolved.exists():
            return nested_resolved, "Nested Dashboard UI Layout Match"

        fallback = self.ui_root / "scripts" / "cli" / "dashboard_cli.py"
        return fallback, "Fallback (Default Route)"

    def get_paths_report(self):
        """Returns dynamic path metrics dictionary."""
        return {
            "Spaceship Root": str(self.spaceship_root),
            "Dashboard Root": str(self.dashboard_root),
            "UI Root": str(self.ui_root),
            "Local Phi-3 Path": str(self.model_path),
            "Dashboard CLI Path": str(self.cli_path),
            "Root Discovered via": self.root_resolution_method,
            "Cli Discovered via": self.resolution_method,
            "Model Active Status": "FOUND" if self.model_path.exists() else "NOT FOUND",
            "CLI Tool Status": "READY" if self.cli_path.exists() else "UNAVAILABLE",
            "Dashboard Root Status": "EXISTS" if self.dashboard_root.is_dir() else "MISSING"
        }
