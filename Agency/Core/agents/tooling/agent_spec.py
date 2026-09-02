from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import re

from Agency.Core.foundation.paths import AGENTS_ROOT
from Agency.Core.capabilities.registry import CAPABILITY_REGISTRY

AGENT_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")
NORMALIZED_AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")

DEFAULT_ROLE = "agent_identity_scaffold"
DEFAULT_DESCRIPTION = None
DEFAULT_RUNTIME_SELECTION_MODE = "environment_manifest"
DEFAULT_MODEL_ENABLED = True
DEFAULT_MEMORY_ENABLED = True
DEFAULT_VECTOR_STORE_ENABLED = True
DEFAULT_AUTONOMY_ENABLED = True
DEFAULT_AUTONOMY_BEHAVIOR = "try_before_asking"
DEFAULT_APPROVAL_REQUIRED = True
DEFAULT_PROPOSAL_REQUIRED_FOR_WRITES = True

DEFAULT_CAPABILITIES = (
    "read_context",
    "summarize_context",
    "propose_patch",
    "prepare_handoff",
    "interpret_guardrails",
)
SUPPORTED_CAPABILITIES = frozenset(CAPABILITY_REGISTRY.names())
SUPPORTED_ACTIVATIONS = frozenset({"voice"})
DEFAULT_ACTIVATIONS = {"voice": False}
RESERVED_AGENT_NAMES = frozenset({
    "Agency",
    "Agents",
    "Archive",
    "Core",
    "Memory",
    "Projects",
    "Runtime",
    "State",
})


class AgentSpecValidationError(ValueError):
    def __init__(self, errors: list[str], *, phase: str = "validation") -> None:
        super().__init__("; ".join(errors))
        self.errors = errors
        self.phase = phase


def normalize_agent_name(raw: str) -> str:
    cleaned = AGENT_NAME_RE.sub("", str(raw).strip())
    if not cleaned:
        raise ValueError("agent_name_empty")
    return cleaned[:1].upper() + cleaned[1:]


def agent_slug(agent_name: str) -> str:
    return agent_name.lower()


def available_model_profiles() -> tuple[str, ...]:
    """Return supported runtime launch profile names."""
    return ("local_cpu", "local_gpu")


@dataclass(frozen=True)
class AgentIdentitySpec:
    name: str
    role: str
    description: str | None = None


@dataclass(frozen=True)
class AgentRuntimeSpec:
    model_enabled: bool = DEFAULT_MODEL_ENABLED
    backend: str | None = None
    accelerator: str | None = None
    inference_route: str | None = None
    execution_mode: str | None = None
    router_runtime: str | None = None
    selection_mode: str = DEFAULT_RUNTIME_SELECTION_MODE
    selection_reason: str | None = None
    environment_manifest_path: str | None = None
    model_profile: str | None = None
    inference_target: str | None = None
    environment_detected: bool = False


@dataclass(frozen=True)
class AgentMemorySpec:
    enabled: bool = DEFAULT_MEMORY_ENABLED
    vector_store: bool = DEFAULT_VECTOR_STORE_ENABLED


@dataclass(frozen=True)
class AgentAutonomySpec:
    enabled: bool = DEFAULT_AUTONOMY_ENABLED
    default_behavior: str = DEFAULT_AUTONOMY_BEHAVIOR


@dataclass(frozen=True)
class AgentActionPolicySpec:
    approval_required: bool = DEFAULT_APPROVAL_REQUIRED
    proposal_required_for_writes: bool = DEFAULT_PROPOSAL_REQUIRED_FOR_WRITES


@dataclass(frozen=True)
class AgentSpec:
    identity: AgentIdentitySpec
    runtime: AgentRuntimeSpec = field(default_factory=AgentRuntimeSpec)
    memory: AgentMemorySpec = field(default_factory=AgentMemorySpec)
    autonomy: AgentAutonomySpec = field(default_factory=AgentAutonomySpec)
    capabilities: tuple[str, ...] = DEFAULT_CAPABILITIES
    activations: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_ACTIVATIONS))
    action_policy: AgentActionPolicySpec = field(default_factory=AgentActionPolicySpec)
    preserve_existing: bool = True

    @property
    def agent_name(self) -> str:
        return self.identity.name

    @property
    def role(self) -> str:
        return self.identity.role

    @property
    def description(self) -> str | None:
        return self.identity.description

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_agent_spec(
    *,
    name: str,
    role: str = DEFAULT_ROLE,
    description: str | None = DEFAULT_DESCRIPTION,
    model_profile: str | None = None,
    model_enabled: bool = DEFAULT_MODEL_ENABLED,
    inference_target: str | None = None,
    backend: str | None = None,
    accelerator: str | None = None,
    inference_route: str | None = None,
    execution_mode: str | None = None,
    router_runtime: str | None = None,
    runtime_selection_mode: str = DEFAULT_RUNTIME_SELECTION_MODE,
    runtime_selection_reason: str | None = None,
    runtime_environment_manifest_path: str | None = None,
    runtime_environment_detected: bool = False,
    memory_enabled: bool = DEFAULT_MEMORY_ENABLED,
    vector_store_enabled: bool = DEFAULT_VECTOR_STORE_ENABLED,
    autonomy_enabled: bool = DEFAULT_AUTONOMY_ENABLED,
    default_autonomy_behavior: str = DEFAULT_AUTONOMY_BEHAVIOR,
    capabilities: list[str] | tuple[str, ...] | None = None,
    activations: dict[str, bool] | None = None,
    approval_required: bool = DEFAULT_APPROVAL_REQUIRED,
    proposal_required_for_writes: bool = DEFAULT_PROPOSAL_REQUIRED_FOR_WRITES,
    preserve_existing: bool = True,
) -> AgentSpec:
    try:
        normalized_name = normalize_agent_name(name)
    except ValueError as exc:
        raise AgentSpecValidationError([str(exc)], phase="normalization") from exc
    capability_values = tuple(capabilities) if capabilities is not None else DEFAULT_CAPABILITIES
    activation_values = dict(DEFAULT_ACTIVATIONS)
    if activations:
        activation_values.update(activations)
    return AgentSpec(
        identity=AgentIdentitySpec(
            name=normalized_name,
            role=str(role).strip(),
            description=str(description).strip() if description is not None and str(description).strip() else None,
        ),
        runtime=AgentRuntimeSpec(
            model_enabled=bool(model_enabled),
            backend=(str(backend).strip() if backend is not None and str(backend).strip() else None),
            accelerator=(str(accelerator).strip() if accelerator is not None and str(accelerator).strip() else None),
            inference_route=(str(inference_route).strip() if inference_route is not None and str(inference_route).strip() else None),
            execution_mode=(str(execution_mode).strip() if execution_mode is not None and str(execution_mode).strip() else None),
            router_runtime=(str(router_runtime).strip() if router_runtime is not None and str(router_runtime).strip() else None),
            selection_mode=str(runtime_selection_mode).strip() or DEFAULT_RUNTIME_SELECTION_MODE,
            selection_reason=(str(runtime_selection_reason).strip() if runtime_selection_reason is not None and str(runtime_selection_reason).strip() else None),
            environment_manifest_path=(str(runtime_environment_manifest_path).strip() if runtime_environment_manifest_path is not None and str(runtime_environment_manifest_path).strip() else None),
            model_profile=(str(model_profile).strip() if model_profile is not None and str(model_profile).strip() else None),
            inference_target=(str(inference_target).strip() if inference_target is not None and str(inference_target).strip() else None),
            environment_detected=bool(runtime_environment_detected),
        ),
        memory=AgentMemorySpec(
            enabled=bool(memory_enabled),
            vector_store=bool(vector_store_enabled),
        ),
        autonomy=AgentAutonomySpec(
            enabled=bool(autonomy_enabled),
            default_behavior=str(default_autonomy_behavior).strip(),
        ),
        capabilities=capability_values,
        activations=activation_values,
        action_policy=AgentActionPolicySpec(
            approval_required=bool(approval_required),
            proposal_required_for_writes=bool(proposal_required_for_writes),
        ),
        preserve_existing=bool(preserve_existing),
    )


def validate_agent_spec(spec: AgentSpec) -> list[str]:
    errors: list[str] = []
    name = spec.identity.name
    role = spec.identity.role

    if not name:
        errors.append("identity.name is required")
    elif not NORMALIZED_AGENT_NAME_RE.match(name):
        errors.append(f"identity.name is not a valid normalized agent name: {name}")
    elif name in RESERVED_AGENT_NAMES:
        errors.append(f"identity.name is reserved: {name}")

    if not role:
        errors.append("identity.role is required")

    profiles = available_model_profiles()
    if (
        spec.runtime.model_profile
        and spec.runtime.model_profile != "auto"
        and spec.runtime.model_profile not in profiles
    ):
        errors.append(f"unsupported runtime profile: {spec.runtime.model_profile}")

    seen_capabilities: set[str] = set()
    for capability in spec.capabilities:
        value = str(capability).strip()
        if not value:
            errors.append("empty capability is not allowed")
            continue
        if value in seen_capabilities:
            errors.append(f"duplicate capability: {value}")
        seen_capabilities.add(value)
        if value not in SUPPORTED_CAPABILITIES:
            errors.append(f"unknown capability: {value}")

    for activation, enabled in sorted(spec.activations.items()):
        if activation not in SUPPORTED_ACTIVATIONS:
            errors.append(f"unknown activation: {activation}")
            continue
        if bool(enabled):
            errors.append(f"activation is unsupported by current platform contract: {activation}")

    if not spec.autonomy.default_behavior:
        errors.append("autonomy.default_behavior is required")

    if (AGENTS_ROOT / name).exists() and not spec.preserve_existing:
        errors.append(f"agent already exists and preservation mode is not selected: {name}")

    return errors


def require_valid_agent_spec(spec: AgentSpec) -> AgentSpec:
    errors = validate_agent_spec(spec)
    if errors:
        raise AgentSpecValidationError(errors)
    return spec
