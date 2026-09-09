from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
from typing import Iterable

from .capability_graph import CapabilityIdentity


CATALOG_SCHEMA = 2


@dataclass(frozen=True)
class CapabilityProofKey:
    identity: str
    source_fingerprint: str
    provenance: str
    distribution: str | None
    distribution_version: str | None
    python_identity: str
    platform_identity: str
    semantics_fingerprint: str


@dataclass(frozen=True)
class StoredCapabilityIdentity:
    module: str
    members: tuple[str, ...] = ()

    @classmethod
    def from_identity(
        cls,
        identity: CapabilityIdentity,
    ) -> "StoredCapabilityIdentity":
        return cls(identity.module, identity.members)

    def to_identity(self) -> CapabilityIdentity:
        return CapabilityIdentity(self.module, self.members)


@dataclass(frozen=True)
class CapabilityProof:
    key: CapabilityProofKey
    disposition: str
    requirements: tuple[StoredCapabilityIdentity, ...]
    evidence: str
    closure: bool = False


def file_fingerprint(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def semantics_fingerprint(paths: Iterable[Path]) -> str:
    digest = sha256()
    for path in sorted(
        (Path(path) for path in paths),
        key=lambda item: str(item),
    ):
        digest.update(str(path).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def python_identity() -> str:
    version = sys.version_info
    return (
        f"{sys.implementation.name}-"
        f"{version.major}.{version.minor}.{version.micro}"
    )


def platform_identity() -> str:
    return "|".join(
        (
            platform.system(),
            platform.machine(),
            platform.release(),
        )
    )


class CapabilityProofCatalog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._proofs: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text())
        if payload.get("schema") != CATALOG_SCHEMA:
            return
        proofs = payload.get("proofs")
        if isinstance(proofs, dict):
            self._proofs = proofs

    @staticmethod
    def _storage_key(key: CapabilityProofKey) -> str:
        payload = json.dumps(
            asdict(key),
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(payload.encode()).hexdigest()

    def lookup(
        self,
        key: CapabilityProofKey,
        *,
        require_closure: bool = False,
    ) -> CapabilityProof | None:
        raw = self._proofs.get(self._storage_key(key))
        if raw is None:
            return None
        proof = CapabilityProof(
            key=CapabilityProofKey(**raw["key"]),
            disposition=raw["disposition"],
            requirements=tuple(
                StoredCapabilityIdentity(
                    module=item["module"],
                    members=tuple(item.get("members", ())),
                )
                for item in raw.get("requirements", ())
            ),
            evidence=raw.get("evidence", ""),
            closure=bool(raw.get("closure", False)),
        )
        if proof.key != key:
            return None
        if require_closure and not proof.closure:
            return None
        return proof

    def store(self, proof: CapabilityProof) -> None:
        self._proofs[self._storage_key(proof.key)] = {
            "key": asdict(proof.key),
            "disposition": proof.disposition,
            "requirements": [
                {
                    "module": item.module,
                    "members": list(item.members),
                }
                for item in proof.requirements
            ],
            "evidence": proof.evidence,
            "closure": proof.closure,
        }

    def publish(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": CATALOG_SCHEMA,
            "proofs": self._proofs,
        }
        candidate = self.path.with_name(self.path.name + ".publish")
        candidate.write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n"
        )
        candidate.replace(self.path)


def make_proof_key(
    identity: CapabilityIdentity,
    source: Path,
    *,
    provenance: str,
    distribution: str | None,
    distribution_version: str | None,
    semantic_paths: Iterable[Path],
) -> CapabilityProofKey:
    return CapabilityProofKey(
        identity=identity.canonical,
        source_fingerprint=file_fingerprint(source),
        provenance=provenance,
        distribution=distribution,
        distribution_version=distribution_version,
        python_identity=python_identity(),
        platform_identity=platform_identity(),
        semantics_fingerprint=semantics_fingerprint(semantic_paths),
    )
