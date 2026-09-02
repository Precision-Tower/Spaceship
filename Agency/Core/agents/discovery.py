"""Filesystem-authoritative Agent discovery.

An Agent exists when its directory exists directly under Agency/Agents.
No persistent registry or hard-coded Agent identity is consulted.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, Iterable

from Agency.Core.foundation.paths import AGENTS_ROOT


class AgentLaunchError(RuntimeError):
    """Raised when an existing Agent cannot satisfy the launcher contract."""


@dataclass(frozen=True)
class AgentDescriptor:
    name: str
    path: Path
    module_name: str

    @property
    def has_python_package(self) -> bool:
        return (self.path / "__init__.py").is_file()


def _candidate_directories(agents_root: Path) -> Iterable[Path]:
    if not agents_root.is_dir():
        return ()

    return (
        path
        for path in agents_root.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and path.name != "__pycache__"
    )


def discover_agents(
    agents_root: Path | None = None,
) -> dict[str, AgentDescriptor]:
    """Return Agents currently present under Agency/Agents.

    Discovery is performed on every call so deleted Agents cannot survive as
    cached or manually registered identities.
    """

    root = Path(agents_root) if agents_root is not None else AGENTS_ROOT
    discovered = {
        path.name: AgentDescriptor(
            name=path.name,
            path=path,
            module_name=f"Agency.Agents.{path.name}",
        )
        for path in _candidate_directories(root)
    }
    return dict(sorted(discovered.items(), key=lambda item: item[0].casefold()))


def resolve_agent(
    name: str,
    agents_root: Path | None = None,
) -> AgentDescriptor | None:
    """Resolve an Agent name case-insensitively from current filesystem state."""

    requested = name.casefold()
    for descriptor in discover_agents(agents_root).values():
        if descriptor.name.casefold() == requested:
            return descriptor
    return None


def _load_main(descriptor: AgentDescriptor) -> Callable[[list[str]], int]:
    if not descriptor.has_python_package:
        raise AgentLaunchError(
            f"agent exists but has no Python package: {descriptor.name}"
        )

    try:
        module = import_module(descriptor.module_name)
    except Exception as exc:
        raise AgentLaunchError(
            f"failed to import agent {descriptor.name}: {exc}"
        ) from exc

    main = getattr(module, "main", None)
    if not callable(main):
        raise AgentLaunchError(
            f"agent exists but exports no callable main: {descriptor.name}"
        )
    return main


def launch_agent(
    name: str,
    argv: list[str],
    agents_root: Path | None = None,
) -> int:
    """Launch a currently discovered Agent by name."""

    descriptor = resolve_agent(name, agents_root)
    if descriptor is None:
        available = ", ".join(discover_agents(agents_root)) or "(none)"
        raise AgentLaunchError(
            f"agent not available: {name}; available agents: {available}"
        )

    main = _load_main(descriptor)
    result = main(list(argv))
    return int(result) if result is not None else 0
