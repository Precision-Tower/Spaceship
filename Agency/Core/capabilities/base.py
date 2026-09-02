from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class CapabilityRegistryError(ValueError):
    """Raised when capability registration or resolution is invalid."""


@dataclass(frozen=True)
class CapabilityDefinition:
    """
    Canonical description of a capability available to factory-created agents.

    A capability definition names the behavior bundle and its runtime owner.
    It does not grant mutation authority by itself; agent action policy remains
    the authority boundary.
    """

    name: str
    runtime_owner: str
    description: str
    operations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise CapabilityRegistryError("capability name is required")
        if not self.runtime_owner.strip():
            raise CapabilityRegistryError(
                f"runtime owner is required for capability: {self.name}"
            )


class CapabilityRegistry:
    """Single authoritative registry for factory-installable capabilities."""

    def __init__(
        self,
        definitions: Iterable[CapabilityDefinition] = (),
    ) -> None:
        self._definitions: dict[str, CapabilityDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: CapabilityDefinition) -> None:
        name = definition.name.strip()
        if name in self._definitions:
            raise CapabilityRegistryError(
                f"duplicate capability registration: {name}"
            )
        self._definitions[name] = definition

    def get(self, name: str) -> CapabilityDefinition:
        normalized = str(name).strip()
        try:
            return self._definitions[normalized]
        except KeyError as exc:
            raise CapabilityRegistryError(
                f"unknown capability: {normalized}"
            ) from exc

    def require(
        self,
        names: Iterable[str],
    ) -> tuple[CapabilityDefinition, ...]:
        return tuple(self.get(name) for name in names)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))

    def definitions(self) -> tuple[CapabilityDefinition, ...]:
        return tuple(self._definitions[name] for name in self.names())
