from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Kind = Literal["observe", "compress", "reconcile", "refine"]

@dataclass(frozen=True)
class BitePolicy:
    investigation_budget: int = 3
    refinement_budget: int = 3
    minimum_information_gain: int = 1

@dataclass(frozen=True)
class ValidationFeedback:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class BiteArtifact:
    number: int
    kind: Kind
    prompt: str
    response: str
    observed: tuple[str, ...] = ()
    inferred: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    next_target: str = ""
    proposal: str = ""
    information_gain: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class BiteResult:
    status: Literal["ready", "escalated"]
    artifacts: tuple[BiteArtifact, ...]
    final_output: str
    reason: str = ""
