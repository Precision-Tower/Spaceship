"""Shared Agent discovery and launch contracts."""

from .discovery import (
    AgentDescriptor,
    AgentLaunchError,
    discover_agents,
    launch_agent,
    resolve_agent,
)

__all__ = [
    "AgentDescriptor",
    "AgentLaunchError",
    "discover_agents",
    "launch_agent",
    "resolve_agent",
]
