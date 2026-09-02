from __future__ import annotations

import json
import uuid
from typing import Any

from Agency.Core.work.tasks.editor.contracts import now_utc
from Agency.Core.work.work_packets import execution, persistence
from Agency.Core.work.work_packets.contracts import (
    WorkPacket,
    WorkPacketStep,
)
from Agency.Core.work.work_packets.proposal_contracts import (
    ProposalIntentKind,
    ProposalRequest,
    ReplaceText,
    proposal_capability,
    validate_proposal_request,
)


def supports(intent_kind: ProposalIntentKind) -> bool:
    return bool(proposal_capability(intent_kind)["enabled"])


def _error_payload(
    *,
    code: str,
    request: ProposalRequest,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "rejected",
        "code": code,
        "intent": request.intent.kind.value,
        "errors": errors,
        "repository_mutation_performed": False,
        "acceptance_established": False,
    }


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _change_intent(intent: ReplaceText) -> str:
    return (
        f"replace {_quoted(intent.old)} with {_quoted(intent.new)} "
        f"in {intent.path}"
    )


def _proposal_packet(
    *,
    play_owner: str,
    request: ProposalRequest,
) -> WorkPacket:
    if not isinstance(request.intent, ReplaceText):
        raise ValueError(
            f"unsupported_proposal_intent:{request.intent.kind.value}"
        )

    timestamp = now_utc()
    packet_id = f"wp-proposal-{uuid.uuid4().hex[:12]}"
    step_id = "propose-change"

    scope = request.scope.to_dict()
    constraints = {
        "mutation_authorized": False,
        **dict(request.constraints),
    }

    step = WorkPacketStep(
        step_id=step_id,
        sequence=1,
        title="Produce bounded patch proposal",
        objective=(
            "Produce a non-applied patch proposal for the requested "
            "repository change."
        ),
        operation="propose_patch",
        status="pending",
        depends_on=[],
        evidence_requirements=[
            "supporting_evidence",
            "proposed_patch",
            "source_unchanged_proof",
        ],
        scope=scope,
        request={
            "repository_context": {
                "operations": ["text_search"],
                "text": request.intent.old[:120],
            },
            "change_intent": _change_intent(request.intent),
            "proposal_intent": request.intent.to_dict(),
        },
        constraints={
            "read_only": True,
            "mutation_authorized": False,
        },
    )

    return WorkPacket(
        packet_id=packet_id,
        schema_version=1,
        title="Canonical proposal request",
        objective="Construct and dispatch an immutable Editor proposal.",
        created_by=play_owner,
        play_owner=play_owner,
        ball_holder=play_owner,
        next_decision_owner=play_owner,
        status="draft",
        scope=scope,
        constraints=constraints,
        acceptance_criteria=list(request.acceptance_criteria),
        steps=[step],
        unresolveds=[],
        contradictions=[],
        created_at=timestamp,
        updated_at=timestamp,
    )


def create_proposal(
    *,
    play_owner: str,
    request: ProposalRequest,
) -> dict[str, Any]:
    owner = str(play_owner or "").strip()
    if not owner:
        return _error_payload(
            code="invalid_proposal_request",
            request=request,
            errors=["play_owner_required"],
        )

    errors = validate_proposal_request(request)
    if errors:
        return _error_payload(
            code="invalid_proposal_request",
            request=request,
            errors=errors,
        )

    if not supports(request.intent.kind):
        return _error_payload(
            code="unsupported_proposal_intent",
            request=request,
            errors=[
                f"unsupported_proposal_intent:{request.intent.kind.value}"
            ],
        )

    packet = _proposal_packet(
        play_owner=owner,
        request=request,
    )

    created = execution.create_packet(packet)
    if not created.get("ok"):
        return created

    selected = execution.select_step(
        packet.packet_id,
        "propose-change",
        owner,
    )
    if not selected.get("ok"):
        return selected

    dispatched = execution.dispatch_step(
        packet.packet_id,
        "propose-change",
        owner,
    )
    dispatched["proposal_request"] = request.to_dict()
    dispatched["proposal_intent"] = request.intent.kind.value
    dispatched["persistence_path"] = persistence.stable_packet_path(
        packet.packet_id
    )
    return dispatched
