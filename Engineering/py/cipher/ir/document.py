from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .nodes import CipherNode


@dataclass(frozen=True)
class SourceArtifact:
    path: str
    family: str
    extension: str

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        family: str,
    ) -> "SourceArtifact":
        source = Path(path)

        return cls(
            path=str(source),
            family=family,
            extension=source.suffix,
        )


@dataclass
class CipherDocument:
    children: list[CipherNode] = field(default_factory=list)
    sources: list[SourceArtifact] = field(default_factory=list)
