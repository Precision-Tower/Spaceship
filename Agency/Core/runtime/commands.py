from __future__ import annotations

DEFAULT_AGENT = "Editor"


def agent_command(*parts: str) -> str:
    command = [
        "python",
        "run.py",
        "agent",
        DEFAULT_AGENT,
    ]
    command.extend(str(part) for part in parts if str(part))
    return " ".join(command)


def mission_command(
    action: str,
    mission_id: str,
    *extra: str,
) -> str:
    return agent_command(
        "mission",
        action,
        "--mission",
        mission_id,
        *extra,
    )
