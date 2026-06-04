"""
Cali Path Discovery Engine (paths.py)
-------------------------------------
Handles workspace discovery, path normalization, model resolution,
and compatibility exports used across agents/, cli/, and runtime/.

Expected layout:

Spaceship/
│
├── Run.py
├── local/
├── UI/
│   ├── Packets/
│   ├── scripts/
│   │   ├── agents/
│   │   ├── cli/
│   │   ├── runtime/
│   │   ├── sessions/
│   │   ├── patches/
│   │   └── logs/
│   └── project.godot
│
└── Models/
"""

from pathlib import Path


# ----------------------------------------------------------------------
# Root Discovery
# ----------------------------------------------------------------------

SPACESHIP_ROOT = Path(__file__).resolve().parents[4]

UI_ROOT = SPACESHIP_ROOT / "UI"
SCRIPTS_ROOT = UI_ROOT / "scripts"

DASHBOARD_ROOT = UI_ROOT

SESSION_DIR = SCRIPTS_ROOT / "sessions"
PATCH_DIR = SCRIPTS_ROOT / "patches"
LOG_DIR = SCRIPTS_ROOT / "logs"

PACKET_DIR = UI_ROOT / "Packets"

for directory in (
    SESSION_DIR,
    PATCH_DIR,
    LOG_DIR,
    PACKET_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# File Scanner
# ----------------------------------------------------------------------

def scan_files(root: Path):
    """
    Recursively scans files while skipping generated/cache folders.
    """

    ignored = {
        ".git",
        "__pycache__",
        ".venv",
        "node_modules",
        ".godot",
        "local",
        ".cache",
        "sessions",
        "logs",
        "old",
    }

    ignored_suffixes = {
        ".safetensors",
        ".gguf",
        ".jsonl",
    }

    results = []

    for path in root.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if path.suffix.lower() in ignored_suffixes:
            continue
        if path.is_file():
            results.append(path.relative_to(root).as_posix())

    return sorted(results)


# ----------------------------------------------------------------------
# Path Resolver
# ----------------------------------------------------------------------

class PathResolver:
    """
    Resolves workspace locations dynamically.

    Provides:
    - Spaceship root
    - UI root
    - Dashboard root
    - CLI entrypoint
    - Local model locations
    """

    def __init__(self, spaceship_root=None):
        self.script_dir = Path(__file__).resolve().parent

        if spaceship_root is not None:
            self.spaceship_root = Path(spaceship_root).resolve()
            self.ui_root = self.spaceship_root / "UI"
            self.dashboard_root = self.ui_root
            self.root_resolution_method = "Provided by Run.py"
            self.cli_path, self.resolution_method = self._resolve_cli_path()
            self.model_path = self.spaceship_root / "local" / "Phi-3-mini-4k-instruct"
            return

        (
            self.ui_root,
            self.dashboard_root,
            self.root_resolution_method,
        ) = self._resolve_roots()

        self.spaceship_root = self.ui_root.parent

        (
            self.cli_path,
            self.resolution_method,
        ) = self._resolve_cli_path()

        self.model_path = (
            self.spaceship_root
            / "local"
            / "Phi-3-mini-4k-instruct"
        )

    # ------------------------------------------------------------------

    def _resolve_roots(self):
        """
        Attempts to discover the UI root and Dashboard root.
        """

        ancestors = (self.script_dir, *self.script_dir.parents)

        for candidate in ancestors:

            if candidate.name.lower() != "ui":
                continue

            expected_core = (
                candidate
                / "scripts"
                / "agents"
                / "core"
            )

            if expected_core.resolve() == self.script_dir:
                return (
                    candidate,
                    candidate.parent,
                    "Derived from agents/core location",
                )

            cli_candidate = (
                candidate
                / "scripts"
                / "cli"
                / "dashboard_cli.py"
            )

            if cli_candidate.exists():
                return (
                    candidate,
                    candidate.parent,
                    "Derived from UI ancestor with CLI",
                )

        for base in ancestors:

            ui_candidate = self._resolve_case_insensitive(
                base,
                ["UI"]
            )

            if not ui_candidate:
                continue

            cli_candidate = self._resolve_case_insensitive(
                ui_candidate,
                [
                    "scripts",
                    "cli",
                    "dashboard_cli.py",
                ],
            )

            if cli_candidate:
                return (
                    ui_candidate,
                    ui_candidate.parent,
                    "Case-insensitive UI fallback",
                )

        fallback_ui = (
            self.script_dir.parents[2]
            if len(self.script_dir.parents) > 2
            else self.script_dir
        )

        return (
            fallback_ui,
            fallback_ui.parent,
            "Fallback layout",
        )

    # ------------------------------------------------------------------

    def _resolve_case_insensitive(
        self,
        base_path,
        parts,
    ):
        """
        Resolve path segments case-insensitively.
        """

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

    # ------------------------------------------------------------------

    def _resolve_cli_path(self):
        """
        Locate dashboard_cli.py.
        """

        primary = (
            self.ui_root
            / "scripts"
            / "cli"
            / "dashboard_cli.py"
        )

        if primary.exists():
            return primary, "Derived UI Root Match"

        direct = self._resolve_case_insensitive(
            self.dashboard_root,
            [
                "UI",
                "scripts",
                "cli",
                "dashboard_cli.py",
            ],
        )

        if direct and direct.exists():
            return direct, "Direct UI Layout Match"

        nested = self._resolve_case_insensitive(
            self.dashboard_root,
            [
                "Dashboard",
                "UI",
                "scripts",
                "cli",
                "dashboard_cli.py",
            ],
        )

        if nested and nested.exists():
            return nested, "Nested Dashboard Layout Match"

        return primary, "Fallback Route"

    # ------------------------------------------------------------------

    def get_paths_report(self):
        """
        Human-readable path report.
        """

        return {
            "Spaceship Root": str(self.spaceship_root),
            "Dashboard Root": str(self.dashboard_root),
            "UI Root": str(self.ui_root),
            "Scripts Root": str(SCRIPTS_ROOT),
            "Session Dir": str(SESSION_DIR),
            "Patch Dir": str(PATCH_DIR),
            "Log Dir": str(LOG_DIR),
            "Packet Dir": str(PACKET_DIR),
            "Local Phi-3 Path": str(self.model_path),
            "Dashboard CLI Path": str(self.cli_path),
            "Root Discovered Via": self.root_resolution_method,
            "CLI Discovered Via": self.resolution_method,
            "Model Active Status": (
                "FOUND"
                if self.model_path.exists()
                else "NOT FOUND"
            ),
            "CLI Tool Status": (
                "READY"
                if self.cli_path.exists()
                else "UNAVAILABLE"
            ),
            "Dashboard Root Status": (
                "EXISTS"
                if self.dashboard_root.exists()
                else "MISSING"
            ),
        }

    def resolve_target_root(self, root=None) -> Path:
        """
        Resolve command target root.

        Default:
        - UI root, because dashboard CLI commands operate inside UI.

        Allowed explicit roots:
        - ui
        - spaceship
        - root
        - .
        """
        if root is None:
            return self.ui_root

        value = str(root).strip().lower()

        if value in {"", "ui", "dashboard"}:
            return self.ui_root

        if value in {".", "spaceship", "root", "repo"}:
            return self.spaceship_root

        candidate = (self.spaceship_root / str(root)).resolve()

        if self.spaceship_root not in candidate.parents and candidate != self.spaceship_root:
            raise ValueError(f"Target root escapes Spaceship root: {root}")

        return candidate