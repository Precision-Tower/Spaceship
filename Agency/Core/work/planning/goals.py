# Agency/Core/work/planning/goals.py
from __future__ import annotations

import re
try:
    import yaml
except ImportError:
    from UI import yaml_compat as yaml

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Agency.Core.foundation.paths import PROJECTS_ROOT

GOAL_ID_RE = re.compile(r"[^a-z0-9_]+")


@dataclass(frozen=True)
class GoalCreateResult:
    project_id: str
    goal_id: str
    goal_path: Path
    action: str
    title: str

    def format(self) -> str:
        return "\n".join(
            [
                "PROJECT_GOAL_CREATED",
                f"project_id: {self.project_id}",
                f"goal_id: {self.goal_id}",
                f"action: {self.action}",
                f"title: {self.title}",
                f"path: {self.goal_path}",
            ]
        )


def create_goal(
    *,
    root: Path,
    project_id: str,
    title: str,
    action: str | None = None,
    goal_text: str | None = None,
) -> GoalCreateResult:
    project_id = normalize_project_id(project_id)
    project_root = PROJECTS_ROOT / project_id
    if not project_root.exists():
        raise FileNotFoundError(f"project_not_found: {project_root}")

    active_dir = project_root / "goals" / "active"
    active_dir.mkdir(parents=True, exist_ok=True)

    next_number = next_goal_number(project_root)
    goal_id = build_goal_id(next_number, title)

    action = action or infer_action(project_id, title)
    goal_text = goal_text or build_goal_text(title)

    goal_path = active_dir / f"{goal_id}.yaml"

    if goal_path.exists():
        raise FileExistsError(f"goal_already_exists: {goal_path}")

    packet: dict[str, Any] = {
        "id": goal_id,
        "action": action,
        "title": title,
        "goal": goal_text,
        "created_by": "Editor",
        "authority": "project_goal_packet_only_not_validation",
        "claims_blocked": [
            "goal_created_equals_work_completed",
            "planned_action_equals_runtime_result",
            "visual_output_equals_validation",
            "runtime_launch_equals_operational_readiness",
        ],
    }

    goal_path.write_text(
        yaml.safe_dump(packet, sort_keys=False),
        encoding="utf-8",
    )

    return GoalCreateResult(
        project_id=project_id,
        goal_id=goal_id,
        goal_path=goal_path,
        action=action,
        title=title,
    )


def next_goal_number(project_root: Path) -> int:
    max_seen = 0

    for folder in [
        project_root / "goals" / "active",
        project_root / "goals" / "done",
    ]:
        if not folder.exists():
            continue

        for path in folder.glob("goal_*.yaml"):
            match = re.match(r"goal_(\d+)_", path.stem)
            if not match:
                continue

            max_seen = max(max_seen, int(match.group(1)))

    return max_seen + 1


def build_goal_id(number: int, title: str) -> str:
    slug = slugify(title)
    return f"goal_{number:03d}_{slug}"


def slugify(text: str) -> str:
    lowered = text.strip().lower().replace("-", "_")
    lowered = GOAL_ID_RE.sub("_", lowered)
    lowered = re.sub(r"_+", "_", lowered).strip("_")

    if not lowered:
        return "untitled_goal"

    return lowered[:70]


def normalize_project_id(project_id: str) -> str:
    return project_id.strip().lower().replace("-", "_")


def infer_action(project_id: str, title: str) -> str:
    text = title.lower()

    if project_id == "boat":
        if "buoyancy" in text or "calculation" in text or "float" in text:
            return "create_buoyancy_calculation_record"

        if "observation" in text or "record" in text:
            return "record_runtime_observation"

        if "godot" in text or "scene" in text:
            return "create_boat_godot_scene"

        if "runtime" in text or "disturb" in text or "barrel" in text:
            return "modify_boat_runtime"

        return "record_runtime_observation"


def build_goal_text(title: str) -> str:
    return (
        f"{title}. Preserve unresolveds, record boundaries, and do not promote "
        "planned work, visual output, runtime launch, or generated artifacts into "
        "validation claims."
    )
