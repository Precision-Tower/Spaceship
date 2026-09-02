from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class EvidenceReference:
    observation_id: str
    path: str | None = None
    inspection_pass: str | int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["pass"] = payload.pop("inspection_pass")
        return payload


@dataclass(frozen=True)
class CausalFinding:
    finding_id: str
    claim: str
    evidence: tuple[EvidenceReference, ...]
    confidence: Confidence = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.finding_id,
            "claim": self.claim,
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ReasoningAssumption:
    assumption_id: str
    statement: str
    reason: str
    risk_if_false: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.assumption_id,
            "statement": self.statement,
            "reason": self.reason,
            "risk_if_false": self.risk_if_false,
        }


@dataclass(frozen=True)
class UnresolvedQuestion:
    unresolved_id: str
    question: str
    blocking: bool = True
    recommended_action: str = "additional_inspection"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.unresolved_id,
            "question": self.question,
            "blocking": self.blocking,
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True)
class SystemModel:
    components: tuple[str, ...] = ()
    control_flow: tuple[str, ...] = ()
    state_ownership: tuple[str, ...] = ()
    integration_points: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "components": list(self.components),
            "control_flow": list(self.control_flow),
            "state_ownership": list(self.state_ownership),
            "integration_points": list(self.integration_points),
        }


@dataclass(frozen=True)
class ReasoningPolicy:
    max_prompt_chars: int = 2800
    require_evidence_for_findings: bool = True
    preserve_unresolveds: bool = True
    repository_access_allowed: bool = False
    mutation_allowed: bool = False
    maximum_findings: int = 8
    maximum_assumptions: int = 8
    maximum_unresolved_questions: int = 10


@dataclass(frozen=True)
class ReasoningResult:
    objective: str
    current_system_model: SystemModel
    causal_findings: tuple[CausalFinding, ...] = ()
    assumptions: tuple[ReasoningAssumption, ...] = ()
    unresolved_questions: tuple[UnresolvedQuestion, ...] = ()
    recommended_next_actions: tuple[str, ...] = ()
    authority: str = "reasoning_only"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "current_system_model": self.current_system_model.to_dict(),
            "causal_findings": [
                finding.to_dict() for finding in self.causal_findings
            ],
            "assumptions": [
                assumption.to_dict() for assumption in self.assumptions
            ],
            "unresolved_questions": [
                unresolved.to_dict()
                for unresolved in self.unresolved_questions
            ],
            "recommended_next_actions": list(
                self.recommended_next_actions
            ),
            "authority": self.authority,
            "metadata": dict(self.metadata),
        }
