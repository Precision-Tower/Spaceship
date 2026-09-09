from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Iterable

from .capability_catalog import (
    CapabilityProof,
    CapabilityProofCatalog,
    StoredCapabilityIdentity,
    make_proof_key,
)
from .capability_graph import (
    CapabilityGraph,
    CapabilityIdentity,
    PythonCapabilitySource,
    build_capability_graph,
    resolve_python_capability_source,
)
from .python_source_resolver import (
    PythonForeignSource,
    resolve_python_foreign_source,
)
from qps.cipher.ir.nodes import DependencyRef


@dataclass(frozen=True)
class ResolvedCapability:
    identity: CapabilityIdentity
    foreign_source: PythonForeignSource
    capability_source: PythonCapabilitySource


@dataclass(frozen=True)
class CapabilityBoundary:
    identity: CapabilityIdentity
    kind: str
    provenance: str
    source_kind: str
    detail: str


@dataclass
class CapabilityDiscovery:
    graph: CapabilityGraph
    resolved: dict[CapabilityIdentity, ResolvedCapability]
    catalog_hits: set[CapabilityIdentity]
    blockers: dict[CapabilityIdentity, str]
    boundaries: dict[CapabilityIdentity, CapabilityBoundary]


def _distribution_version(name: str | None) -> str | None:
    if not name:
        return None
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def discover_python_capability_graph(
    roots: Iterable[CapabilityIdentity],
    *,
    catalog: CapabilityProofCatalog | None = None,
    semantic_paths: Iterable[Path] = (),
) -> CapabilityDiscovery:
    semantic_paths = tuple(Path(path) for path in semantic_paths)
    resolved: dict[CapabilityIdentity, ResolvedCapability] = {}
    catalog_hits: set[CapabilityIdentity] = set()
    blockers: dict[CapabilityIdentity, str] = {}
    boundaries: dict[CapabilityIdentity, CapabilityBoundary] = {}

    def boundary(
        identity: CapabilityIdentity,
        foreign: PythonForeignSource,
        detail: str,
    ) -> None:
        # Importlib provenance is discovery evidence, never native ABI proof.
        # Built-ins/extensions/frozen implementations cross an irreducible
        # host boundary and remain unproven until the native resolver supplies
        # exact library/symbol evidence.
        if foreign.source_kind in {
            "built-in",
            "native-extension",
            "frozen",
        }:
            kind = "native-proof-required"
        elif foreign.state in {"missing", "unresolved"}:
            kind = "unresolved"
        else:
            kind = "source-unresolved"
        boundaries[identity] = CapabilityBoundary(
            identity=identity,
            kind=kind,
            provenance=foreign.provenance,
            source_kind=foreign.source_kind,
            detail=detail,
        )
        blockers[identity] = detail

    def resolve(identity: CapabilityIdentity) -> ResolvedCapability | None:
        existing = resolved.get(identity)
        if existing is not None:
            return existing

        dependency = DependencyRef(
            package=identity.module.split(".", 1)[0],
            module=identity.module,
            symbol=(
                ".".join(identity.members)
                if identity.members
                else None
            ),
            semantic_identity=identity.canonical,
        )
        foreign = resolve_python_foreign_source(dependency)
        if foreign.origin is None or foreign.source_kind != "python":
            detail = (
                f"{identity.canonical}: no exact Python source "
                f"({foreign.provenance}/{foreign.source_kind})"
            )
            boundary(identity, foreign, detail)
            return None

        capability = resolve_python_capability_source(
            identity,
            foreign.origin,
        )
        if capability is None:
            detail = (
                f"{identity.canonical}: exact Python capability "
                "source could not be resolved"
            )
            boundary(identity, foreign, detail)
            return None

        item = ResolvedCapability(identity, foreign, capability)
        resolved[identity] = item
        return item

    def proof_key(item: ResolvedCapability):
        return make_proof_key(
            item.identity,
            item.foreign_source.origin,
            provenance=item.foreign_source.provenance,
            distribution=item.foreign_source.distribution,
            distribution_version=_distribution_version(
                item.foreign_source.distribution
            ),
            semantic_paths=semantic_paths,
        )

    def closure_lookup(
        identity: CapabilityIdentity,
    ) -> tuple[CapabilityIdentity, ...] | None:
        if catalog is None:
            return None
        item = resolve(identity)
        if item is None:
            return None
        proof = catalog.lookup(
            proof_key(item),
            require_closure=True,
        )
        if proof is None:
            return None
        catalog_hits.add(identity)
        return tuple(
            requirement.to_identity()
            for requirement in proof.requirements
        )

    def expand(
        identity: CapabilityIdentity,
    ) -> tuple[CapabilityIdentity, ...]:
        item = resolve(identity)
        if item is None:
            return ()
        return item.capability_source.requirements

    graph = build_capability_graph(
        roots,
        expand,
        closure_lookup=closure_lookup,
    )
    return CapabilityDiscovery(
        graph=graph,
        resolved=resolved,
        catalog_hits=catalog_hits,
        blockers=blockers,
        boundaries=boundaries,
    )


@dataclass
class CapabilityCollapse:
    result: object
    native_proven: dict[CapabilityIdentity, object]


def collapse_python_capability_discovery(
    discovery: CapabilityDiscovery,
    *,
    workspace_root: Path,
    translated_proofs=None,
):
    from qps.cipher.foreign.indexed_native_binding import (
        resolve_indexed_native_binding,
    )
    from qps.cipher.ir.nodes import DependencyRef
    from .capability_graph import (
        CapabilityDisposition,
        collapse_capability_graph,
    )

    native_proven: dict[CapabilityIdentity, object] = {}

    def dependency(identity: CapabilityIdentity) -> DependencyRef:
        return DependencyRef(
            package=identity.module.split(".", 1)[0],
            module=identity.module,
            symbol=(
                ".".join(identity.members)
                if identity.members
                else None
            ),
            semantic_identity=identity.canonical,
        )

    def resolve_leaf(identity: CapabilityIdentity) -> CapabilityDisposition:
        if identity in discovery.catalog_hits:
            return CapabilityDisposition(
                identity,
                "proven",
                "catalog closure proof",
            )

        boundary = discovery.boundaries.get(identity)
        if boundary is not None:
            if boundary.kind == "native-proof-required":
                binding = resolve_indexed_native_binding(
                    dependency(identity),
                    workspace_root,
                )
                if (
                    binding.state == "library-resolved"
                    and binding.binary is not None
                    and binding.native_lookup
                ):
                    native_proven[identity] = binding
                    return CapabilityDisposition(
                        identity,
                        "proven",
                        (
                            "indexed native proof "
                            f"{binding.binary}:{binding.native_lookup}"
                        ),
                    )
                return CapabilityDisposition(
                    identity,
                    "blocked",
                    (
                        "native proof required; "
                        f"indexed resolver state={binding.state}: "
                        f"{binding.detail}"
                    ),
                )

            return CapabilityDisposition(
                identity,
                "blocked",
                boundary.detail,
            )

        if identity in discovery.resolved:
            proof = (translated_proofs or {}).get(identity)
            if proof is not None:
                return CapabilityDisposition(
                    identity,
                    "proven",
                    getattr(
                        proof,
                        "evidence",
                        "translated-and-validated",
                    ),
                )
            return CapabilityDisposition(
                identity,
                "blocked",
                "translated-and-validated proof required",
            )

        return CapabilityDisposition(
            identity,
            "blocked",
            "capability has no source, catalog, or native proof",
        )

    result = collapse_capability_graph(
        discovery.graph,
        resolve_leaf,
    )
    return CapabilityCollapse(
        result=result,
        native_proven=native_proven,
    )


@dataclass
class AuthoredCapabilityDiscovery:
    usage: object
    discovery: CapabilityDiscovery | None

    @property
    def blockers(self) -> tuple[str, ...]:
        usage_blockers = tuple(self.usage.blockers)
        if self.discovery is None:
            return usage_blockers
        graph_blockers = tuple(
            detail
            for _, detail in sorted(
                self.discovery.blockers.items(),
                key=lambda pair: pair[0].canonical,
            )
        )
        return usage_blockers + graph_blockers


def discover_authored_python_capabilities(
    source: str,
    *,
    catalog: CapabilityProofCatalog | None = None,
    semantic_paths: Iterable[Path] = (),
) -> AuthoredCapabilityDiscovery:
    from .capability_graph import discover_capability_usage

    usage = discover_capability_usage(source)
    if usage.blockers:
        # Ambiguous authored semantics must stop narrowing before graph
        # expansion. Never guess a smaller closure.
        return AuthoredCapabilityDiscovery(
            usage=usage,
            discovery=None,
        )

    roots = tuple(
        requirement.identity
        for requirement in usage.requirements
    )
    discovery = discover_python_capability_graph(
        roots,
        catalog=catalog,
        semantic_paths=semantic_paths,
    )
    return AuthoredCapabilityDiscovery(
        usage=usage,
        discovery=discovery,
    )


def store_proven_capability_closures(
    discovery: CapabilityDiscovery,
    collapse,
    catalog: CapabilityProofCatalog,
    *,
    semantic_paths,
) -> tuple[CapabilityIdentity, ...]:
    """Persist only exact capabilities whose complete closure is proven."""
    stored: list[CapabilityIdentity] = []

    for identity in sorted(
        discovery.graph.nodes,
        key=lambda item: (
            -discovery.graph.nodes[item].first_tier,
            item.canonical,
        ),
    ):
        disposition = collapse.result.dispositions.get(identity)
        if disposition is None or disposition.state != "proven":
            continue

        node = discovery.graph.nodes[identity]
        if any(
            collapse.result.dispositions.get(child) is None
            or collapse.result.dispositions[child].state != "proven"
            for child in node.requires
        ):
            continue

        resolved = discovery.resolved.get(identity)
        if resolved is None or resolved.capability_source is None:
            continue

        foreign = resolved.foreign_source
        key = make_proof_key(
            identity,
            resolved.capability_source.source,
            provenance=foreign.provenance,
            distribution=foreign.distribution,
            distribution_version=_distribution_version(
                foreign.distribution
            ),
            semantic_paths=semantic_paths,
        )
        catalog.store(
            CapabilityProof(
                key=key,
                disposition=disposition.state,
                requirements=tuple(
                    StoredCapabilityIdentity.from_identity(child)
                    for child in sorted(
                        node.requires,
                        key=lambda item: item.canonical,
                    )
                ),
                evidence=disposition.detail or "proven capability closure",
                closure=True,
            )
        )
        stored.append(identity)

    catalog.publish()
    return tuple(stored)

def publish_proven_capability_transaction(
    plan,
    discovery: CapabilityDiscovery,
    collapse,
    catalog: CapabilityProofCatalog,
    *,
    semantic_paths,
    fail_after=None,
):
    """Publish validated library candidates before persisting closure proof."""
    from .publish import publish_library_plan

    published = publish_library_plan(
        plan,
        fail_after=fail_after,
    )
    stored = store_proven_capability_closures(
        discovery,
        collapse,
        catalog,
        semantic_paths=semantic_paths,
    )
    return published, stored
