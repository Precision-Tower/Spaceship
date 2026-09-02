# Agency/Core/work/planning/memory.py
from __future__ import annotations

try:
    import yaml
except ImportError:
    from UI import yaml_compat as yaml

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Agency.Core.foundation.paths import DEFAULT_OPERATIONAL_AGENT, agent_memory_root


@dataclass(frozen=True)
class ProjectMemory:
    root: Path
    owner: str = DEFAULT_OPERATIONAL_AGENT

    @property
    def memory_root(self) -> Path:
        return agent_memory_root(self.owner, root=self.root)

    @property
    def project_index_path(self) -> Path:
        return self.memory_root / "project_index.yaml"

    @property
    def long_term_lessons_path(self) -> Path:
        return self.memory_root / "long_term_lessons.yaml"

    @property
    def runtime_patterns_path(self) -> Path:
        return self.memory_root / "runtime_patterns.yaml"

    def ensure(self) -> None:
        self.memory_root.mkdir(parents=True, exist_ok=True)

        ensure_yaml(
            self.project_index_path,
            {
                "projects": {},
            },
        )

        ensure_yaml(
            self.long_term_lessons_path,
            {
                "long_term_lessons": {},
            },
        )

        ensure_yaml(
            self.runtime_patterns_path,
            {
                "runtime_patterns": {},
            },
        )

    def load_project_index(self) -> dict[str, Any]:
        self.ensure()
        return load_yaml(self.project_index_path)

    def save_project_index(self, data: dict[str, Any]) -> None:
        self.project_index_path.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )

    def load_long_term_lessons(self) -> dict[str, Any]:
        self.ensure()
        return load_yaml(self.long_term_lessons_path)

    def save_long_term_lessons(self, data: dict[str, Any]) -> None:
        self.long_term_lessons_path.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )

    def load_runtime_patterns(self) -> dict[str, Any]:
        self.ensure()
        return load_yaml(self.runtime_patterns_path)

    def save_runtime_patterns(self, data: dict[str, Any]) -> None:
        self.runtime_patterns_path.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )

    def register_project(
        self,
        *,
        project_id: str,
        status: str = "active",
        role: str = "",
        source_project_id: str | None = None,
        godot_project_id: str | None = None,
    ) -> None:
        data = self.load_project_index()
        projects = data.setdefault("projects", {})

        projects[project_id] = {
            "status": status,
            "role": role,
            "source_project_id": source_project_id or project_id,
            "godot_project_id": godot_project_id or project_id,
        }

        self.save_project_index(data)

    def project_exists(self, project_id: str) -> bool:
        data = self.load_project_index()
        return project_id in data.get("projects", {})

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        data = self.load_project_index()
        project = data.get("projects", {}).get(project_id)

        if isinstance(project, dict):
            return project

        return None

    def record_long_term_lesson(
        self,
        *,
        lesson_id: str,
        lesson: str,
        source_project: str,
        status: str = "observed",
    ) -> None:
        data = self.load_long_term_lessons()
        lessons = data.setdefault("long_term_lessons", {})

        lessons[lesson_id] = {
            "lesson": lesson,
            "source_project": source_project,
            "status": status,
        }

        self.save_long_term_lessons(data)

    def format_project_index(self) -> str:
        data = self.load_project_index()
        projects = data.get("projects", {})

        if not projects:
            return "PROJECT_MEMORY_INDEX\n(no projects registered)"

        lines = ["PROJECT_MEMORY_INDEX"]

        for project_id, info in projects.items():
            lines.extend(
                [
                    f"- {project_id}",
                    f"  status: {info.get('status', 'unknown')}",
                    f"  source_project_id: {info.get('source_project_id', project_id)}",
                    f"  godot_project_id: {info.get('godot_project_id', project_id)}",
                    f"  role: {info.get('role', '')}",
                ]
            )

        return "\n".join(lines)

    def format_long_term_lessons(self) -> str:
        data = self.load_long_term_lessons()
        lessons = data.get("long_term_lessons", {})

        if not lessons:
            return "PROJECT_LONG_TERM_LESSONS\n(no lessons recorded)"

        lines = ["PROJECT_LONG_TERM_LESSONS"]

        for lesson_id, info in lessons.items():
            lines.extend(
                [
                    f"- {lesson_id}",
                    f"  status: {info.get('status', 'unknown')}",
                    f"  source_project: {info.get('source_project', 'unknown')}",
                    f"  lesson: {info.get('lesson', '')}",
                ]
            )

        return "\n".join(lines)


def ensure_yaml(path: Path, default: dict[str, Any]) -> None:
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(default, sort_keys=False),
        encoding="utf-8",
    )


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    if not isinstance(data, dict):
        return {}

    return data
