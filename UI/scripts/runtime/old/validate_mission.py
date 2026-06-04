#!/usr/bin/env python3
"""Validate Mission parser/renderer without starting Godot.

Reads Bridge/Core/Dashboard/UI/Mission.yaml and prints the
rendered mission text exactly as the dashboard would display it.

Non-invasive: does not modify repo files.
"""
from pathlib import Path
import sys


def load_yaml_simple(path: Path):
    try:
        import yaml
    except Exception:
        yaml = None

    if yaml:
        with open(path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f) or {}
            except Exception:
                pass

    # Fallback simple parser for top-level keys and a top-level tasks list
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "":
                # Possibly a list block
                if key == "tasks":
                    lst = []
                    i += 1
                    while i < len(lines) and lines[i].lstrip().startswith("-"):
                        item = lines[i].lstrip()[1:].strip()
                        lst.append(item)
                        i += 1
                    data["tasks"] = lst
                    continue
                else:
                    data[key] = None
            else:
                data[key] = val

        i += 1

    return data


def render_mission(data: dict) -> str:
    parts = []

    goal = data.get("goal") or data.get("name")
    if goal:
        parts.append("Current Goal:")
        parts.append(str(goal))
        parts.append("")

    decision = data.get("decision")
    if decision:
        parts.append("Current Decision:")
        parts.append(str(decision))
        parts.append("")

    observed = data.get("observed")
    if observed:
        parts.append("Observed:")
        parts.append(str(observed))
        parts.append("")

    recommendation = data.get("recommendation")
    if recommendation:
        parts.append("Recommendation:")
        parts.append(str(recommendation))
        parts.append("")

    next_action = data.get("next_action") or data.get("phase")
    if next_action:
        parts.append("Next:")
        parts.append(str(next_action))
        parts.append("")

    tasks = data.get("tasks") or []
    if isinstance(tasks, str):
        tasks = [tasks]
    # Tasks may be a list of mappings with 'label' and 'status'
    if tasks:
        parts.append("Top Tasks:")
        for t in tasks[:5]:
            label = None
            status = None
            if isinstance(t, dict):
                label = t.get("label") or t.get("name") or str(t)
                status = (t.get("status") or "").lower()
            else:
                label = str(t)
                status = ""

            if status == "complete":
                marker = "[x]"
            elif status == "in_progress" or status == "in-progress":
                marker = "[~]"
            elif status == "pending":
                marker = "[ ]"
            else:
                marker = "[ ]"

            parts.append(f"{marker} {label}")
        parts.append("")

    if not parts:
        return "(Mission file empty or unrecognized format)"

    return "\n".join(parts).strip()


def main():
    script_dir = Path(__file__).resolve().parent
    ui_dir = script_dir.parent.parent
    mission_file = ui_dir / "Mission.yaml"

    if not mission_file.exists():
        print(f"MISSION_FILE_NOT_FOUND: {mission_file}")
        sys.exit(0)

    data = load_yaml_simple(mission_file) or {}

    # Normalize nested structure: prefer top-level 'Mission' mapping if present
    if isinstance(data, dict) and "Mission" in data and isinstance(data["Mission"], dict):
        data = data["Mission"]

    # Backward-compatible field mapping: support 'current_phase' as 'phase'
    if isinstance(data, dict) and "phase" not in data and "current_phase" in data:
        data["phase"] = data.get("current_phase")

    text = render_mission(data)
    print(text)

class MissionValidator:
    def __init__(self, mission_path: Path | None = None):
        if mission_path is None:
            script_dir = Path(__file__).resolve().parent
            ui_dir = script_dir.parent.parent
            mission_path = ui_dir / "Mission.yaml"

        self.mission_path = Path(mission_path)

    def load(self) -> dict:
        if not self.mission_path.exists():
            return {}

        data = load_yaml_simple(self.mission_path) or {}

        if isinstance(data, dict) and "Mission" in data and isinstance(data["Mission"], dict):
            data = data["Mission"]

        if isinstance(data, dict) and "phase" not in data and "current_phase" in data:
            data["phase"] = data.get("current_phase")

        return data

    def render(self) -> str:
        return render_mission(self.load())

    def validate(self) -> dict:
        exists = self.mission_path.exists()
        data = self.load() if exists else {}

        return {
            "ok": exists and bool(data),
            "mission_path": str(self.mission_path),
            "exists": exists,
            "recognized": bool(data),
            "rendered": render_mission(data) if data else "",
        }

if __name__ == "__main__":
    main()

