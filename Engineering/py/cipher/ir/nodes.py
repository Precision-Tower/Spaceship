from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TranslationState(str, Enum):
    DIRECT = "direct"
    MAPPED = "mapped"
    INFERRED = "inferred"
    DEFERRED = "deferred"
    UNRESOLVED = "unresolved"
    UNSUPPORTED = "unsupported"


@dataclass
class SourceRef:
    language: str
    path: str = ""
    line: int | None = None
    column: int | None = None


@dataclass
class DependencyRef:
    package: str
    module: str | None = None
    symbol: str | None = None
    alias: str | None = None
    version: str | None = None
    semantic_identity: str | None = None
    source: SourceRef | None = None


@dataclass
class CipherNode:
    kind: str
    name: str | None = None
    value: Any = None
    children: list["CipherNode"] = field(default_factory=list)
    source: SourceRef | None = None
    state: TranslationState = TranslationState.DIRECT
    notes: list[str] = field(default_factory=list)
    dependencies: list[DependencyRef] = field(default_factory=list)
