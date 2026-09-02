from __future__ import annotations

from collections.abc import Iterable

from Agency.Core.capabilities.base import (
    CapabilityDefinition,
    CapabilityRegistry,
    CapabilityRegistryError,
)

CAPABILITY_REGISTRY = CapabilityRegistry(
    (
        CapabilityDefinition(
            name="read_context",
            runtime_owner="Agency.Core.runtime.context_builder",
            description="Read repository and agent context through shared runtime.",
            operations=("read",),
        ),
        CapabilityDefinition(
            name="summarize_context",
            runtime_owner="Agency.Core.runtime.context_builder",
            description="Summarize observed context while preserving uncertainty.",
            operations=("summarize",),
        ),
        CapabilityDefinition(
            name="propose_patch",
            runtime_owner="Agency.Core.runtime.agent_shell",
            description="Prepare mutation proposals without bypassing approval.",
            operations=("propose",),
        ),
        CapabilityDefinition(
            name="prepare_handoff",
            runtime_owner="Agency.Core.runtime.agent_shell",
            description="Prepare reconstructable downstream work handoffs.",
            operations=("handoff",),
        ),
        CapabilityDefinition(
            name="interpret_guardrails",
            runtime_owner="Agency.Core.runtime.agent_shell",
            description="Interpret runtime and action-policy boundaries.",
            operations=("interpret",),
        ),
        CapabilityDefinition(
            name="engineering",
            runtime_owner="Agency.Core.capabilities.engineering",
            description=(
                "Execute the shared engineering mission lifecycle without "
                "depending on a specific agent implementation."
            ),
            operations=(
                "mission_create",
                "mission_status",
                "mission_list",
                "mission_show",
                "mission_resume",
                "inspect",
                "plan",
                "replan",
                "resourcefulness",
                "propose",
                "review",
                "implement",
                "verify",
            ),
        ),
    )
)


def get_capability(name: str) -> CapabilityDefinition:
    return CAPABILITY_REGISTRY.get(name)


def require_capabilities(
    names: Iterable[str],
) -> tuple[CapabilityDefinition, ...]:
    return CAPABILITY_REGISTRY.require(names)


def resolve_capabilities(
    names: Iterable[str],
) -> dict[str, CapabilityDefinition]:
    """
    Resolve declared capability names into concrete definitions.

    The returned mapping preserves declaration order and rejects duplicate
    declarations so capability ownership cannot become ambiguous.
    """

    resolved: dict[str, CapabilityDefinition] = {}

    for definition in require_capabilities(names):
        if definition.name in resolved:
            raise CapabilityRegistryError(
                f"duplicate capability declaration: {definition.name}"
            )
        resolved[definition.name] = definition

    return resolved
