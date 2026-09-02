from __future__ import annotations

from typing import Any

from Agency.Core.knowledge.reasoning.contracts import EvidenceReference


def first_evidence_ref(evidence: dict[str, Any]) -> EvidenceReference | None:
    for item in evidence.get("observations", []):
        observation_id = str(item.get("id") or "")
        path = item.get("path")

        if observation_id and path:
            return EvidenceReference(
                observation_id=observation_id,
                path=str(path),
                inspection_pass=item.get("pass"),
            )

    return None


def normalize_evidence_refs(
    raw_refs: Any,
    evidence: dict[str, Any],
) -> tuple[EvidenceReference, ...]:
    observations = evidence.get("observations_by_id", {})
    refs: list[EvidenceReference] = []

    if not isinstance(raw_refs, list):
        return ()

    for raw_ref in raw_refs:
        if isinstance(raw_ref, str):
            observation_id = raw_ref
        elif isinstance(raw_ref, dict):
            observation_id = str(
                raw_ref.get("observation_id")
                or raw_ref.get("id")
                or ""
            )
        else:
            continue

        source = observations.get(observation_id)
        if not source:
            continue

        refs.append(
            EvidenceReference(
                observation_id=observation_id,
                path=source.get("path"),
                inspection_pass=source.get("pass"),
            )
        )

    return tuple(refs)
