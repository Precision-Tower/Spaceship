from __future__ import annotations

import json
import sys
from pathlib import Path

from Agency.Core.state.event_log import append_agent_event, append_project_event
from Agency.Core.state.engine import normalize_name, normalize_project_id

from Agency.Core.foundation.paths import AGENTS_ROOT, PROJECTS_ROOT


def agent_state_path(agent_name: str) -> Path:
    agent_name = normalize_name(agent_name)
    return AGENTS_ROOT / agent_name / "state" / "agent_state.yaml"


def project_state_path(project_id: str) -> Path:
    project_id = normalize_project_id(project_id)
    return PROJECTS_ROOT / project_id / "state" / "project_state.yaml"


def replace_status(path: Path, new_status: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"state_file_not_found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    old_status = read_status(text)

    if old_status == new_status:
        return old_status

    lines = []
    replaced = False

    for line in text.splitlines():
        if line.strip().startswith("status:") and not replaced:
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}status: {new_status}")
            replaced = True
        else:
            lines.append(line)

    if not replaced:
        raise ValueError("status_field_not_found")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return old_status


def read_status(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("status:"):
            return stripped.split(":", 1)[1].strip()
    return "unknown"


def transition_agent_status(agent_name: str, new_status: str, reason: str) -> dict:
    agent_name = normalize_name(agent_name)
    path = agent_state_path(agent_name)

    before_status = replace_status(path, new_status)

    event = append_agent_event(
        agent_name=agent_name,
        reason=f"status changed from {before_status} to {new_status}: {reason}",
        actor="state_transition_engine",
        evidence=[str(path)],
    )

    return {
        "ok": True,
        "kind": "agent",
        "owner": agent_name,
        "from_status": before_status,
        "to_status": new_status,
        "state": str(path),
        "event": event,
        "authority": "state_transition_record_not_truth",
    }


def transition_project_status(project_id: str, new_status: str, reason: str) -> dict:
    project_id = normalize_project_id(project_id)
    path = project_state_path(project_id)

    before_status = replace_status(path, new_status)

    event = append_project_event(
        project_id=project_id,
        reason=f"status changed from {before_status} to {new_status}: {reason}",
        actor="state_transition_engine",
        evidence=[str(path)],
    )

    return {
        "ok": True,
        "kind": "project",
        "owner": project_id,
        "from_status": before_status,
        "to_status": new_status,
        "state": str(path),
        "event": event,
        "authority": "state_transition_record_not_truth",
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if len(argv) < 4:
        print('usage: python -m UI.state.transitions <agent|project> <name> <new_status> "<reason>"')
        return 2

    kind = argv[0].strip().lower()
    name = argv[1].strip()
    new_status = argv[2].strip()
    reason = " ".join(argv[3:]).strip()

    try:
        if kind == "agent":
            result = transition_agent_status(name, new_status, reason)
        elif kind == "project":
            result = transition_project_status(name, new_status, reason)
        else:
            print(f"ERR: unknown transition kind: {kind}")
            return 2
    except Exception as exc:
        print(f"ERR: {exc}")
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
