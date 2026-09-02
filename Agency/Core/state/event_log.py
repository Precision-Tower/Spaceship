from __future__ import annotations

import json, yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from Agency.Core.foundation.paths import AGENTS_ROOT, PROJECTS_ROOT, stable_path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def agent_log_path(agent_name: str) -> Path:
    agent_name = normalize_agent_name(agent_name)
    return AGENTS_ROOT / agent_name / "state" / "transition_log.yaml"


def project_log_path(project_id: str) -> Path:
    project_id = normalize_project_id(project_id)
    return PROJECTS_ROOT / project_id / "state" / "transition_log.yaml"


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def next_event_id(log_text: str, prefix: str = "event") -> str:
    count = log_text.count("  - id:")
    return f"{prefix}_{count + 1:04d}"


def append_agent_event(
    agent_name: str,
    reason: str,
    actor: str = "operator",
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    agent_name = normalize_agent_name(agent_name)
    path = agent_log_path(agent_name)
    return append_event(
        path=path,
        owner=agent_name,
        kind="agent",
        actor=actor,
        reason=reason,
        evidence=evidence or [],
    )


def append_project_event(
    project_id: str,
    reason: str,
    actor: str = "operator",
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    project_id = normalize_project_id(project_id)
    path = project_log_path(project_id)
    return append_event(
        path=path,
        owner=project_id,
        kind="project",
        actor=actor,
        reason=reason,
        evidence=evidence or [],
    )


def append_event(
    path: Path,
    owner: str,
    kind: str,
    actor: str,
    reason: str,
    evidence: list[str],
) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("event_reason_empty")

    if not path.exists():
        raise FileNotFoundError(f"transition_log_not_found: {stable_path(path)}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    log = data.setdefault("TransitionLog", {})
    log.setdefault("owner", owner)
    log.setdefault("kind", kind)
    log.setdefault("authority", "transition_history_not_truth")

    events = log.get("events")
    if not isinstance(events, list):
        events = []
        log["events"] = events

    event_id = f"event_{len(events) + 1:04d}"

    events.append({
        "id": event_id,
        "owner": owner,
        "kind": kind,
        "actor": actor,
        "reason": reason.strip(),
        "timestamp": utc_now(),
        "before_state_hash": None,
        "after_state_hash": None,
        "evidence": evidence or ["none"],
        "authority": "transition_history_not_truth",
    })

    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "kind": kind,
        "owner": owner,
        "event_id": event_id,
        "transition_log": stable_path(path),
        "authority": "transition_history_not_truth",
    }


def append_event_text(current: str, event_text: str) -> str:
    text = current.rstrip()

    if "events: []" in text:
        text = text.replace("events: []", "events:")

    if not text:
        text = "TransitionLog:\n  authority: transition_history_not_truth\n  events:"

    return text + "\n" + event_text.rstrip() + "\n"

def render_event(
    event_id: str,
    owner: str,
    kind: str,
    actor: str,
    reason: str,
    evidence: list[str],
) -> str:
    lines = [
        f"  - id: {yaml_scalar(event_id)}",
        f"    owner: {yaml_scalar(owner)}",
        f"    kind: {yaml_scalar(kind)}",
        f"    actor: {yaml_scalar(actor)}",
        f"    reason: {yaml_scalar(reason)}",
        f"    timestamp: {yaml_scalar(utc_now())}",
        "    before_state_hash: null",
        "    after_state_hash: null",
        "    evidence:",
    ]

    if evidence:
        for item in evidence:
            lines.append(f"      - {yaml_scalar(item)}")
    else:
        lines.append("      - none")

    lines.append("    authority: transition_history_not_truth")

    return "\n".join(lines)

def yaml_scalar(value: Any) -> str:
    text = str(value)

    if not text:
        return '""'

    unsafe = any(ch in text for ch in [":", "#", "{", "}", "[", "]", ",", '"', "'"])
    multiline = "\n" in text

    if multiline:
        return json.dumps(text)

    if unsafe or text.strip() != text:
        return json.dumps(text)

    return text


def read_agent_events(agent_name: str) -> dict[str, Any]:
    agent_name = normalize_agent_name(agent_name)
    path = agent_log_path(agent_name)
    return read_log(path, owner=agent_name, kind="agent")


def read_project_events(project_id: str) -> dict[str, Any]:
    project_id = normalize_project_id(project_id)
    path = project_log_path(project_id)
    return read_log(path, owner=project_id, kind="project")


def read_log(path: Path, owner: str, kind: str) -> dict[str, Any]:
    exists = path.exists()
    text = read_text_if_exists(path)
    event_count = text.count("  - id:")

    return {
        "kind": kind,
        "owner": owner,
        "exists": exists,
        "event_count": event_count,
        "transition_log": stable_path(path),
        "authority": "transition_history_not_truth",
        "text": text,
    }


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)

    if len(argv) < 2:
        print(
            "usage: python -m UI.state.event_log "
            "<record-agent|record-project|log-agent|log-project> <name> [reason]"
        )
        return 2

    command = argv[0].strip().lower()
    target = argv[1].strip()
    reason = " ".join(argv[2:]).strip()

    try:
        if command == "record-agent":
            result = append_agent_event(target, reason)
        elif command == "record-project":
            result = append_project_event(target, reason)
        elif command == "log-agent":
            result = read_agent_events(target)
        elif command == "log-project":
            result = read_project_events(target)
        else:
            print(f"ERR: unknown event log command: {command}")
            return 2
    except Exception as exc:
        print(f"ERR: {exc}")
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
