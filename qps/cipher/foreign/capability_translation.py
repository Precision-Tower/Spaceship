from __future__ import annotations

from dataclasses import dataclass
import ast
from pathlib import Path
import tempfile

from .capability_graph import CapabilityIdentity
from .capability_discovery import ResolvedCapability


@dataclass(frozen=True)
class TranslatedCapability:
    identity: CapabilityIdentity
    source: Path
    candidate: str
    evidence: str


def _exact_source_segment(
    resolved: ResolvedCapability,
) -> str:
    capability = resolved.capability_source
    text = capability.source.read_text(encoding="utf-8")
    tree = ast.parse(text)

    if capability.definition_kind not in {
        "Assign",
        "AnnAssign",
    }:
        raise ValueError(
            "exact capability translation unsupported for "
            f"{capability.definition_kind}"
        )

    wanted = capability.definition_name
    for node in tree.body:
        names: set[str] = set()
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        else:
            continue

        if wanted not in names:
            continue

        segment = ast.get_source_segment(text, node)
        if not segment:
            raise ValueError(
                f"source segment unavailable for {capability.identity.canonical}"
            )
        return segment.rstrip() + "\n"

    raise ValueError(
        f"definition not found for {capability.identity.canonical}"
    )


def translate_python_capability(
    resolved: ResolvedCapability,
    *,
    workspace_root: Path,
) -> TranslatedCapability:
    from qps.cipher.plan import _inspect_unit

    segment = _exact_source_segment(resolved)

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source = root / (
            resolved.capability_source.definition_name + ".py"
        )
        destination = root / "candidate.qps"
        source.write_text(segment, encoding="utf-8")

        unit = _inspect_unit(
            source,
            destination,
            workspace_root=workspace_root,
        )

    if unit.status != "ready" or unit.candidate is None:
        raise ValueError(
            "exact capability translation failed: "
            + (unit.detail or unit.status)
        )

    # The extraction file is translation machinery, not authored provenance.
    # Replace only its exact emitted source-path metadata with the real source
    # path, then validate the exact durable candidate bytes again.
    transient_path = str(source)
    durable_path = str(resolved.capability_source.source)
    if transient_path not in unit.candidate:
        raise ValueError(
            "translated capability candidate lacks transient provenance"
        )
    candidate = unit.candidate.replace(
        transient_path,
        durable_path,
        1,
    )

    from qps.cipher.plan import _validate_candidate_qps

    # Canonical validator is exception-on-failure and returns None on pass.
    _validate_candidate_qps(candidate)

    return TranslatedCapability(
        identity=resolved.identity,
        source=resolved.capability_source.source,
        candidate=candidate,
        evidence=(
            "exact capability translated, durable provenance restored, "
            "and exact candidate qps validated"
        ),
    )
