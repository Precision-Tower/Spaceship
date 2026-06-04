from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


class MissionMemory:
    """Read-only active mission memory for Weebo proposal checks."""

    REQUIRED_FIELDS = (
        "mission_id",
        "current_goal",
        "active_phase",
        "near_term_objective",
        "blocked_work",
        "allowed_work",
        "next_safe_step",
        "source_notes",
    )

    def __init__(self, spaceship_root: Path | str | None = None):
        if spaceship_root is None:
            spaceship_root = Path(__file__).resolve().parents[3]

        self.root = Path(spaceship_root).resolve()
        self.mission_path = self.root / "UI" / "Weebo" / "memory" / "active_mission.yaml"

    def load_mission(self) -> dict[str, Any]:
        if not self.mission_path.exists():
            return self._empty_mission("active_mission.yaml is missing")

        text = self.mission_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) if yaml else self._fallback_load(text)
        if isinstance(data, dict) and "active_mission" in data and isinstance(data["active_mission"], dict):
            data = data["active_mission"]
        if not isinstance(data, dict):
            return self._empty_mission("active_mission.yaml did not parse to a mapping")

        mission = dict(data)
        for field in self.REQUIRED_FIELDS:
            if field not in mission:
                mission[field] = [] if field in {"blocked_work", "allowed_work", "source_notes"} else ""

        return mission

    def format_mission(self) -> str:
        mission = self.load_mission()
        lines = [
            "ACTIVE MISSION",
            "",
            f"mission_id: {mission.get('mission_id', '')}",
            f"current_goal: {mission.get('current_goal', '')}",
            f"active_phase: {mission.get('active_phase', '')}",
            f"near_term_objective: {mission.get('near_term_objective', '')}",
            "",
            "Allowed work:",
        ]
        lines.extend(f"- {item}" for item in mission.get("allowed_work", []) or [])
        lines.append("")
        lines.append("Blocked work:")
        lines.extend(f"- {item}" for item in mission.get("blocked_work", []) or [])
        lines.append("")
        lines.append(f"next_safe_step: {mission.get('next_safe_step', '')}")
        lines.append("")
        lines.append("Source notes:")
        lines.extend(f"- {item}" for item in mission.get("source_notes", []) or [])
        return "\n".join(lines)

    def format_focus(self) -> str:
        mission = self.load_mission()
        return "\n".join(
            [
                "CURRENT FOCUS",
                "",
                f"goal: {mission.get('current_goal', '')}",
                f"phase: {mission.get('active_phase', '')}",
                f"near_term_objective: {mission.get('near_term_objective', '')}",
            ]
        )

    def format_next(self) -> str:
        mission = self.load_mission()
        lines = [
            "NEXT SAFE STEP",
            "",
            f"- {mission.get('next_safe_step', '')}",
            "",
            "Allowed now:",
        ]
        lines.extend(f"- {item}" for item in mission.get("allowed_work", []) or [])
        lines.append("")
        lines.append("Still blocked:")
        lines.extend(f"- {item}" for item in mission.get("blocked_work", []) or [])
        return "\n".join(lines)

    def format_mission_check(self) -> str:
        mission = self.load_mission()
        lines = [
            "ACTIVE MISSION CHECK",
            "",
            f"current_goal: {mission.get('current_goal', '')}",
            f"active_phase: {mission.get('active_phase', '')}",
            f"near_term_objective: {mission.get('near_term_objective', '')}",
            f"next_safe_step: {mission.get('next_safe_step', '')}",
            "",
            "Blocked work:",
        ]
        lines.extend(f"- {item}" for item in mission.get("blocked_work", []) or [])
        lines.append("")
        lines.append("Allowed work:")
        lines.extend(f"- {item}" for item in mission.get("allowed_work", []) or [])
        return "\n".join(lines)

    def _fallback_load(self, text: str) -> dict[str, Any]:
        data: dict[str, Any] = {}
        active_list_key: str | None = None

        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.endswith(":") and not stripped.startswith("- "):
                active_list_key = stripped[:-1].strip()
                data[active_list_key] = []
                continue

            if active_list_key and stripped.startswith("- "):
                data[active_list_key].append(self._clean_scalar(stripped[2:]))
                continue

            if ":" in stripped:
                active_list_key = None
                field, value = stripped.split(":", 1)
                data[field.strip()] = self._clean_scalar(value)

        return data

    def _empty_mission(self, reason: str) -> dict[str, Any]:
        return {
            "mission_id": "missing",
            "current_goal": reason,
            "active_phase": "unknown",
            "near_term_objective": "",
            "blocked_work": [],
            "allowed_work": [],
            "next_safe_step": "",
            "source_notes": [reason],
        }

    def _clean_scalar(self, value: str) -> str:
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        return value

