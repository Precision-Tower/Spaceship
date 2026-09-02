from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from Agency.Core.foundation.paths import AGENTS_ROOT, PROJECTS_ROOT, stable_path


def normalize_agent_name(raw: str) -> str:
    cleaned = "".join(ch for ch in raw.strip() if ch.isalnum() or ch == "_")
    if not cleaned:
        raise ValueError("agent_name_empty")
    return cleaned[:1].upper() + cleaned[1:]


def normalize_project_id(raw: str) -> str:
    cleaned = raw.strip().lower().replace("-", "_")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch == "_")
    if not cleaned:
        raise ValueError("project_id_empty")
    return cleaned


def agent_paths(agent_name: str) -> dict[str, Path]:
    agent_name = normalize_agent_name(agent_name)
    root = AGENTS_ROOT / agent_name / "state"
    return {
        "state": root / "agent_state.yaml",
        "log": root / "transition_log.yaml",
    }


def project_paths(project_id: str) -> dict[str, Path]:
    project_id = normalize_project_id(project_id)
    root = PROJECTS_ROOT / project_id / "state"
    return {
        "state": root / "project_state.yaml",
        "log": root / "transition_log.yaml",
    }


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing_file: {stable_path(path)}")

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def extract_status(state_data: dict[str, Any]) -> str | None:
    for key in ("AgentState", "ProjectState"):
        value = state_data.get(key)
        if isinstance(value, dict):
            return value.get("status")
    return None


def extract_events(log_data: dict[str, Any]) -> list[dict[str, Any]]:
    log = log_data.get("TransitionLog", {})
    events = log.get("events", [])
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict)]


def replay_agent(agent_name: str) -> dict[str, Any]:
    agent_name = normalize_agent_name(agent_name)
    paths = agent_paths(agent_name)
    return replay(
        kind="agent",
        owner=agent_name,
        state_path=paths["state"],
        log_path=paths["log"],
    )


def replay_project(project_id: str) -> dict[str, Any]:
    project_id = normalize_project_id(project_id)
    paths = project_paths(project_id)
    return replay(
        kind="project",
        owner=project_id,
        state_path=paths["state"],
        log_path=paths["log"],
    )


def replay(kind: str, owner: str, state_path: Path, log_path: Path) -> dict[str, Any]:
    state_data = load_yaml(state_path)
    log_data = load_yaml(log_path)

    events = extract_events(log_data)

    timeline = []
    for event in events:
        timeline.append(
            {
                "id": event.get("id"),
                "actor": event.get("actor"),
                "reason": event.get("reason"),
                "timestamp": event.get("timestamp"),
                "evidence": event.get("evidence", []),
                "authority": event.get("authority"),
            }
        )

    return {
        "kind": kind,
        "owner": owner,
        "status": extract_status(state_data),
        "event_count": len(timeline),
        "state": stable_path(state_path),
        "transition_log": stable_path(log_path),
        "timeline": timeline,
        "authority": "state_replay_summary_not_source_truth",
    }


def format_replay(result: dict[str, Any]) -> str:
    lines = [
        "STATE_REPLAY",
        f"kind: {result['kind']}",
        f"owner: {result['owner']}",
        f"current_status: {result.get('status')}",
        f"event_count: {result['event_count']}",
        f"state: {result['state']}",
        f"transition_log: {result['transition_log']}",
        f"authority: {result['authority']}",
        "",
        "timeline:",
    ]

    timeline = result.get("timeline") or []
    if not timeline:
        lines.append("  - none")
        return "\n".join(lines)

    for event in timeline:
        lines.extend(
            [
                f"  - id: {event.get('id')}",
                f"    actor: {event.get('actor')}",
                f"    reason: {event.get('reason')}",
                f"    timestamp: {event.get('timestamp')}",
            ]
        )

        evidence = event.get("evidence") or []
        lines.append("    evidence:")
        for item in evidence:
            lines.append(f"      - {item}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    if len(argv) < 2:
        print("usage: python -m UI.state.replay <agent|project> <name> [--json]")
        return 2

    kind = argv[0].strip().lower()
    name = argv[1].strip()
    as_json = "--json" in argv

    try:
        if kind == "agent":
            result = replay_agent(name)
        elif kind == "project":
            result = replay_project(name)
        else:
            print(f"ERR: unknown replay kind: {kind}")
            return 2
    except Exception as exc:
        print(f"ERR: {exc}")
        return 1

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_replay(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
