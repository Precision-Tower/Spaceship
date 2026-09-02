from __future__ import annotations
import json
from collections.abc import Callable
from pathlib import Path
from .contracts import BiteArtifact, BitePolicy, BiteResult, ValidationFeedback
from .prompts import investigation_prompt, refinement_prompt

Invoke = Callable[[str], str]
Validate = Callable[[str], ValidationFeedback]
Ready = Callable[[BiteArtifact], bool]
CandidateExtractor = Callable[[BiteArtifact], str]
RefinementPromptBuilder = Callable[
    [
        str,
        str,
        ValidationFeedback,
        tuple[BiteArtifact, ...],
        int,
    ],
    str,
]

HEADINGS = ("Observed", "Inferred", "Unresolved", "Evidence", "Next target", "Proposal")

def _section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    active = False
    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line.casefold().rstrip(":") == heading.casefold():
            active = True
            continue
        if active and line.rstrip(":") in HEADINGS:
            break
        if active and line:
            out.append(line[1:].strip() if line[:1] in "-*" else line)
    return out

def _artifact(number: int, kind: str, prompt: str, response: str, previous: BiteArtifact | None) -> BiteArtifact:
    observed = tuple(_section(response, "Observed"))
    inferred = tuple(_section(response, "Inferred"))
    unresolved = tuple(_section(response, "Unresolved"))
    evidence = tuple(_section(response, "Evidence"))
    next_target = " ".join(_section(response, "Next target"))
    proposal = "\n".join(_section(response, "Proposal")).strip()
    current = set(observed + unresolved + evidence)
    prior = set() if previous is None else set(previous.observed + previous.unresolved + previous.evidence)
    resolved = set() if previous is None else set(previous.unresolved) - set(unresolved)
    return BiteArtifact(
        number=number,
        kind=kind,  # type: ignore[arg-type]
        prompt=prompt,
        response=response,
        observed=observed,
        inferred=inferred,
        unresolved=unresolved,
        evidence=evidence,
        next_target=next_target,
        proposal=proposal,
        information_gain=len(current - prior) + len(resolved),
    )

# BEGIN patch_009b_candidate_extractor
def _proposal_candidate(artifact: BiteArtifact) -> str:
    return artifact.proposal
# END patch_009b_candidate_extractor

def _persist(root: Path | None, artifact: BiteArtifact) -> None:
    if root is None:
        return
    path = root / f"bite_{artifact.number:03d}" / "artifact.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def run_investigation(
    *,
    objective: str,
    repository_context: str,
    invoke: Invoke,
    ready: Ready,
    constraints: tuple[str, ...] = (),
    policy: BitePolicy = BitePolicy(),
    output_root: Path | None = None,
) -> BiteResult:
    artifacts: list[BiteArtifact] = []
    for number in range(1, policy.investigation_budget + 1):
        prompt = investigation_prompt(objective, repository_context, tuple(artifacts), number, constraints)
        response = invoke(prompt)
        kind = "observe" if number == 1 else "compress" if number == 2 else "reconcile"
        artifact = _artifact(number, kind, prompt, response, artifacts[-1] if artifacts else None)
        artifacts.append(artifact)
        _persist(output_root, artifact)
        if ready(artifact):
            return BiteResult("ready", tuple(artifacts), artifact.proposal or response)
        if number > 1 and artifact.information_gain < policy.minimum_information_gain:
            return BiteResult("escalated", tuple(artifacts), artifact.proposal or response, "no_information_gain")
    final = artifacts[-1]
    return BiteResult("escalated", tuple(artifacts), final.proposal or final.response, "investigation_budget_exhausted")

def run_refinement(
    *,
    objective: str,
    candidate: str,
    invoke: Invoke,
    validate: Validate,
    candidate_extractor: CandidateExtractor = _proposal_candidate,
    prompt_builder: RefinementPromptBuilder = refinement_prompt,
    policy: BitePolicy = BitePolicy(),
    output_root: Path | None = None,
) -> BiteResult:
    artifacts: list[BiteArtifact] = []
    feedback = validate(candidate)
    if feedback.valid:
        return BiteResult("ready", (), candidate)
    previous_errors: tuple[str, ...] | None = None
    for number in range(1, policy.refinement_budget + 1):
        prompt = prompt_builder(
            objective,
            candidate,
            feedback,
            tuple(artifacts),
            number,
        )
        response = invoke(prompt)
        artifact = _artifact(number, "refine", prompt, response, artifacts[-1] if artifacts else None)
        artifacts.append(artifact)
        _persist(output_root, artifact)
        extracted_candidate = candidate_extractor(artifact)
        if extracted_candidate:
            candidate = extracted_candidate
        repeated = previous_errors == feedback.errors
        previous_errors = feedback.errors
        feedback = validate(candidate)
        if feedback.valid:
            return BiteResult("ready", tuple(artifacts), candidate)
        if repeated:
            return BiteResult("escalated", tuple(artifacts), candidate, "repeated_same_failure")
    return BiteResult("escalated", tuple(artifacts), candidate, "refinement_budget_exhausted")
