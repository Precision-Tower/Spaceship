from __future__ import annotations

import shutil
import subprocess
import sys
try:
    import yaml
except ImportError:
    from UI import yaml_compat as yaml

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from Agency.Core.work.projects.types import ProjectConfig

Action = Callable[..., dict[str, Any]]


PASS_STATUSES = {
    "pass",
    "already_satisfied",
}


def run_next_goal(project: ProjectConfig) -> int:
    goal_path = find_active_goal(project)

    if goal_path is None:
        print(f"NO_ACTIVE_GOALS: {project.id}")
        return 0

    try:
        goal = load_goal(goal_path)
        context = build_context(project, goal)
        artifact_path = write_context_artifact(project, goal, context)

        execution = execute_project_action(
            project=project,
            goal=goal,
            context=context,
        )

        result_path = write_result(
            project=project,
            goal=goal,
            context=context,
            artifact_path=artifact_path,
            execution=execution,
        )

        if execution.get("status") in PASS_STATUSES:
            move_goal_to_done(project, goal_path)

        print(
            yaml.safe_dump(
                {
                    "project_id": project.id,
                    "goal_id": goal.get("id"),
                    "action": goal.get("action"),
                    "status": execution.get("status"),
                    "artifact": stable_path(artifact_path),
                    "result": stable_path(result_path),
                },
                sort_keys=False,
            ).strip()
        )

        return 0 if execution.get("status") in PASS_STATUSES else 1

    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 1


def find_active_goal(project: ProjectConfig) -> Path | None:
    active_dir = project.root / "goals" / "active"

    if not active_dir.exists():
        return None

    goals = sorted(
        path for path in active_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
    )

    return goals[0] if goals else None


def load_goal(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"goal_not_mapping: {path}")

    goal_text = str(data.get("goal", "")).strip()
    if not goal_text:
        raise ValueError(f"empty_goal_text: {path}")

    if not str(data.get("id", "")).strip():
        raise ValueError(f"missing_goal_id: {path}")

    if not str(data.get("action", "")).strip():
        raise ValueError(f"missing_goal_action: {path}")

    return data


def build_context(project: ProjectConfig, goal: dict[str, Any]) -> dict[str, Any]:
    query = str(goal.get("query") or goal.get("goal") or "").strip()

    vector = attempt_vector_retrieval(query)
    fallback = fallback_context(
        query=query,
        roots=project.fallback_roots,
    ) if not vector["used"] else []

    return {
        "query": query,
        "vector": vector,
        "fallback": fallback,
    }


def attempt_vector_retrieval(query: str) -> dict[str, Any]:
    root = repo_root()

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "Agency.Core.agents.tooling.Chroma.query_index",
            "Editor",
            query,
        ],
        cwd=root,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    return {
        "used": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def summarize_vector_failure(vector: dict[str, Any]) -> str:
    stderr = str(vector.get("stderr", "") or "").strip()
    returncode = vector.get("returncode")

    if "vector_tool_not_found" in stderr:
        return "vector_tool_not_found"

    if not stderr:
        return f"vector_retrieval_failed_returncode_{returncode}_stderr_empty"

    return f"vector_retrieval_failed_returncode_{returncode}_stderr_suppressed_for_memory_hygiene"


def fallback_context(
    query: str,
    roots: list[Path],
    limit: int = 6,
) -> list[dict[str, Any]]:
    terms = keyword_terms(query)
    matches: list[dict[str, Any]] = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not is_searchable(path):
                continue

            text = path.read_text(encoding="utf-8", errors="replace")
            score = score_text(text, terms)

            if score <= 0:
                continue

            matches.append(
                {
                    "path": stable_path(path),
                    "score": score,
                    "snippet": snippet_for(text, terms),
                }
            )

    matches.sort(key=lambda item: (-item["score"], item["path"]))
    return matches[:limit]


def write_context_artifact(
    project: ProjectConfig,
    goal: dict[str, Any],
    context: dict[str, Any],
) -> Path:
    goal_id = str(goal["id"])
    artifact_path = project.root / "artifacts" / f"{goal_id}_memory_context.md"

    vector = context["vector"]
    fallback = context["fallback"]

    lines = [
        f"# {goal_id} Memory Context",
        "",
        f"project_id: `{project.id}`",
        f"action: `{goal.get('action')}`",
        "",
        "Goal:",
        "",
        str(goal.get("goal", "")).strip(),
        "",
        "Boundary:",
        "Retrieval is context only. Retrieval is not validation. Artifact is not runtime truth.",
        "",
        "## Vector Retrieval",
        "",
        f"returncode: `{vector['returncode']}`",
        f"used: `{str(vector['used']).lower()}`",
    ]

    if not vector["used"]:
        lines.extend(
            [
                "",
                "Vector retrieval was unavailable or returned no successful result.",
                "",
                "failure_summary:",
                "```text",
                summarize_vector_failure(vector),
                "```",
            ]
        )

    lines.extend(["", "## Fallback Context", ""])

    if not fallback:
        lines.append("No fallback matches found.")
    else:
        for index, item in enumerate(fallback, start=1):
            lines.extend(
                [
                    f"### Match {index}",
                    "",
                    f"path: `{item['path']}`",
                    f"score: `{item['score']}`",
                    "",
                    "```text",
                    item["snippet"],
                    "```",
                    "",
                ]
            )

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return artifact_path


def execute_project_action(
    project: ProjectConfig,
    goal: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    action_name = str(goal.get("action", "")).strip()
    action = project.actions.get(action_name)

    if action is None:
        return {
            "status": "fail",
            "error": f"unknown_action: {action_name}",
            "mutation": "none",
            "files_written": [],
        }

    result = action(
        goal=goal,
        context=context,
        project=project,
    )

    if not isinstance(result, dict):
        return {
            "status": "fail",
            "error": f"action_returned_non_mapping: {action_name}",
            "mutation": "unknown",
            "files_written": [],
        }

    result.setdefault("status", "pass")
    result.setdefault("mutation", "unspecified")
    result.setdefault("files_written", [])

    return result


def write_result(
    project: ProjectConfig,
    goal: dict[str, Any],
    context: dict[str, Any],
    artifact_path: Path,
    execution: dict[str, Any],
) -> Path:
    goal_id = str(goal["id"])
    result_path = project.root / "results" / f"{goal_id}_result.yaml"

    vector = context["vector"]
    fallback = context["fallback"]

    files_written = [
        stable_path(artifact_path),
        stable_path(result_path),
    ]

    for file_path in execution.get("files_written", []):
        files_written.append(stable_path(Path(file_path)))

    packet = {
        "ProjectResult": {
            "project_id": project.id,
            "goal_id": goal_id,
            "action": goal.get("action"),
            "status": execution.get("status"),
            "mode": "project_lane_only",
            "authority": "proving_ground_only_not_task_substrate",
            "mutation": execution.get("mutation"),
            "vector_retrieval_used": bool(vector["used"]),
            "vector_returncode": vector["returncode"],
            "fallback_used": not bool(vector["used"]),
            "fallback_match_count": len(fallback),
            "artifact": stable_path(artifact_path),
            "files_written": dedupe(files_written),
            "blocked_paths": [
                "Agency/Agents/*/work/Tasks/",
                "Agency/Agents/*/work/Projects/godot_playground/",
            ],
            "claims_blocked": [
                "retrieval_context_equals_validation",
                "artifact_equals_runtime_truth",
                "project_lane_equals_task_substrate",
                "visual_float_equals_stability",
                "runtime_behavior_equals_validation",
            ],
        }
    }

    if execution.get("error"):
        packet["ProjectResult"]["error"] = execution["error"]

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        yaml.safe_dump(packet, sort_keys=False),
        encoding="utf-8",
    )

    return result_path


def move_goal_to_done(project: ProjectConfig, goal_path: Path) -> Path:
    done_dir = project.root / "goals" / "done"
    done_dir.mkdir(parents=True, exist_ok=True)

    target = done_dir / goal_path.name

    if target.exists():
        target = done_dir / f"{goal_path.stem}_{int(target.stat().st_mtime)}{goal_path.suffix}"

    shutil.move(str(goal_path), str(target))
    return target


def keyword_terms(query: str) -> list[str]:
    raw_terms = [
        term.strip(".,:;!?()[]{}\"'").lower()
        for term in query.replace("_", " ").split()
    ]

    terms = [term for term in raw_terms if len(term) >= 4]
    return sorted(set(terms))


def score_text(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def snippet_for(text: str, terms: list[str], width: int = 900) -> str:
    lowered = text.lower()

    first_hit = min(
        (lowered.find(term) for term in terms if lowered.find(term) >= 0),
        default=0,
    )

    start = max(0, first_hit - 180)
    snippet = text[start:start + width].strip()
    return sanitize_memory_snippet(snippet.replace("\r\n", "\n"))

def sanitize_memory_snippet(text: str) -> str:
    markers = [
        "Warning: You are sending unauthenticated requests",
        "Loading weights:",
    ]

    lines = []
    for line in text.splitlines():
        if any(marker in line for marker in markers):
            continue
        lines.append(line)

    return "\n".join(lines).strip()

def is_searchable(path: Path) -> bool:
    if not path.is_file():
        return False

    if "__pycache__" in path.parts:
        return False

    return path.suffix.lower() in {
        ".yaml",
        ".yml",
        ".md",
        ".txt",
        ".gd",
        ".py",
        ".json",
    }


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    output = []

    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)

    return output


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def stable_path(path: Path) -> str:
    root = repo_root()
    resolved = path.resolve()

    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return str(resolved)
