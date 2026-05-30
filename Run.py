#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


PATH_NAMES = (
    "godot",
    "godot4",
    "godot4.6",
    "godot4.5",
    "godot4.4",
    "Godot",
)

LINUX_COMMON_PATHS = (
    Path("/usr/bin/godot"),
    Path("/usr/local/bin/godot"),
    Path("/usr/games/godot"),
    Path("/snap/bin/godot"),
    Path("/opt/godot/godot"),
    Path("/opt/Godot/Godot"),
    Path.home() / ".local/share/flatpak/exports/bin/org.godotengine.Godot",
    Path("/var/lib/flatpak/exports/bin/org.godotengine.Godot"),
)


def _is_windows() -> bool:
    return os.name == "nt"


def _looks_like_godot(path: Path) -> bool:
    name = path.name.lower()
    if "godot" not in name or name == "project.godot":
        return False
    if _is_windows():
        return path.suffix.lower() in {".exe", ".bat", ".cmd"}
    return path.suffix.lower() not in {".exe", ".bat", ".cmd"}


def _is_runnable(path: Path) -> bool:
    if not path.is_file():
        return False
    if _is_windows():
        return path.suffix.lower() in {".exe", ".bat", ".cmd"}
    return os.access(path, os.X_OK)


def _candidate_score(path: Path) -> Tuple[int, str]:
    name = path.name.lower()
    score = 0
    if _is_windows() and "console" not in name:
        score += 10
    if not _is_windows() and "linux" not in name and path.suffix.lower() != ".appimage":
        score += 10
    return score, str(path).lower()


def _scan_tool_root(root: Path) -> List[Path]:
    if not root.is_dir():
        return []
    candidates = [
        path
        for path in root.rglob("*")
        if _looks_like_godot(path) and _is_runnable(path)
    ]
    return sorted(candidates, key=_candidate_score)


def _which_candidates() -> List[Path]:
    names = list(PATH_NAMES)
    if _is_windows():
        names.extend(f"{name}.exe" for name in PATH_NAMES)

    candidates = []
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            path = Path(resolved)
            if _looks_like_godot(path) and _is_runnable(path):
                candidates.append(path)
    return candidates


def find_godot(core_dir: Path) -> Tuple[Optional[Path], List[str]]:
    dashboard_tools = core_dir / "Dashboard" / "Tools"
    home_tools = Path.home() / "Tools"
    searched = [
        str(dashboard_tools),
        str(home_tools),
    ]

    for root in (dashboard_tools, home_tools):
        candidates = _scan_tool_root(root)
        if candidates:
            return candidates[0], searched

    if not _is_windows():
        searched.extend(str(path) for path in LINUX_COMMON_PATHS)
        for path in LINUX_COMMON_PATHS:
            if _looks_like_godot(path) and _is_runnable(path):
                return path, searched

    searched.append("PATH: " + ", ".join(PATH_NAMES))
    path_candidates = _which_candidates()
    if path_candidates:
        return path_candidates[0], searched

    return None, searched


def print_missing_project(core_dir: Path, project_file: Path) -> None:
    print("[ERROR] Dashboard project.godot was not found.")
    print(f"Core directory: {core_dir}")
    print(f"Expected project: {project_file}")


def print_missing_godot(project_file: Path, searched: List[str]) -> None:
    print("[ERROR] Godot executable was not found.")
    print(f"Project file: {project_file}")
    print("Searched:")
    for item in searched:
        print(f"  - {item}")
    print("Place Godot under Dashboard/Tools, ~/Tools, or install it on PATH.")


def main() -> int:
    core_dir = Path(__file__).resolve().parent
    project_file = core_dir / "Dashboard" / "UI" / "project.godot"

    if not project_file.is_file():
        print_missing_project(core_dir, project_file)
        return 1

    godot, searched = find_godot(core_dir)
    if godot is None:
        print_missing_godot(project_file, searched)
        return 1

    print("=== Spaceship Dashboard Launcher ===")
    print(f"Core: {core_dir}")
    print(f"Project: {project_file}")
    print(f"Godot: {godot}")

    env = os.environ.copy()
    env["DASHBOARD_PYTHON"] = sys.executable

    try:
        subprocess.Popen([str(godot), "--path", str(project_file.parent)], env=env)
    except OSError as exc:
        print(f"[ERROR] Failed to launch Godot: {exc}")
        return 1

    print("Godot launched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
