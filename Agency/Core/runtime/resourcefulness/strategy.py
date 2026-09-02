from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ResourcefulnessContext:
    mission_id: str
    plan: dict[str, Any]
    artifacts: dict[str, Any]
    evidence: dict[str, Any]
    created_at: str
    schema_version: int
    coverage_categories: list[str]
    proposal_readiness: dict[str, Any]


@dataclass(frozen=True)
class ResourcefulnessResult:
    strategy: str
    status: str
    reason: str
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    confidence: str = "medium"
    next_recommendation: str = "replan"

    def summary(self, artifact_paths: dict[str, str] | None = None) -> dict[str, Any]:
        return {
            "status": self.status,
            "strategy": self.strategy,
            "reason": self.reason,
            "confidence": self.confidence,
            "next_recommendation": self.next_recommendation,
            "artifacts": artifact_paths or {},
        }


class ResourcefulnessStrategy(Protocol):
    def name(self) -> str:
        ...

    def can_execute(self, context: ResourcefulnessContext) -> bool:
        ...

    def execute(self, context: ResourcefulnessContext) -> ResourcefulnessResult:
        ...
