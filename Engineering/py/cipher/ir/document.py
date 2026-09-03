from __future__ import annotations

from dataclasses import dataclass, field

from .nodes import CipherNode


@dataclass
class CipherDocument:
    children: list[CipherNode] = field(default_factory=list)
