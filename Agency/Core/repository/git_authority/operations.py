from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from Agency.Core.repository.git_authority.authority import get_status
from Agency.Core.repository.git_authority.commands import repository_ref
from Agency.Core.foundation.paths import WORK_PACKETS_ROOT, DASHBOARD_ROOT


def _latest_work_packet() -> dict[str, Any] | None:
    root = WORK_PACKETS_ROOT
    if not root.exists():
        return None
    packet_files = sorted(root.glob("*/packet.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in packet_files:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


def operations_status() -> dict[str, Any]:
    repository = repository_ref(DASHBOARD_ROOT)
    git_status = get_status(repository)
    packet = _latest_work_packet()
    selected_step = None
    current_route = None
    if packet:
        for step in packet.get("steps", []):
            if step.get("status") in {"selected", "dispatched"}:
                selected_step = {
                    "step_id": step.get("step_id"),
                    "status": step.get("status"),
                    "operation": step.get("operation"),
                }
                current_route = step.get("operation")
                break
    return {
        "ok": True,
        "projection": "operations_status",
        "persistence": "not_persisted_live_projection",
        "ce_os_state_source": "WorkPacket persisted authority state",
        "git_state_source": "live_git_query",
        "authority": {
            "play_owner": packet.get("play_owner") if packet else None,
            "ball_holder": packet.get("ball_holder") if packet else None,
            "next_decision_owner": packet.get("next_decision_owner") if packet else None,
            "active_work_packet": packet.get("packet_id") if packet else None,
            "selected_step": selected_step,
            "current_route": current_route,
            "unresolveds": packet.get("unresolveds", []) if packet else [],
        },
        "git": git_status.to_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python run.py operations")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status")
    args = parser.parse_args(argv or [])
    if args.command != "status":
        parser.print_help()
        return 2
    print(json.dumps(operations_status(), indent=2, sort_keys=True))
    return 0
