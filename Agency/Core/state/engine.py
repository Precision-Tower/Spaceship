from __future__ import annotations

from pathlib import Path
from typing import Any

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
UI_ROOT = DASHBOARD_ROOT / "UI"
AGENCY_ROOT = DASHBOARD_ROOT / "Agency"
AGENTS_ROOT = AGENCY_ROOT / "Agents"

from Agency.Core.foundation.paths import PROJECTS_ROOT

def stable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(DASHBOARD_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def write_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def init_agent_state(agent_name: str) -> dict[str, Any]:
    agent_name = normalize_name(agent_name)
    agent_dir = AGENTS_ROOT / agent_name
    state_dir = agent_dir / "state"

    created: list[str] = []
    preserved: list[str] = []

    files = {
        state_dir / "agent_state.yaml": render_agent_state(agent_name),
        state_dir / "transition_log.yaml": render_agent_transition_log(agent_name),
        state_dir / "README.md": render_agent_state_readme(agent_name),
    }

    for path, text in files.items():
        if write_if_missing(path, text):
            created.append(stable_path(path))
        else:
            preserved.append(stable_path(path))

    return {
        "kind": "agent",
        "owner": agent_name,
        "state_dir": stable_path(state_dir),
        "created": created,
        "preserved_existing": preserved,
        "authority": "state_scaffold_only_not_runtime_authority",
    }


def init_project_state(project_id: str) -> dict[str, Any]:
    project_id = normalize_project_id(project_id)
    project_dir = PROJECTS_ROOT / project_id
    state_dir = project_dir / "state"

    created: list[str] = []
    preserved: list[str] = []

    files = {
        state_dir / "project_state.yaml": render_project_state(project_id),
        state_dir / "transition_log.yaml": render_project_transition_log(project_id),
        state_dir / "README.md": render_project_state_readme(project_id),
    }

    for path, text in files.items():
        if write_if_missing(path, text):
            created.append(stable_path(path))
        else:
            preserved.append(stable_path(path))

    return {
        "kind": "project",
        "owner": project_id,
        "state_dir": stable_path(state_dir),
        "created": created,
        "preserved_existing": preserved,
        "authority": "state_scaffold_only_not_runtime_authority",
    }

def render_project_state_readme(project_id: str) -> str:
    return f"""# {project_id} Project State

This directory contains explicit project state for `{project_id}`.

Project state is not artifacts.
Project state is not memory.
Project state is not simulation validation.

All future state changes should be represented by transition events.

Authority:
explicit_state_model_not_validation
"""

def agent_state_status(agent_name: str) -> dict[str, Any]:
    agent_name = normalize_name(agent_name)
    agent_dir = AGENTS_ROOT / agent_name
    state_dir = agent_dir / "state"

    paths = {
        "agent_dir": agent_dir,
        "state_dir": state_dir,
        "state": state_dir / "agent_state.yaml",
        "transition_log": state_dir / "transition_log.yaml",
        "readme": state_dir / "README.md",
        "runtime": agent_dir / "runtime.yaml",
        "memory_sources": agent_dir / "memory" / "sources.yaml",
    }

    return {
        "kind": "agent",
        "owner": agent_name,
        "exists": agent_dir.exists(),
        "state_ready": all(
            paths[key].exists()
            for key in ("state", "transition_log", "readme")
        ),
        "connected_to_runtime": paths["runtime"].exists(),
        "connected_to_memory": paths["memory_sources"].exists(),
        "active": False,
        "authority": "state_status_only_not_runtime_authority",
        "paths": {key: stable_path(path) for key, path in paths.items()},
    }


def project_state_status(project_id: str) -> dict[str, Any]:
    project_id = normalize_project_id(project_id)
    project_dir = PROJECTS_ROOT / project_id
    state_dir = project_dir / "state"

    paths = {
        "project_dir": project_dir,
        "state_dir": state_dir,
        "state": state_dir / "project_state.yaml",
        "transition_log": state_dir / "transition_log.yaml",
        "readme": state_dir / "README.md",
        "actions": project_dir / "actions.py",
        "project": project_dir / "project.py",
    }

    return {
        "kind": "project",
        "owner": project_id,
        "exists": project_dir.exists(),
        "state_ready": all(
            paths[key].exists()
            for key in ("state", "transition_log", "readme")
        ),
        "connected_to_actions": paths["actions"].exists(),
        "connected_to_project": paths["project"].exists(),
        "active": False,
        "authority": "state_status_only_not_runtime_authority",
        "paths": {key: stable_path(path) for key, path in paths.items()},
    }


def normalize_name(raw: str) -> str:
    cleaned = "".join(ch for ch in raw.strip() if ch.isalnum() or ch == "_")
    if not cleaned:
        raise ValueError("name_empty")
    return cleaned[:1].upper() + cleaned[1:]


def normalize_project_id(raw: str) -> str:
    cleaned = raw.strip().lower().replace("-", "_")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch == "_")
    if not cleaned:
        raise ValueError("project_id_empty")
    return cleaned


def render_agent_state(agent_name: str) -> str:
    return f"""AgentState:
  owner: {agent_name}

  status: scaffold
  active: false

  authority: state_scaffold_only_not_runtime_authority

  activation:
    connected_to_runtime: false
    connected_to_memory: false
    connected_to_actions: false
    last_verified_command: null

  current:
    focus: null
    capabilities: []
    open_questions: []
    risks: []

  rules:
    - state_is_explicit_not_implied
    - inactive_state_is_not_runtime_authority
    - activation_requires_verified_route
    - transitions_required_for_state_changes
"""


def render_project_state(project_id: str) -> str:
    return f"""ProjectState:
  project_id: {project_id}

  status: scaffold
  active: false

  objectives: []

  constraints: []

  assumptions: []

  resources: []

  risks: []

  open_questions: []

  current_phase: null

  authority: explicit_state_model_not_validation

  rules:
    - project_state_is_explicit_not_implied
    - artifacts_are_not_state
    - memory_is_not_state
    - transitions_required_for_state_changes
"""


def render_agent_transition_log(agent_name: str) -> str:
    return f"""TransitionLog:
  owner: {agent_name}
  kind: agent
  authority: transition_history_not_truth
  events: []
"""


def render_project_transition_log(project_id: str) -> str:
    return f"""TransitionLog:
  owner: {project_id}
  kind: project
  authority: transition_history_not_truth
  events: []
"""


def render_agent_state_readme(agent_name: str) -> str:
    return f"""# {agent_name} State

This directory contains explicit state for `{agent_name}`.

State is not memory.
State is not retrieval.
State is not model output.

State becomes active only after verified runtime connection.

Authority:
state_scaffold_only_not_runtime_authority
"""

def main(argv: list[str] | None = None) -> int:
    import json
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        print(
            "usage: python Run.py state "
            "<init-agent|status-agent|init-project|status-project|"
            "transition-agent|transition-project|"
            "record-agent|record-project|"
            "log-agent|log-project> ..."
        )
        return 2

    command = argv[0].strip().lower()

    if len(argv) < 2:
        print(f"ERR: missing target for state command: {command}")
        return 2

    target = argv[1].strip()

    try:
        if command == "init-agent":
            result = init_agent_state(target)

        elif command == "status-agent":
            result = agent_state_status(target)

        elif command == "init-project":
            result = init_project_state(target)

        elif command == "status-project":
            result = project_state_status(target)

        elif command == "transition-agent":
            if len(argv) < 4:
                print(
                    'usage: python Run.py state transition-agent '
                    '<agent> <new_status> "<reason>"'
                )
                return 2

            from Agency.Core.state.transitions import transition_agent_status

            result = transition_agent_status(
                target,
                argv[2].strip(),
                " ".join(argv[3:]).strip(),
            )

        elif command == "transition-project":
            if len(argv) < 4:
                print(
                    'usage: python Run.py state transition-project '
                    '<project> <new_status> "<reason>"'
                )
                return 2

            from Agency.Core.state.transitions import transition_project_status

            result = transition_project_status(
                target,
                argv[2].strip(),
                " ".join(argv[3:]).strip(),
            )

        elif command == "record-agent":
            if len(argv) < 3:
                print(
                    'usage: python Run.py state record-agent '
                    '<agent> "<reason>"'
                )
                return 2

            from Agency.Core.state.event_log import append_agent_event

            result = append_agent_event(
                target,
                " ".join(argv[2:]).strip(),
            )

        elif command == "record-project":
            if len(argv) < 3:
                print(
                    'usage: python Run.py state record-project '
                    '<project> "<reason>"'
                )
                return 2

            from Agency.Core.state.event_log import append_project_event

            result = append_project_event(
                target,
                " ".join(argv[2:]).strip(),
            )

        elif command == "log-agent":
            from Agency.Core.state.event_log import read_agent_events

            result = read_agent_events(target)

        elif command == "log-project":
            from Agency.Core.state.event_log import read_project_events

            result = read_project_events(target)

        elif command == "replay-project":
            from Agency.Core.state.replay import replay_project

            result = replay_project(target)

        elif command == "replay-agent":
            from Agency.Core.state.replay import replay_agent

            result = replay_agent(target)

        else:
            print(f"ERR: unknown state command: {command}")
            return 2

    except Exception as exc:
        print(f"ERR: {exc}")
        return 1

    print(json.dumps(result, indent=2))
    return 0
