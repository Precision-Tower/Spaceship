from __future__ import annotations

from Agency.Core.runtime.commands import mission_command
import argparse
from typing import Any


def _real_operator_notes(raw_notes: str) -> str:
    ignored = {
        "",
        "# Operator Notes",
        "No operator review has been recorded.",
    }
    lines = [
        line.strip()
        for line in str(raw_notes or "").splitlines()
        if line.strip() and line.strip() not in ignored
    ]
    return "\n".join(lines).strip()


def _validate_review_request(
    args: argparse.Namespace,
    operator_notes: str = "",
) -> tuple[str | None, str, str | None]:
    requested = [
        ("approved", bool(getattr(args, "approve", False))),
        ("rejected", bool(getattr(args, "reject", False))),
        ("changes_requested", bool(getattr(args, "request_changes", False))),
    ]
    decisions = [decision for decision, enabled in requested if enabled]

    if len(decisions) != 1:
        return (
            None,
            "",
            "Exactly one of --approve, --reject, or --request-changes is required.",
        )

    cli_note = str(getattr(args, "note", "") or "").strip()
    note = cli_note or _real_operator_notes(operator_notes)
    decision = decisions[0]

    if decision == "changes_requested" and not note:
        return (
            None,
            "",
            "--request-changes requires --note or existing operator notes.",
        )

    return decision, note, None


def _review_next_action(
    mission_id: str,
    decision: str,
) -> dict[str, Any]:
    if decision == "approved":
        return {
            "command": mission_command("implement", mission_id),
            "authority": "operator_approval",
            "reason": "Proposal approved by operator.",
        }

    if decision == "rejected":
        return {
            "command": "Review proposal or regenerate.",
            "authority": "operator_review",
            "reason": "Proposal rejected by operator.",
        }

    return {
        "command": mission_command("propose", mission_id),
        "authority": "operator_review",
        "reason": "Operator requested proposal revision.",
    }


def _render_review_markdown(decision: dict[str, Any]) -> str:
    notes = str(decision.get("notes") or "").strip() or "none"
    next_action = decision.get("next_action", {})

    lines = [
        "# Mission Review",
        "",
        "## Decision",
        "",
        str(decision.get("decision") or ""),
        "",
        "## Operator Notes",
        "",
        notes,
        "",
        "## Next Action",
        "",
        str(next_action.get("command") or ""),
        "",
        str(next_action.get("reason") or ""),
        "",
        "## Implementation Authorized",
        "",
        str(bool(decision.get("implementation_authorized"))).lower(),
        "",
    ]

    return "\n".join(lines)