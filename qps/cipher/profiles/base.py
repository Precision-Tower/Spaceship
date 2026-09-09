from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qps.cipher.ir.document import CipherDocument


@dataclass(frozen=True)
class SemanticCapability:
    semantic_name: str
    implementation_symbol: str
    source_path: str
    source_line: int | None


class CipherProfile(Protocol):
    name: str

    def capabilities(
        self,
        document: CipherDocument,
    ) -> list[SemanticCapability]:
        ...


class EmptyProfile:
    name = "universal"

    def capabilities(
        self,
        document: CipherDocument,
    ) -> list[SemanticCapability]:
        return []
