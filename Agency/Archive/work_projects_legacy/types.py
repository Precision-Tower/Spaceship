# Agency/Core/work/projects/types.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol


ActionResult = dict[str, Any]
ProjectContext = dict[str, Any]
GoalPacket = dict[str, Any]


class ProjectAction(Protocol):
    def __call__(
        self,
        *,
        goal: GoalPacket,
        context: ProjectContext,
        project: ProjectConfig,
    ) -> ActionResult:
        ...


@dataclass(frozen=True)
class ProjectConfig:
    id: str
    name: str
    root: Path
    actions: dict[str, ProjectAction]
    fallback_roots: list[Path] = field(default_factory=list)

    authority: str = "project_lane_only_not_validation"
    mode: str = "bounded_project_execution"

    def goals_active_dir(self) -> Path:
        return self.root / "goals" / "active"

    def goals_done_dir(self) -> Path:
        return self.root / "goals" / "done"

    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    def results_dir(self) -> Path:
        return self.root / "results"

    def memory_dir(self) -> Path:
        return self.root / "memory"


@dataclass(frozen=True)
class ProjectRunResult:
    project_id: str
    goal_id: str | None
    action: str | None
    status: str
    artifact: Path | None = None
    result: Path | None = None
    error: str | None = None

    def ok(self) -> bool:
        return self.status in {"pass", "already_satisfied", "no_active_goals"}


@dataclass(frozen=True)
class ProjectCreateResult:
    project_id: str
    project_root: Path
    created: list[Path]
    skipped: list[Path]


@dataclass(frozen=True)
class ContextPacket:
    query: str
    vector: dict[str, Any]
    fallback: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "vector": self.vector,
            "fallback": self.fallback,
        }
