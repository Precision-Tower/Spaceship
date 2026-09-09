from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from Agency.GeminiGo.session import quota_day
from Agency.GeminiGo.assignment import select_assignment, bounded_evidence
from Agency.GeminiGo.dispatch import action_fingerprint, dispatch_read_only_assignment
from Agency.GeminiGo.worker import run_turn
from Agency.GeminiGo.state import append_event, load_state, save_state


DEFAULT_SESSION = "daily"
POLL_SECONDS = 300


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def repository_fingerprint() -> dict[str, str]:
    root = repo_root()

    def run(*args: str) -> str:
        result = subprocess.run(
            args,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        return result.stdout.strip()

    def digest(path: str) -> str:
        target = root / path
        if not target.is_file():
            return "absent"
        return run("git", "hash-object", path)

    # Wake only for authored GeminiGo work authority and implementation
    # changes. Kernel discovery is an operator-authorized GeminiGo lane;
    # unrelated Cipher/UI churn must not consume Gemini quota.
    geminigo_files = sorted(
        str(path.relative_to(root))
        for path in (root / "Agency" / "GeminiGo").rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name != "credentials.json"
    )
    material = "\n".join(
        f"{path}:{digest(path)}" for path in geminigo_files
    )
    import hashlib
    kernel_files = sorted(
        str(path.relative_to(root))
        for path in (root / "qps" / "kernel").rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
    )
    kernel_material = "\n".join(
        f"{path}:{digest(path)}" for path in kernel_files
    )
    return {
        "agency_checklist": digest("Agency/checklist.qps"),
        "agency_index": digest("Agency/_index.qps"),
        "qps_checklist": digest("qps/checklist.qps"),
        "qps_index": digest("qps/_index.qps"),
        "kernel": hashlib.sha256(
            kernel_material.encode()
        ).hexdigest(),
        "geminigo": hashlib.sha256(material.encode()).hexdigest(),
    }


def should_wake(state: dict[str, Any], fingerprint: dict[str, str]) -> bool:
    today = quota_day()
    if state.get("last_wake_quota_day") != today:
        return True
    if state.get("session_status") in {"blocked", "stopped", "working", "provider_wait"}:
        return False
    return state.get("last_fingerprint") != fingerprint


def final_audit_required(
    state: dict[str, Any],
    fingerprint: dict[str, str],
) -> bool:
    return state.get("last_final_audit_fingerprint") != fingerprint


def run_final_audit() -> dict[str, Any]:
    root = repo_root()
    script = root / "Agency" / "audit" / "agency-capability-audit.sh"
    if not script.is_file():
        return {
            "ok": False,
            "status": "audit_unavailable",
            "reason": f"missing audit entrypoint: {script}",
        }
    result = subprocess.run(
        ["bash", str(script)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "status": "clean" if result.returncode == 0 else "findings",
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def mark_sleep(
    session_id: str,
    state: dict[str, Any],
    *,
    fingerprint: dict[str, str],
    reason: str,
) -> dict[str, Any]:
    next_state = {
        **state,
        "session_status": "idle",
        "last_wake_quota_day": quota_day(),
        "last_fingerprint": fingerprint,
        "sleep_reason": reason,
    }
    save_state(session_id, next_state)
    append_event(session_id, "sleep", reason=reason)
    return next_state


def run_cycle(*, session_id: str = DEFAULT_SESSION) -> dict[str, Any]:
    state = load_state(session_id)
    fingerprint = repository_fingerprint()

    if not should_wake(state, fingerprint):
        return {"action": "sleep", "reason": "wake_suppressed"}

    next_state = {
        **state,
        "session_status": "ready",
        "last_wake_quota_day": quota_day(),
        "last_fingerprint": fingerprint,
        "sleep_reason": None,
    }
    save_state(session_id, next_state)
    append_event(session_id, "wake", reason="daily_or_repository_change")

    assignment = select_assignment()
    if assignment is None:
        if final_audit_required(next_state, fingerprint):
            audit = run_final_audit()
            audited_fingerprint = repository_fingerprint()
            audited_state = {
                **next_state,
                "last_final_audit_fingerprint": audited_fingerprint,
                "last_final_audit_status": audit.get("status"),
                "last_final_audit_returncode": audit.get("returncode"),
            }
            save_state(session_id, audited_state)
            append_event(
                session_id,
                "final_audit",
                fingerprint=audited_fingerprint,
                ok=bool(audit.get("ok")),
                status=audit.get("status"),
                returncode=audit.get("returncode"),
            )
            if not audit.get("ok"):
                mark_sleep(
                    session_id,
                    audited_state,
                    fingerprint=audited_fingerprint,
                    reason="final_audit_findings",
                )
                return {
                    "action": "sleep",
                    "reason": "final_audit_findings",
                    "audit": audit,
                }
            mark_sleep(
                session_id,
                audited_state,
                fingerprint=audited_fingerprint,
                reason="final_audit_clean",
            )
            return {
                "action": "sleep",
                "reason": "final_audit_clean",
                "audit": audit,
            }

        mark_sleep(
            session_id, next_state, fingerprint=fingerprint,
            reason="final_audit_already_recorded",
        )
        return {"action": "sleep", "reason": "final_audit_already_recorded"}

    action_fp = action_fingerprint(assignment)
    if next_state.get("last_action_fingerprint") == action_fp:
        repeated = int(next_state.get("repeated_action_count") or 0) + 1
        stalled = {
            **next_state,
            "last_action_fingerprint": action_fp,
            "repeated_action_count": repeated,
            "session_status": "stopped",
            "stop_reason": "STALLED",
        }
        save_state(session_id, stalled)
        append_event(
            session_id, "action_suppressed",
            reason="repeated_action_fingerprint",
            fingerprint=action_fp,
            repeated_action_count=repeated,
        )
        mark_sleep(
            session_id, stalled, fingerprint=fingerprint,
            reason="worker_stalled_repeated_action",
        )
        return {
            "action": "sleep",
            "reason": "repeated_action_fingerprint",
            "assignment": assignment["identity"],
        }

    dispatch = dispatch_read_only_assignment(assignment)
    dispatched_state = {
        **next_state,
        "last_action_fingerprint": action_fp,
        "repeated_action_count": 0,
        "work_packet_id": dispatch.get("packet_id"),
    }
    save_state(session_id, dispatched_state)
    append_event(
        session_id, "core_dispatch",
        assignment=assignment["identity"],
        fingerprint=action_fp,
        ok=bool(dispatch.get("ok")),
        stage=dispatch.get("stage"),
        packet_id=dispatch.get("packet_id"),
        editor_result_status=dispatch.get("editor_result_status"),
    )

    if not dispatch.get("ok"):
        mark_sleep(
            session_id, dispatched_state,
            fingerprint=repository_fingerprint(),
            reason=f"core_dispatch_{dispatch.get('stage') or 'failed'}",
        )
        return {
            "action": "sleep",
            "reason": f"core_dispatch_{dispatch.get('stage') or 'failed'}",
            "assignment": assignment["identity"],
            "dispatch": dispatch,
        }

    evidence = bounded_evidence(assignment) + (
        "\nCORE_WORK_PACKET: " + str(dispatch.get("packet_id")) +
        "\nCORE_EDITOR_RESULT: " + str(dispatch.get("editor_result_status")) +
        "\nCORE_EDITOR_RESULT_PATH: " + str(dispatch.get("editor_result_path")) +
        "\nREPOSITORY_MUTATION_PERFORMED: " +
        str(bool(dispatch.get("repository_mutation_performed"))).lower()
    )
    result = run_turn(
        session_id=session_id,
        purpose=assignment["identity"],
        request=assignment["next"] or assignment["summary"],
        evidence=evidence,
        work_packet_id=dispatch.get("packet_id"),
    )
    reason = result.get("stop_reason")
    if reason in {"CLEAN", "COMPLETE", "BLOCKED", "STALLED", "QUOTA"}:
        mark_sleep(
            session_id, load_state(session_id),
            fingerprint=repository_fingerprint(),
            reason=f"worker_{str(reason).lower()}",
        )
    return {
        "action": "worker_turn",
        "assignment": assignment["identity"],
        "dispatch": dispatch,
        "worker_stop_reason": reason,
    }


def daemon_loop(
    *,
    session_id: str = DEFAULT_SESSION,
    poll_seconds: int = POLL_SECONDS,
) -> None:
    while True:
        run_cycle(session_id=session_id)
        time.sleep(max(1, poll_seconds))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m Agency.GeminiGo.daemon")
    parser.add_argument("--session", default=DEFAULT_SESSION)
    parser.add_argument("--poll-seconds", type=int, default=POLL_SECONDS)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)

    if args.once:
        state = load_state(args.session)
        fingerprint = repository_fingerprint()
        wake = should_wake(state, fingerprint)
        print(json.dumps({
            "session": args.session,
            "wake": wake,
            "quota_day": quota_day(),
            "fingerprint": fingerprint,
        }, indent=2))
        return 0

    daemon_loop(session_id=args.session, poll_seconds=args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
