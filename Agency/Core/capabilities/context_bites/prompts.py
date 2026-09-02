from __future__ import annotations
from .contracts import BiteArtifact, ValidationFeedback

FORMAT = """Return exactly:
Observed:
- facts
Inferred:
- cautious conclusions
Unresolved:
- blockers
Evidence:
- exact file/symbol/line pointers
Next target:
one highest-value target
Proposal:
smallest justified output"""

def digest(items: tuple[BiteArtifact, ...]) -> str:
    if not items:
        return "none"
    return "\n\n".join(
        f"BITE {x.number} [{x.kind}]\n"
        f"Observed: {' | '.join(x.observed) or 'none'}\n"
        f"Unresolved: {' | '.join(x.unresolved) or 'none'}\n"
        f"Evidence: {' | '.join(x.evidence) or 'none'}\n"
        f"Proposal: {x.proposal or 'none'}"
        for x in items
    )

def investigation_prompt(
    objective: str,
    repository_context: str,
    prior: tuple[BiteArtifact, ...],
    number: int,
    constraints: tuple[str, ...] = (),
) -> str:
    purpose = {
        1: "Map the active causal surface.",
        2: "Trace the highest-value unresolved dependency boundary.",
        3: "Reconcile compressed evidence into a causal change model.",
    }.get(number, "Reduce the highest-value remaining uncertainty.")
    return f"""CONTEXT BITE {number}
OBJECTIVE
{objective}

PURPOSE
{purpose}

CONSTRAINTS
{chr(10).join(f"- {x}" for x in constraints) or "- none"}

PRIOR COMPRESSED ARTIFACTS
{digest(prior)}

CURRENT REPOSITORY CONTEXT
{repository_context}

RULES
- Do not repeat settled territory.
- Preserve unresolveds and contradictions.
- Mark facts as observed and conclusions as inferred.
- Retain evidence pointers.
- Do not mutate files or apply patches.

{FORMAT}"""

def refinement_prompt(
    objective: str,
    candidate: str,
    feedback: ValidationFeedback,
    prior: tuple[BiteArtifact, ...],
    number: int,
) -> str:
    errors = "\n".join(f"- {x}" for x in feedback.errors) or "- none"
    warnings = "\n".join(f"- {x}" for x in feedback.warnings) or "- none"
    return f"""REFINEMENT BITE {number}
OBJECTIVE
{objective}

CURRENT CANDIDATE
{candidate}

VALIDATOR ERRORS
{errors}

VALIDATOR WARNINGS
{warnings}

PRIOR REFINEMENTS
{digest(prior)}

RULES
- Correct only named validator failures.
- Preserve work that already passed.
- Do not broaden scope.
- If blocked, preserve the blocker instead of guessing.

{FORMAT}"""
