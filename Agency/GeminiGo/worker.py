from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from Agency.GeminiGo.bootstrap import (
    BOOTSTRAP_CONTRACT,
    build_continuation_context,
    build_initial_context,
)
from Agency.GeminiGo.credentials import api_key, public_status
from Agency.GeminiGo.provider import available_models, model_name
from Agency.GeminiGo.supervisor import execute_with_failover
from Agency.GeminiGo.session import clear_interaction, needs_rotation, quota_day
from Agency.GeminiGo.state import append_event, load_state, recent_events, save_state


def _read_evidence(path: str | None) -> str:
    if not path:
        return ""
    source = Path(path).expanduser()
    if not source.is_file():
        raise ValueError(f"evidence_file_not_found:{path}")
    return source.read_text(encoding="utf-8", errors="replace")


def _stop_reason(text: str) -> str | None:
    for reason in ("CLEAN", "COMPLETE", "BLOCKED", "STALLED", "QUOTA"):
        if f"GEMINIGO_STOP({reason})" in text:
            return reason
    return None


def run_turn(
    *,
    session_id: str,
    purpose: str,
    request: str,
    evidence: str = "",
    mission_id: str | None = None,
    work_packet_id: str | None = None,
) -> dict[str, Any]:
    state = load_state(session_id)
    if needs_rotation(state):
        state = clear_interaction(state, reason="quota_day_changed")

    previous = state.get("interaction_id")
    if previous:
        context = build_continuation_context(request=request, evidence=evidence)
    else:
        context = build_initial_context(
            request=request,
            evidence=evidence,
            checkpoint=str(state.get("last_response") or ""),
            mission_id=mission_id or state.get("mission_id"),
            work_packet_id=work_packet_id or state.get("work_packet_id"),
        )

    turn = int(state.get("turn", 0)) + 1
    append_event(session_id, "turn_requested", turn=turn, purpose=purpose)

    result = execute_with_failover(
        purpose=purpose,
        context=context,
        previous_interaction_id=previous,
        system_instruction=BOOTSTRAP_CONTRACT,
        session_id=session_id,
    )
    response_text = str(result.get("response_text") or result.get("reason") or result.get("error_detail") or "")
    stop_reason = _stop_reason(response_text)
    interaction_id = result.get("interaction_id") or previous

    next_state = {
        **state,
        "turn": turn,
        "mission_id": mission_id or state.get("mission_id"),
        "work_packet_id": work_packet_id or state.get("work_packet_id"),
        "last_purpose": purpose,
        "last_response": response_text[-12000:],
        "interaction_id": interaction_id,
        "quota_day": quota_day() if interaction_id else None,
        "session_status": "stopped" if stop_reason else ("working" if result.get("ok") else "provider_wait"),
        "stop_reason": stop_reason,
    }
    save_state(session_id, next_state)
    append_event(
        session_id, "turn_completed", turn=turn, ok=bool(result.get("ok")),
        status=result.get("status"), model=result.get("model"),
        interaction_id=interaction_id, stop_reason=stop_reason,
    )
    return {
        **result,
        "session_id": session_id,
        "turn": turn,
        "stop_reason": stop_reason,
        "continuity_persisted": True,
        "repository_mutation_performed": False,
        "acceptance_established": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m Agency.GeminiGo.worker")
    sub = parser.add_subparsers(dest="command", required=True)
    turn = sub.add_parser("turn")
    turn.add_argument("--session", required=True)
    turn.add_argument("--purpose", required=True)
    turn.add_argument("--request", required=True)
    turn.add_argument("--evidence-file")
    turn.add_argument("--mission")
    turn.add_argument("--work-packet")
    status = sub.add_parser("status")
    status.add_argument("--session", required=True)
    sub.add_parser("models")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "models":
        print(json.dumps({
            "model": model_name(),
            "available_models": available_models(api_key=api_key("primary")),
            "credentials": public_status(),
        }, indent=2))
        return 0
    if args.command == "status":
        print(json.dumps({"state": load_state(args.session), "recent_events": recent_events(args.session)}, indent=2))
        return 0
    result = run_turn(
        session_id=args.session, purpose=args.purpose, request=args.request,
        evidence=_read_evidence(args.evidence_file),
        mission_id=args.mission, work_packet_id=args.work_packet,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
