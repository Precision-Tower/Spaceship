from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable, Any

from Agency.Core.agents.tooling.agent_spec import (
    DEFAULT_ACTIVATIONS,
    DEFAULT_AUTONOMY_BEHAVIOR,
    DEFAULT_AUTONOMY_ENABLED,
    DEFAULT_CAPABILITIES,
    DEFAULT_MEMORY_ENABLED,
    DEFAULT_MODEL_ENABLED,
    DEFAULT_PROPOSAL_REQUIRED_FOR_WRITES,
    DEFAULT_ROLE,
    DEFAULT_VECTOR_STORE_ENABLED,
    SUPPORTED_CAPABILITIES,
)
from Agency.Core.agents.tooling.agent_spec import (
    AgentSpec,
    AgentSpecValidationError,
    agent_slug,
    available_model_profiles,
    build_agent_spec,
    require_valid_agent_spec,
)
from Agency.Core.foundation.paths import AGENTS_ROOT, stable_path
from Agency.Core.runtime.environment import (
    EnvironmentManifest,
    ResolvedRuntime,
    environment_manifest_path,
    load_or_create_environment_manifest,
)
from Agency.Core.state.engine import init_agent_state


class AgentFactoryError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        phase: str,
        files_written: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.files_written = files_written or []


def write_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def create_agent(agent_name_raw: str) -> dict[str, Any]:
    """Compatibility path for existing callers that pass only a name."""
    spec = build_agent_spec(name=agent_name_raw, role=DEFAULT_ROLE)
    return create_agent_from_spec(spec)


def _runtime_reason_text(resolved: ResolvedRuntime) -> str:
    return "; ".join(resolved.selection_reason) or "Runtime resolved from EnvironmentManifest."


def _resolve_runtime_for_spec(
    spec: AgentSpec,
) -> tuple[AgentSpec, ResolvedRuntime, dict[str, Any]]:
    runtime = spec.runtime

    requested_profile = None
    if runtime.model_profile:
        normalized_profile = runtime.model_profile.strip().lower()
        if normalized_profile != "auto":
            requested_profile = normalized_profile

    manifest = load_or_create_environment_manifest(interactive=False)
    resolved = manifest.resolved_runtime

    if requested_profile:
        resolved = replace(
            resolved,
            accelerator=(
                "cuda"
                if requested_profile == "local_gpu"
                else "cpu"
            ),
            execution_mode=requested_profile,
            selection_reason=[
                f"Explicit runtime profile selected: {requested_profile}"
            ],
        )

    manifest_payload = manifest.to_dict()["EnvironmentManifest"]

    resolved_runtime = replace(
        runtime,
        backend=resolved.backend,
        accelerator=resolved.accelerator,
        inference_route=resolved.inference_route,
        execution_mode=resolved.execution_mode,
        router_runtime=resolved.router_runtime,
        selection_mode=(
            "explicit_profile"
            if requested_profile
            else "environment_manifest"
        ),
        selection_reason=_runtime_reason_text(resolved),
        environment_manifest_path=environment_manifest_path().as_posix(),
        model_profile=runtime.model_profile,
        inference_target=runtime.inference_target,
        environment_detected=True,
    )
    return replace(spec, runtime=resolved_runtime), resolved, manifest_payload


def create_agent_from_spec(spec: AgentSpec) -> dict[str, Any]:
    spec = require_valid_agent_spec(spec)
    spec, runtime_selection, environment_manifest = _resolve_runtime_for_spec(spec)
    spec = require_valid_agent_spec(spec)
    agent_name = spec.agent_name
    agent_dir = AGENTS_ROOT / agent_name
    memory_dir = agent_dir / "memory"
    chroma_dir = memory_dir / "Chroma"

    files = render_agent_files(spec)
    created: list[str] = []
    preserved: list[str] = []

    try:
        for path, text in files.items():
            if write_if_missing(path, text):
                created.append(stable_path(path))
            else:
                preserved.append(stable_path(path))
    except Exception as exc:
        raise AgentFactoryError(
            str(exc),
            phase="filesystem",
            files_written=created,
        ) from exc

    try:
        state_result = init_agent_state(agent_name)
    except Exception as exc:
        raise AgentFactoryError(
            str(exc),
            phase="state_initialization",
            files_written=created,
        ) from exc

    created.extend(state_result.get("created", []))
    preserved.extend(state_result.get("preserved_existing", []))

    return {
        "status": "created",
        "agent": agent_name,
        "agent_dir": stable_path(agent_dir),
        "memory_dir": stable_path(memory_dir),
        "chroma_dir": stable_path(chroma_dir),
        "state_dir": state_result["state_dir"],
        "created": created,
        "preserved_existing": preserved,
        "next_commands": [
            f'python run.py agent ask {agent_name} "current mission"',
            f"python run.py agent memory build {agent_name}",
            f'python run.py agent memory query {agent_name} "current mission"',
            f"python run.py state status-agent {agent_name}",
        ],
        "authority": "agent_creation_only_not_runtime_validation",
        "runtime_selection": runtime_selection.to_dict(),
        "environment_manifest": environment_manifest,
        "agent_spec": spec.to_dict(),
    }


def render_agent_init(spec: AgentSpec) -> str:
    """Render the package-level launcher required by Agent discovery."""

    module_name = agent_slug(spec.agent_name)
    return f"""\"\"\"Launcher package for the {spec.agent_name} Agent.\"\"\"

from .{module_name} import main

__all__ = ["main"]
"""


def render_agent_files(spec: AgentSpec) -> dict[Path, str]:
    agent_name = spec.agent_name
    agent_dir = AGENTS_ROOT / agent_name
    memory_dir = agent_dir / "memory"
    chroma_dir = memory_dir / "Chroma"

    return {
        agent_dir / "__init__.py": render_agent_init(spec),
        agent_dir / "README.md": render_readme(spec),
        agent_dir / f"{agent_slug(agent_name)}.py": render_agent_py(spec),
        memory_dir / "sources.yaml": render_sources_yaml(spec),
        memory_dir / "short_term.yaml": render_short_term_yaml(spec),
        chroma_dir / ".keep": "",
        agent_dir / "runtime.yaml": render_runtime_yaml(spec),
        agent_dir / "output_contract.yaml": render_output_contract_yaml(spec),
        agent_dir / "action_policy.yaml": render_action_policy_yaml(spec),
        agent_dir / "autonomy" / "autonomy.yaml": render_autonomy_yaml(spec),
        agent_dir / "actions" / "proposals" / ".keep": "",
        agent_dir / "actions" / "results" / ".keep": "",
        agent_dir / "actions" / "sandbox" / ".keep": "",
    }


def _yaml_bool(value: bool) -> str:
    return "true" if value else "false"


def _yaml_null_or_string(value: str | None) -> str:
    if value is None:
        return "null"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_runtime_yaml(spec: AgentSpec) -> str:
    backend = spec.runtime.backend or "gguf"
    accelerator = spec.runtime.accelerator or "cpu"
    inference_route = spec.runtime.inference_route or "local"
    execution_mode = spec.runtime.execution_mode or "local_cpu"
    selection_mode = spec.runtime.selection_mode or "environment_manifest"
    selection_reason = spec.runtime.selection_reason or "Runtime resolved from EnvironmentManifest."
    manifest_path = spec.runtime.environment_manifest_path or environment_manifest_path().as_posix()
    manifest_authority = stable_path(Path(manifest_path))
    return f"""AgentRuntime:
  owner: {spec.agent_name}

  identity:
    role: {spec.role}
    description: {_yaml_null_or_string(spec.description)}

  environment:
    manifest: {manifest_path}
    authority: EnvironmentManifest

  RuntimeIdentity:
    runtime:
      backend: {backend}
      accelerator: {accelerator}
      inference_route: {inference_route}
      execution_mode: {execution_mode}

  model:
    enabled: {_yaml_bool(spec.runtime.model_enabled)}
    route: Agency/Core/runtime/model_service.py
    backend: {backend}
    accelerator: {accelerator}
    inference_route: {inference_route}
    execution_mode: {execution_mode}
    router_runtime: {_yaml_null_or_string(spec.runtime.router_runtime)}
    selection_mode: {selection_mode}
    authority: shared_runtime_not_agent_owned
    runtime_authority: {manifest_authority}

  environment_selection:
    detected: {_yaml_bool(spec.runtime.environment_detected)}
    reason: {_yaml_null_or_string(selection_reason)}
    authority: creation_time_observation_not_runtime_guarantee

  compatibility:
  rules:
    - model_output_is_draft
    - model_output_is_not_source_authority
    - model_output_requires_operator_or_action_route_before_mutation
    - agent_does_not_own_model_runtime
"""


def render_output_contract_yaml(spec: AgentSpec) -> str:
    return f"""AgentOutputContract:
  owner: {spec.agent_name}
  status: scaffold_candidate
  authority: output_shape_only_not_truth

  default_mode: basic_agent_response

  modes:
    basic_agent_response:
      required_sections:
        - Observed
        - Inferred
        - Unresolved
        - Next action
      constraints:
        - do_not_invent_files_or_routes
        - distinguish_observed_from_inferred
        - no_completion_claim_without_execution
        - preserve_authority_boundaries
"""


def render_short_term_yaml(spec: AgentSpec) -> str:
    return f"""ShortTermMemory:
  owner: {spec.agent_name}
  status: active_working_memory
  role: temporary_context_not_authority
  memory_enabled: {_yaml_bool(spec.memory.enabled)}
  vector_store_enabled: {_yaml_bool(spec.memory.vector_store)}

  current_focus: null

  recent_events: []

  pending_promotions:
    to_sources_yaml: []

  unresolveds: []

  next_suggested_action: null

  rules:
    - short_term_memory_is_not_authority
    - promote_to_sources_yaml_only_after_review
    - Chroma_indexes_sources_yaml_not_short_term_by_default
    - clear_or_roll_forward_when_context_changes
"""


def render_readme(spec: AgentSpec) -> str:
    description = spec.description or "null"
    backend = spec.runtime.backend or "gguf"
    accelerator = spec.runtime.accelerator or "cpu"
    inference_route = spec.runtime.inference_route or "local"
    execution_mode = spec.runtime.execution_mode or "local_cpu"
    return f"""# {spec.agent_name}

```yaml
{spec.agent_name}:
  role: {spec.role}
  description: {description}
  status: scaffold
  authority: local_agent_memory_only_not_validation

  owns:
    - local_context
    - local_memory
    - role_specific_outputs

  does_not_own:
    - validation
    - source_authority
    - mission_authority_unless_explicitly_granted
    - hidden_truth

  memory:
    enabled: {_yaml_bool(spec.memory.enabled)}
    vector_store: {_yaml_bool(spec.memory.vector_store)}
    sources: memory/sources.yaml
    short_term: memory/short_term.yaml
    chroma: memory/Chroma

  runtime:
    config: runtime.yaml
    model_route: Agency/Core/runtime/model_service.py
    backend: {backend}
    accelerator: {accelerator}
    inference_route: {inference_route}
    execution_mode: {execution_mode}
    model_authority: draft_generation_only_not_truth

  state:
    config: state/agent_state.yaml
    transition_log: state/transition_log.yaml
    authority: state_scaffold_only_not_runtime_authority
```
"""


def render_agent_py(spec: AgentSpec) -> str:
    agent_name = spec.agent_name
    return f"""from __future__ import annotations

import sys
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Agency.Core.runtime.agent_shell import main as shell_main
from Agency.Core.runtime.authoritative_state import authoritative_state as runtime_authoritative_state

AGENT_NAME = "{agent_name}"


def authoritative_state():
    return runtime_authoritative_state(AGENT_NAME)


def main(argv: list[str] | None = None) -> int:
    return shell_main(AGENT_NAME, argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
"""


def render_action_policy_yaml(spec: AgentSpec) -> str:
    allowed = "\n".join(f"    - {capability}" for capability in spec.capabilities)
    return f"""ActionPolicy:
  owner: {spec.agent_name}
  status: scaffold_candidate
  authority: action_boundary_policy_only_not_execution_authority

  default:
    mutation_allowed_from_normal_ask: false
    proposal_required_for_writes: {_yaml_bool(spec.action_policy.proposal_required_for_writes)}
    approval_required: {_yaml_bool(spec.action_policy.approval_required)}

  allowed:
{allowed}

  prohibited:
    - direct_file_mutation_without_action_packet
    - validation_claims
    - canon_promotion
    - irreversible_architecture_change_without_operator_approval
"""


def render_autonomy_yaml(spec: AgentSpec) -> str:
    return f"""Autonomy:
  owner: {spec.agent_name}
  status: scaffold
  authority: autonomous_workflow_policy_only_not_truth
  canon: false
  validation_authority: false

  mode:
    enabled: {_yaml_bool(spec.autonomy.enabled)}
    default_behavior: {spec.autonomy.default_behavior}

  activations:
    voice: {_yaml_bool(bool(spec.activations.get("voice", False)))}

  purpose:
    - reduce_operator_question_load
    - attempt_first_pass_solutions_before_escalation
    - expose_hidden_assumptions
    - preserve_unresolveds
    - maintain_forward_motion_under_uncertainty

  rules:
    - attempt_reversible_solution_when_possible
    - preserve_assumptions_in_output
    - classify_unknowns_before_escalating
    - ask_minimum_required_questions_only
    - never_treat_silence_as_validation
    - never_treat_draft_solution_as_canon
    - never_treat_working_assumption_as_operator_decision

  escalate_to_operator_for:
    - mission_direction_changes
    - identity_or_role_changes
    - irreversible_architecture_choices
    - validation_claims
    - canon_promotion
    - strategic_priority_conflicts
"""


def render_sources_yaml(spec: AgentSpec) -> str:
    return f"""MemorySources:
  owner: {spec.agent_name}
  purpose: agent_memory
  enabled: {_yaml_bool(spec.memory.enabled)}
  vector_store_enabled: {_yaml_bool(spec.memory.vector_store)}
  sources:
    - Agency/Agents/{spec.agent_name}
    - DashboardAuthority.yaml
"""


def format_result(result: dict[str, Any]) -> str:
    lines = [
        "AGENT_CREATED",
        f"status: {result.get('status', 'created')}",
        f"agent: {result['agent']}",
        f"agent_dir: {result['agent_dir']}",
        f"memory_dir: {result['memory_dir']}",
        f"chroma_dir: {result['chroma_dir']}",
        f"authority: {result['authority']}",
        f"state_dir: {result['state_dir']}",
        "",
        "created:",
    ]

    created = result.get("created") or []
    if created:
        lines.extend(f"  - {item}" for item in created)
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("preserved_existing:")

    preserved = result.get("preserved_existing") or []
    if preserved:
        lines.extend(f"  - {item}" for item in preserved)
    else:
        lines.append("  - none")

    runtime_selection = result.get("runtime_selection") or {}
    if runtime_selection:
        lines.append("")
        lines.append("runtime_selection:")
        lines.append(f"  backend: {runtime_selection.get('backend')}")
        lines.append(f"  accelerator: {runtime_selection.get('accelerator')}")
        lines.append(f"  inference_route: {runtime_selection.get('inference_route')}")
        lines.append(f"  execution_mode: {runtime_selection.get('execution_mode')}")

    lines.append("")
    lines.append("next_commands:")
    lines.extend(f"  - {item}" for item in result["next_commands"])

    return "\n".join(lines)


def format_failure(
    *,
    phase: str,
    errors: list[str],
    files_written: list[str] | None = None,
) -> str:
    lines = [
        "AGENT_CREATE_FAILED",
        "status: failed",
        f"phase: {phase}",
        "files_written:",
    ]
    written = files_written or []
    if written:
        lines.extend(f"  - {item}" for item in written)
    else:
        lines.append("  - none")
    lines.append("errors:")
    lines.extend(f"  - {error}" for error in errors)
    return "\n".join(lines)


def _ask_required(prompt: str, *, input_func: Callable[[str], str]) -> str:
    value = input_func(prompt).strip()
    return value


def _ask_optional(prompt: str, default: str | None, *, input_func: Callable[[str], str]) -> str | None:
    suffix = f" [{default}]" if default is not None else ""
    value = input_func(f"{prompt}{suffix}: ").strip()
    if value:
        return value
    return default


def _ask_bool(prompt: str, default: bool, *, input_func: Callable[[str], str]) -> bool:
    marker = "Y/n" if default else "y/N"
    while True:
        value = input_func(f"{prompt} [{marker}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer y or n.")


def _ask_choice(
    prompt: str,
    choices: tuple[str, ...],
    default: str,
    *,
    input_func: Callable[[str], str],
) -> str:
    if not choices:
        return default
    choice_lines = [f"{index}. {value}" for index, value in enumerate(choices, start=1)]
    while True:
        value = input_func(f"{prompt} [{default}]\n" + "\n".join(choice_lines) + "\nselection: ").strip()
        if not value:
            return default
        if value.isdigit():
            index = int(value) - 1
            if 0 <= index < len(choices):
                return choices[index]
        if value in choices:
            return value
        print("Please choose one of the listed values.")


def _ask_multiple(
    prompt: str,
    choices: tuple[str, ...],
    defaults: tuple[str, ...],
    *,
    input_func: Callable[[str], str],
) -> tuple[str, ...]:
    choice_lines = [f"{index}. {value}" for index, value in enumerate(choices, start=1)]
    default_display = ",".join(str(choices.index(value) + 1) for value in defaults if value in choices)
    while True:
        value = input_func(f"{prompt} [{default_display}]\n" + "\n".join(choice_lines) + "\nselection: ").strip()
        if not value:
            return defaults
        selected: list[str] = []
        valid = True
        for part in value.split(","):
            token = part.strip()
            if not token:
                continue
            if token.isdigit():
                index = int(token) - 1
                if 0 <= index < len(choices):
                    selected.append(choices[index])
                    continue
            if token in choices:
                selected.append(token)
                continue
            valid = False
            break
        if valid:
            return tuple(dict.fromkeys(selected))
        print("Please choose comma-separated numbers or capability names.")


def collect_interactive_agent_spec(*, input_func: Callable[[str], str] = input) -> AgentSpec | None:
    name = _ask_required("agent name: ", input_func=input_func)
    role = _ask_optional("role", DEFAULT_ROLE, input_func=input_func) or DEFAULT_ROLE
    description = _ask_optional("description", None, input_func=input_func)
    profiles = available_model_profiles()
    model_profile = _ask_choice("legacy runtime alias", ("environment", *profiles), "environment", input_func=input_func)
    if model_profile == "environment":
        model_profile = None
    model_enabled = _ask_bool("model access enabled", DEFAULT_MODEL_ENABLED, input_func=input_func)
    memory_enabled = _ask_bool("memory enabled", DEFAULT_MEMORY_ENABLED, input_func=input_func)
    vector_store_enabled = _ask_bool("vector storage provisioned", DEFAULT_VECTOR_STORE_ENABLED, input_func=input_func)
    autonomy_enabled = _ask_bool("autonomy enabled", DEFAULT_AUTONOMY_ENABLED, input_func=input_func)
    capabilities = _ask_multiple(
        "capabilities",
        tuple(sorted(SUPPORTED_CAPABILITIES)),
        DEFAULT_CAPABILITIES,
        input_func=input_func,
    )
    voice_enabled = _ask_bool("voice activation enabled", False, input_func=input_func)
    spec = build_agent_spec(
        name=name,
        role=role,
        description=description,
        model_profile=model_profile,
        runtime_selection_mode="explicit_profile" if model_profile else "environment_manifest",
        model_enabled=model_enabled,
        memory_enabled=memory_enabled,
        vector_store_enabled=vector_store_enabled,
        autonomy_enabled=autonomy_enabled,
        capabilities=capabilities,
        activations={"voice": voice_enabled},
    )
    require_valid_agent_spec(spec)
    print("Normalized AgentSpec:")
    print(json.dumps(spec.to_dict(), indent=2))
    confirmed = _ask_bool("create this agent", False, input_func=input_func)
    return spec if confirmed else None


def _add_bool_flags(parser: argparse.ArgumentParser, *, enabled: str, disabled: str, dest: str) -> None:
    parser.add_argument(enabled, dest=dest, action="store_true", default=None)
    parser.add_argument(disabled, dest=dest, action="store_false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python run.py agent create",
        description="Provision a Dashboard agent from a validated AgentSpec.",
        epilog=(
            "Defaults: role=agent_identity_scaffold, runtime=environment_manifest, "
            "model_enabled=true, memory_enabled=true, vector_store_enabled=true, "
            "autonomy_enabled=true, default_autonomy_behavior=try_before_asking, "
            "voice=false."
        ),
    )
    parser.add_argument("agent_name", nargs="?", help="legacy name-only agent creation")
    parser.add_argument("--name", default=None)
    parser.add_argument("--role", default=None)
    parser.add_argument("--description", default=None)
    parser.add_argument("--model-profile", default=None)
    parser.add_argument("--auto-runtime", action="store_true")
    _add_bool_flags(parser, enabled="--model-enabled", disabled="--model-disabled", dest="model_enabled")
    _add_bool_flags(parser, enabled="--memory-enabled", disabled="--memory-disabled", dest="memory_enabled")
    _add_bool_flags(parser, enabled="--vector-store-enabled", disabled="--vector-store-disabled", dest="vector_store_enabled")
    _add_bool_flags(parser, enabled="--autonomy-enabled", disabled="--autonomy-disabled", dest="autonomy_enabled")
    parser.add_argument("--default-autonomy-behavior", default=None)
    parser.add_argument("--capability", action="append", default=None)
    _add_bool_flags(parser, enabled="--voice-enabled", disabled="--voice-disabled", dest="voice_enabled")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--raw", "--json", dest="raw", action="store_true")
    return parser


def _has_declarative_values(args: argparse.Namespace) -> bool:
    for name in (
        "name",
        "role",
        "description",
        "model_profile",
        "auto_runtime",
        "model_enabled",
        "memory_enabled",
        "vector_store_enabled",
        "autonomy_enabled",
        "default_autonomy_behavior",
        "capability",
        "voice_enabled",
    ):
        value = getattr(args, name, None)
        if name == "auto_runtime":
            if value:
                return True
            continue
        if value is not None:
            return True
    return False


def spec_from_args(args: argparse.Namespace, *, input_func: Callable[[str], str] = input) -> AgentSpec | None:
    declarative = _has_declarative_values(args)
    legacy_name_only = bool(args.agent_name) and not declarative

    if not args.agent_name and not declarative:
        if args.non_interactive:
            raise AgentSpecValidationError(["identity.name is required", "identity.role is required"], phase="input")
        return collect_interactive_agent_spec(input_func=input_func)

    name = args.name or args.agent_name
    if not name:
        raise AgentSpecValidationError(["identity.name is required"], phase="input")

    role = args.role
    if role is None:
        if legacy_name_only:
            role = DEFAULT_ROLE
        elif args.non_interactive:
            raise AgentSpecValidationError(["identity.role is required"], phase="input")
        else:
            role = _ask_optional("role", DEFAULT_ROLE, input_func=input_func) or DEFAULT_ROLE

    raw_model_profile = (
        str(args.model_profile).strip()
        if args.model_profile is not None
        else None
    )
    model_profile_auto = bool(
        raw_model_profile and raw_model_profile.lower() == "auto"
    )
    explicit_model_profile = (
        raw_model_profile
        if raw_model_profile and not model_profile_auto
        else None
    )
    del model_profile_auto
    runtime_selection_mode = (
        "explicit_profile"
        if explicit_model_profile
        else "environment_manifest"
    )

    spec = build_agent_spec(
        name=name,
        role=role,
        description=args.description,
        model_profile=explicit_model_profile,
        runtime_selection_mode=runtime_selection_mode,
        model_enabled=DEFAULT_MODEL_ENABLED if args.model_enabled is None else args.model_enabled,
        memory_enabled=DEFAULT_MEMORY_ENABLED if args.memory_enabled is None else args.memory_enabled,
        vector_store_enabled=DEFAULT_VECTOR_STORE_ENABLED if args.vector_store_enabled is None else args.vector_store_enabled,
        autonomy_enabled=DEFAULT_AUTONOMY_ENABLED if args.autonomy_enabled is None else args.autonomy_enabled,
        default_autonomy_behavior=args.default_autonomy_behavior or DEFAULT_AUTONOMY_BEHAVIOR,
        capabilities=args.capability or DEFAULT_CAPABILITIES,
        activations={"voice": bool(args.voice_enabled)} if args.voice_enabled is not None else DEFAULT_ACTIVATIONS,
    )
    require_valid_agent_spec(spec)
    return spec


def main(
    argv: list[str] | None = None,
    *,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        spec = spec_from_args(args, input_func=input_func)
        if spec is None:
            output_func("AGENT_CREATE_CANCELLED")
            output_func("status: cancelled")
            return 2
        result = create_agent_from_spec(spec)
    except AgentSpecValidationError as exc:
        output_func(format_failure(phase=exc.phase, errors=exc.errors))
        return 1
    except AgentFactoryError as exc:
        output_func(format_failure(phase=exc.phase, errors=[str(exc)], files_written=exc.files_written))
        return 1
    except Exception as exc:
        output_func(format_failure(phase="unknown", errors=[str(exc)]))
        return 1

    if args.raw:
        output_func(json.dumps(result, indent=2))
    else:
        output_func(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
