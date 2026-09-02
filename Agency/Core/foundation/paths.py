from __future__ import annotations

from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------
# Root authority
# ---------------------------------------------------------------------

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]

AGENCY_ROOT = DASHBOARD_ROOT / "Agency"
CORE_ROOT = AGENCY_ROOT / "Core"
AGENTS_ROOT = AGENCY_ROOT / "Agents"
DEFAULT_OPERATIONAL_AGENT = "Editor"


def normalize_agent_name(raw: str) -> str:
    cleaned = "".join(ch for ch in str(raw or "").strip() if ch.isalnum() or ch == "_")
    if not cleaned:
        raise ValueError("agent_name_empty")
    return cleaned[:1].upper() + cleaned[1:]


def agent_root(agent_name: str = DEFAULT_OPERATIONAL_AGENT) -> Path:
    return AGENTS_ROOT / normalize_agent_name(agent_name)


def agent_state_root(agent_name: str = DEFAULT_OPERATIONAL_AGENT) -> Path:
    return agent_root(agent_name) / "state"


def agent_work_root(agent_name: str = DEFAULT_OPERATIONAL_AGENT) -> Path:
    return agent_root(agent_name) / "work"


def agent_runtime_root(agent_name: str = DEFAULT_OPERATIONAL_AGENT) -> Path:
    return agent_root(agent_name) / "runtime"


def agent_memory_root(
    agent_name: str = DEFAULT_OPERATIONAL_AGENT,
    *,
    root: str | Path | None = None,
) -> Path:
    if root is None:
        agents_root = AGENTS_ROOT
    else:
        agents_root = Path(root).resolve() / "Agency" / "Agents"
    return agents_root / normalize_agent_name(agent_name) / "memory"


EDITOR_AGENT_ROOT = agent_root("Editor")
EDITOR_WORK_ROOT = agent_work_root("Editor")
EDITOR_RUNTIME_ROOT = agent_runtime_root("Editor")
EDITOR_MEMORY_ROOT = agent_memory_root("Editor")

STATE_ROOT = agent_state_root(DEFAULT_OPERATIONAL_AGENT)
WORK_ROOT = agent_work_root(DEFAULT_OPERATIONAL_AGENT)
MISSIONS_ROOT = WORK_ROOT / "Missions"
PINBOARD_ROOT = WORK_ROOT / "Pinboard"
PROPOSALS_ROOT = WORK_ROOT / "Proposals"
WORK_PACKETS_ROOT = WORK_ROOT / "WorkPackets"

EDITOR_TASKS_ROOT = EDITOR_WORK_ROOT / "EditorTasks"
INSPECTIONS_ROOT = EDITOR_WORK_ROOT / "Inspections"
PROJECTS_ROOT = WORK_ROOT / "Projects"
DATASETS_ROOT = AGENCY_ROOT / "Datasets"
ARCHIVE_ROOT = AGENCY_ROOT / "Archive"

UI_ROOT = DASHBOARD_ROOT / "UI"
MAIN_UI_ROOT = UI_ROOT / "Main"

LOCAL_ROOT = DASHBOARD_ROOT / "local"
TOOLS_ROOT = DASHBOARD_ROOT / "Tools"

RUN_PY = DASHBOARD_ROOT / "run.py"
ENVIRONMENT_MANIFEST_PATH = EDITOR_RUNTIME_ROOT / "environment_manifest.yaml"
MODEL_SERVER_PID_PATH = EDITOR_RUNTIME_ROOT / "llama-server.pid"
MODEL_SERVER_LOG_PATH = EDITOR_RUNTIME_ROOT / "logs" / "llama-server.log"
WATCH_LOG = EDITOR_RUNTIME_ROOT / "sessions" / "run_watch.jsonl"


# ---------------------------------------------------------------------
# Compatibility aliases
# ---------------------------------------------------------------------

SPACESHIP_ROOT = DASHBOARD_ROOT
SOURCE_UI_ROOT = UI_ROOT
DASHBOARD_UI_ROOT = UI_ROOT
WORKSPACE_ROOT = DASHBOARD_ROOT.parent


# ---------------------------------------------------------------------
# Directory setup
# ---------------------------------------------------------------------

def ensure_core_dirs() -> None:
    for path in (
        AGENCY_ROOT,
        CORE_ROOT,
        AGENTS_ROOT,
        DATASETS_ROOT,
        ARCHIVE_ROOT,
        UI_ROOT,
        MAIN_UI_ROOT,
        LOCAL_ROOT,
        EDITOR_AGENT_ROOT,
        STATE_ROOT,
        WORK_ROOT,
        MISSIONS_ROOT,
        PINBOARD_ROOT,
        PROPOSALS_ROOT,
        WORK_PACKETS_ROOT,
        EDITOR_TASKS_ROOT,
        INSPECTIONS_ROOT,
        EDITOR_RUNTIME_ROOT,
        EDITOR_MEMORY_ROOT,
        WATCH_LOG.parent,
        MODEL_SERVER_LOG_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------

def stable_path(path: str | Path, root: Path = DASHBOARD_ROOT) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def resolve_under(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate

    resolved = candidate.resolve()
    root_resolved = root.resolve()

    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError(f"path_escapes_root: {value}")

    return resolved


def scan_files(
    root: str | Path,
    *,
    suffixes: Iterable[str] | None = None,
    ignored_parts: Iterable[str] | None = None,
) -> list[Path]:
    root = Path(root)

    suffixes = set(s.lower() for s in (suffixes or (
        ".py", ".gd", ".tscn", ".tres", ".yaml", ".yml", ".json", ".md", ".txt"
    )))

    ignored = set(ignored_parts or (
        ".git",
        ".godot",
        "__pycache__",
        ".venv",
        "node_modules",
        "local",
        "sessions",
        "logs",
        "Archive",
    ))

    results: list[Path] = []

    if not root.exists():
        return results

    for path in root.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        results.append(path)

    return sorted(results)


# ---------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------

class PathResolver:
    def __init__(self, root: str | Path | None = None):
        self.dashboard_root = Path(root).resolve() if root else DASHBOARD_ROOT

        self.agency_root = self.dashboard_root / "Agency"
        self.core_root = self.agency_root / "Core"
        self.agents_root = self.agency_root / "Agents"
        self.default_agent_root = self.agents_root / DEFAULT_OPERATIONAL_AGENT
        self.agent_state_root = self.default_agent_root / "state"
        self.agent_work_root = self.default_agent_root / "work"
        self.agent_runtime_root = self.default_agent_root / "runtime"
        self.core_projects_root = self.core_root / "projects"
        self.projects_root = self.agent_work_root / "Projects"
        self.memory_root = self.core_root / "memory"
        self.datasets_root = self.agency_root / "Datasets"
        self.archive_root = self.agency_root / "Archive"

        self.ui_root = self.dashboard_root / "UI"
        self.main_ui_root = self.ui_root / "Main"

        self.local_root = self.dashboard_root / "local"
        self.tools_root = self.dashboard_root / "Tools"

        self.run_py = self.dashboard_root / "run.py"
        self.watch_log = self.agent_runtime_root / "sessions" / "run_watch.jsonl"

        self.spaceship_root = self.dashboard_root
        self.source_ui_root = self.ui_root
        self.shared_root = self.core_root
        self.scripts_root = self.core_root
        self.cli_path = self.run_py

        self.root_resolution_method = "Agency/Core/foundation/paths.py"
        self.resolution_method = "Dashboard Agency layout"

    def resolve(self, path: str | Path) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p.resolve()
        return (self.dashboard_root / p).resolve()

    def resolve_target_root(self, root: str | Path | None = None) -> Path:
        if root is None:
            return self.dashboard_root

        value = str(root).strip()
        lowered = value.lower()

        aliases = {
            "": self.dashboard_root,
            ".": self.dashboard_root,
            "dashboard": self.dashboard_root,
            "dashboard-root": self.dashboard_root,
            "root": self.dashboard_root,
            "repo": self.dashboard_root,
            "agency": self.agency_root,
            "core": self.core_root,
            "agents": self.agents_root,
            "projects": self.projects_root,
            "core-projects": self.core_projects_root,
            "agent": self.default_agent_root,
            "agent-state": self.agent_state_root,
            "agent-work": self.agent_work_root,
            "agent-runtime": self.agent_runtime_root,
            "memory": self.memory_root,
            "datasets": self.datasets_root,
            "ui": self.ui_root,
            "main": self.main_ui_root,
            "ui-main": self.main_ui_root,
            "local": self.local_root,
        }

        if lowered in aliases:
            return aliases[lowered]

        return resolve_under(self.dashboard_root, value)

    def get_paths_report(self) -> dict[str, str]:
        return {
            "Dashboard Root": str(self.dashboard_root),
            "Agency Root": str(self.agency_root),
            "Core Root": str(self.core_root),
            "Agents Root": str(self.agents_root),
            "Projects Root": str(self.projects_root),
            "Core Projects Root": str(self.core_projects_root),
            "Default Agent Root": str(self.default_agent_root),
            "Agent State Root": str(self.agent_state_root),
            "Agent Work Root": str(self.agent_work_root),
            "Agent Runtime Root": str(self.agent_runtime_root),
            "Memory Root": str(self.memory_root),
            "Datasets Root": str(self.datasets_root),
            "UI Root": str(self.ui_root),
            "Main UI Root": str(self.main_ui_root),
            "Local Root": str(self.local_root),
            "Run.py": str(self.run_py),
            "Watch Log": str(self.watch_log),
            "Root Discovered Via": self.root_resolution_method,
            "CLI Discovered Via": self.resolution_method,
            "Dashboard Root Status": "EXISTS" if self.dashboard_root.exists() else "MISSING",
            "Agency Status": "EXISTS" if self.agency_root.exists() else "MISSING",
            "Main UI Status": "EXISTS" if self.main_ui_root.exists() else "MISSING",
            "Run.py Status": "EXISTS" if self.run_py.exists() else "MISSING",
        }


def ensure_spaceship_on_pythonpath() -> Path:
    return DASHBOARD_ROOT


ensure_core_dirs()


__all__ = [
    "DASHBOARD_ROOT",
    "AGENCY_ROOT",
    "CORE_ROOT",
    "AGENTS_ROOT",
    "DEFAULT_OPERATIONAL_AGENT",
    "EDITOR_AGENT_ROOT",
    "EDITOR_WORK_ROOT",
    "EDITOR_RUNTIME_ROOT",
    "EDITOR_MEMORY_ROOT",
    "STATE_ROOT",
    "WORK_ROOT",
    "MISSIONS_ROOT",
    "PINBOARD_ROOT",
    "PROPOSALS_ROOT",
    "WORK_PACKETS_ROOT",
    "EDITOR_TASKS_ROOT",
    "INSPECTIONS_ROOT",
    "PROJECTS_ROOT",
    "DATASETS_ROOT",
    "ARCHIVE_ROOT",
    "UI_ROOT",
    "MAIN_UI_ROOT",
    "LOCAL_ROOT",
    "TOOLS_ROOT",
    "RUN_PY",
    "ENVIRONMENT_MANIFEST_PATH",
    "MODEL_SERVER_PID_PATH",
    "MODEL_SERVER_LOG_PATH",
    "WATCH_LOG",
    "SPACESHIP_ROOT",
    "SOURCE_UI_ROOT",
    "DASHBOARD_UI_ROOT",
    "WORKSPACE_ROOT",
    "PathResolver",
    "agent_root",
    "agent_state_root",
    "agent_work_root",
    "agent_runtime_root",
    "agent_memory_root",
    "normalize_agent_name",
    "ensure_core_dirs",
    "ensure_spaceship_on_pythonpath",
    "scan_files",
    "stable_path",
    "resolve_under",
]
