# Agency/Core/work/projects/factory.py
from __future__ import annotations

import re
import sys
try:
    import yaml
except ImportError:
    from UI import yaml_compat as yaml

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from Agency.Core.foundation.paths import DASHBOARD_ROOT, PROJECTS_ROOT, stable_path

PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class ProjectCreateResult:
    project_id: str
    project_root: Path
    created: list[Path]
    skipped: list[Path]

    def format(self) -> str:
        lines = [
            "PROJECT_CREATED",
            f"id: {self.project_id}",
            f"path: {stable_path(self.project_root)}",
            "",
            "created:",
        ]

        lines.extend(f"  - {stable_path(path)}" for path in self.created)

        if self.skipped:
            lines.extend(["", "skipped_existing:"])
            lines.extend(f"  - {stable_path(path)}" for path in self.skipped)

        return "\n".join(lines)


def create_project(
    project_id: str,
    *,
    root: Path | None = None,
    force: bool = False,
    seed_goal: bool = True,
) -> ProjectCreateResult:
    """
    Create a lean project package.

    Creates:

        project_dir = PROJECTS_ROOT / project_id
          __init__.py
          project.py
          actions.py
          goals/active/
          goals/done/
          artifacts/
          results/
          memory/
            runtime_lessons.yaml
            success_patterns.yaml
            failure_patterns.yaml

    This function creates structure only.
    It does not register the project automatically.
    It does not execute goals.
    It does not claim validation.
    """
    project_id = normalize_project_id(project_id)
    validate_project_id(project_id)

    root = root or repo_root()
    projects_root = PROJECTS_ROOT
    project_root = projects_root / project_id

    if project_root.exists() and not force:
        raise FileExistsError(
            f"project_already_exists: {stable_path(project_root)} "
            f"(use force=True only if you intend to fill missing skeleton files)"
        )

    created: list[Path] = []
    skipped: list[Path] = []

    dirs = [
        project_root,
        project_root / "goals",
        project_root / "goals" / "active",
        project_root / "goals" / "done",
        project_root / "artifacts",
        project_root / "results",
        project_root / "memory",
    ]

    for directory in dirs:
        ensure_dir(directory, created, skipped)

    write_file(
        project_root / "__init__.py",
        init_py_template(),
        created,
        skipped,
        force=force,
    )

    write_file(
        project_root / "project.py",
        project_py_template(project_id),
        created,
        skipped,
        force=force,
    )

    write_file(
        project_root / "actions.py",
        actions_py_template(project_id),
        created,
        skipped,
        force=force,
    )

    write_file(
        project_root / "memory" / "runtime_lessons.yaml",
        memory_seed_template(project_id, "runtime_lessons"),
        created,
        skipped,
        force=force,
    )

    write_file(
        project_root / "memory" / "success_patterns.yaml",
        memory_seed_template(project_id, "success_patterns"),
        created,
        skipped,
        force=force,
    )

    write_file(
        project_root / "memory" / "failure_patterns.yaml",
        memory_seed_template(project_id, "failure_patterns"),
        created,
        skipped,
        force=force,
    )

    if seed_goal:
        seed_goal_filename = seed_goal_file_name(project_id)

        write_file(
            project_root / "goals" / "active" / seed_goal_filename,
            seed_goal_template(project_id),
            created,
            skipped,
            force=force,
        )

    return ProjectCreateResult(
        project_id=project_id,
        project_root=project_root,
        created=created,
        skipped=skipped,
    )


def normalize_project_id(project_id: str) -> str:
    return project_id.strip().lower().replace("-", "_")


def validate_project_id(project_id: str) -> None:
    if not project_id:
        raise ValueError("missing_project_id")

    if not PROJECT_ID_RE.match(project_id):
        raise ValueError(
            "invalid_project_id: use lowercase letters, numbers, and underscores; "
            "must start with a letter"
        )

    blocked = {
        "lib",
        "registry",
        "__pycache__",
        "tasks",
        "memory",
    }

    if project_id in blocked:
        raise ValueError(f"reserved_project_id: {project_id}")


def ensure_dir(path: Path, created: list[Path], skipped: list[Path]) -> None:
    if path.exists():
        skipped.append(path)
        return

    path.mkdir(parents=True, exist_ok=True)
    created.append(path)


def write_file(
    path: Path,
    text: str,
    created: list[Path],
    skipped: list[Path],
    *,
    force: bool = False,
) -> None:
    if path.exists() and not force:
        skipped.append(path)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    created.append(path)


def init_py_template() -> str:
    return '''from __future__ import annotations

from .project import PROJECT

__all__ = ["PROJECT"]
'''


def project_py_template(project_id: str) -> str:
    project_name = project_id.replace("_", " ").title()

    return f'''from __future__ import annotations

from pathlib import Path

from Agency.Core.work.projects.types import ProjectConfig

from .actions import ACTIONS


PROJECT_ROOT = Path(__file__).resolve().parent

PROJECT = ProjectConfig(
    id="{project_id}",
    name="{project_name}",
    root=PROJECT_ROOT,
    actions=ACTIONS,
    fallback_roots=[
        PROJECT_ROOT / "memory",
        PROJECT_ROOT / "artifacts",
    ],
)
'''


def actions_py_template(project_id: str) -> str:
    action_name = f"generate_{project_id}_artifact"

    return f'''from __future__ import annotations

from pathlib import Path
from typing import Any


def {action_name}(
    *,
    goal: dict[str, Any],
    context: dict[str, Any],
    project: Any,
) -> dict[str, Any]:
    goal_id = str(goal.get("id", "goal_001_seed_artifact"))
    artifact_path = project.root / "artifacts" / f"{{goal_id}}_artifact.md"

    lines = [
        f"# {{goal.get('title', goal_id)}}",
        "",
        f"project_id: `{{project.id}}`",
        f"goal_id: `{{goal_id}}`",
        "",
        "Goal:",
        "",
        str(goal.get("goal", "")).strip(),
        "",
        "Boundary:",
        "This artifact is project-lane output only. It is not validation, runtime truth, or operational readiness.",
        "",
        "Unresolved:",
        "",
        "- Define the first concrete object under observation.",
        "- Preserve unknowns instead of converting them into confidence theater.",
    ]

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("\\n".join(lines).rstrip() + "\\n", encoding="utf-8")

    return {{
        "status": "pass",
        "mutation": "{project_id}_artifact_written",
        "files_written": [
            artifact_path,
        ],
    }}


ACTIONS = {{
    "{action_name}": {action_name},
}}
'''


def memory_seed_template(project_id: str, memory_type: str) -> str:
    data: dict[str, Any] = {
        memory_type: {
            "project_id": project_id,
            "status": "seed",
            "authority": "project_memory_only_not_validation",
            "items": [],
        }
    }

    return yaml.safe_dump(data, sort_keys=False)


def seed_goal_template(project_id: str) -> str:
    action_name = f"generate_{project_id}_artifact"

    if project_id == "boat":
        data: dict[str, Any] = {
            "id": "goal_001_floating_barrel_artifact",
            "action": "generate_boat_artifact",
            "title": "Create floating barrel starting artifact",
            "goal": (
                "Create the first boat project artifact: a floating barrel concept "
                "with visible float behavior, disturbance behavior, unresolved buoyancy "
                "variables, and no stability or validation claims."
            ),
        }
    else:
        data = {
            "id": "goal_001_seed_artifact",
            "action": action_name,
            "title": f"Create {project_id} seed artifact",
            "goal": (
                f"Create the first {project_id} project artifact with visible unresolveds, "
                "clear authority boundaries, and no validation claims."
            ),
        }

    return yaml.safe_dump(data, sort_keys=False)

def seed_goal_file_name(project_id: str) -> str:
    if project_id == "boat":
        return "goal_001_floating_barrel_artifact.yaml"

    return "goal_001_seed_artifact.yaml"

def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def stable_path(path: Path) -> str:
    root = repo_root()
    resolved = path.resolve()

    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return str(resolved)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="project-factory")
    parser.add_argument("project_id")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-seed-goal", action="store_true")

    args = parser.parse_args(argv)

    try:
        result = create_project(
            args.project_id,
            force=args.force,
            seed_goal=not args.no_seed_goal,
        )
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 1

    print(result.format())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
