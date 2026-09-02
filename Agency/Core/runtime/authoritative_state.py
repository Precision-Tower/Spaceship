from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from Agency.Core.runtime.inference_policy import is_text_transform_request

try:
    import yaml
except ImportError:
    from Agency.Core import yaml_compat as yaml

from Agency.Core.foundation.paths import AGENCY_ROOT, DASHBOARD_ROOT, PINBOARD_ROOT, stable_path
from Agency.Core.runtime.environment import load_environment_manifest


AGENT_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")
UNAVAILABLE_MESSAGE = "Authoritative runtime state is not currently available."


@dataclass(frozen=True)
class AuthoritativeAgentState:
    agent: str
    available: bool
    identity: dict[str, Any]
    runtime: dict[str, Any]
    environment: dict[str, Any]
    authority: dict[str, Any]
    active_mission: dict[str, Any]
    loaded_policies: list[dict[str, Any]]
    memory: dict[str, Any]
    sources: dict[str, str]
    unavailable_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_agent_name(raw: str) -> str:
    cleaned = AGENT_NAME_RE.sub("", raw.strip())
    if not cleaned:
        raise ValueError("agent_name_empty")
    return cleaned[:1].upper() + cleaned[1:]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _runtime_identity(agent_runtime: dict[str, Any]) -> dict[str, Any]:
    runtime_identity = agent_runtime.get("RuntimeIdentity")
    if not isinstance(runtime_identity, dict):
        runtime_identity = {}
    runtime = runtime_identity.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}

    model = agent_runtime.get("model")
    if not isinstance(model, dict):
        model = {}

    return {
        "backend": runtime.get("backend") or model.get("backend"),
        "accelerator": runtime.get("accelerator") or model.get("accelerator"),
        "inference_route": runtime.get("inference_route") or model.get("inference_route"),
        "execution_mode": runtime.get("execution_mode") or model.get("execution_mode"),
        "router_runtime": model.get("router_runtime"),
        "selection_mode": model.get("selection_mode"),
    }


def _environment_state(agent_runtime: dict[str, Any]) -> dict[str, Any]:
    environment = agent_runtime.get("environment")
    if not isinstance(environment, dict):
        environment = {}

    manifest_value = environment.get("manifest")
    manifest_path = Path(str(manifest_value)) if manifest_value else None
    if manifest_path is not None and not manifest_path.is_absolute():
        manifest_path = DASHBOARD_ROOT / manifest_path

    payload: dict[str, Any] = {
        "manifest": str(manifest_path) if manifest_path else None,
        "authority": environment.get("authority") or "EnvironmentManifest",
        "available": False,
    }
    if manifest_path is None or not manifest_path.exists():
        return payload

    try:
        manifest = load_environment_manifest(manifest_path)
    except Exception as exc:
        payload["load_error"] = f"{type(exc).__name__}: {exc}"
        return payload

    manifest_data = manifest.to_dict().get("EnvironmentManifest", {})
    payload.update(
        {
            "available": True,
            "identity": manifest_data.get("identity", {}),
            "capabilities": manifest_data.get("capabilities", {}),
            "resolved_runtime": manifest.resolved_runtime.to_dict(),
            "manifest_authority": manifest.authority,
            "updated_at": manifest.updated_at,
        }
    )
    return payload


def _policy_entry(name: str, path: Path, root_key: str) -> dict[str, Any]:
    data = _load_yaml(path)
    body = data.get(root_key) if isinstance(data, dict) else {}
    if not isinstance(body, dict):
        body = {}
    return {
        "name": name,
        "loaded": bool(data),
        "path": stable_path(path),
        "authority": body.get("authority"),
        "status": body.get("status"),
    }


def _loaded_policies(agent_dir: Path, runtime_loaded: bool) -> list[dict[str, Any]]:
    runtime_entry = {
        "name": "runtime",
        "loaded": runtime_loaded,
        "path": stable_path(agent_dir / "runtime.yaml"),
        "authority": "EnvironmentManifest",
        "status": "loaded" if runtime_loaded else "missing",
    }
    return [
        runtime_entry,
        _policy_entry("output_contract", agent_dir / "output_contract.yaml", "AgentOutputContract"),
        _policy_entry("action_policy", agent_dir / "action_policy.yaml", "ActionPolicy"),
        _policy_entry("autonomy", agent_dir / "autonomy" / "autonomy.yaml", "Autonomy"),
    ]




def _memory_state(agent_dir: Path) -> dict[str, Any]:
    sources_path = agent_dir / "memory" / "sources.yaml"
    chroma_dir = agent_dir / "memory" / "Chroma"
    data = _load_yaml(sources_path)
    body = data.get("MemorySources") if isinstance(data, dict) else {}
    if not isinstance(body, dict):
        body = {}
    return {
        "loaded": bool(data),
        "enabled": bool(body.get("enabled", False)),
        "vector_store_enabled": bool(body.get("vector_store_enabled", False)),
        "sources_file": stable_path(sources_path),
        "chroma": stable_path(chroma_dir),
        "chroma_exists": chroma_dir.exists(),
        "configured_sources": body.get("sources", []),
        "authority": body.get("authority") or "agent_memory_configuration",
    }


def _active_mission(missions_pinboard: Path | None = None) -> dict[str, Any]:
    pinboard = missions_pinboard or PINBOARD_ROOT / "current.json"
    data = _load_json(pinboard)
    if not data:
        return {
            "active": False,
            "summary": "No active mission.",
            "source": stable_path(pinboard),
        }

    mission = data.get("mission") or data.get("active_mission")
    last_observation = data.get("last_observation") if isinstance(data.get("last_observation"), dict) else {}
    mission_id = None
    intent = None

    if isinstance(mission, dict):
        mission_id = mission.get("mission_id") or mission.get("id")
        intent = mission.get("intent") or mission.get("summary")
    elif mission:
        intent = str(mission)

    if not mission_id and isinstance(last_observation, dict):
        mission_id = last_observation.get("mission_id")

    if not (mission_id or intent):
        return {
            "active": False,
            "summary": "No active mission.",
            "source": stable_path(pinboard),
        }

    return {
        "active": True,
        "mission_id": mission_id,
        "intent": intent,
        "last_observation": last_observation,
        "next_action": data.get("next_action"),
        "source": stable_path(pinboard),
    }


def authoritative_state(
    agent_name: str,
    *,
    agents_root: Path | None = None,
    missions_pinboard: Path | None = None,
) -> AuthoritativeAgentState:
    normalized = normalize_agent_name(agent_name)
    root = agents_root or AGENCY_ROOT / "Agents"
    agent_dir = root / normalized
    runtime_path = agent_dir / "runtime.yaml"
    runtime_yaml = _load_yaml(runtime_path)
    agent_runtime = runtime_yaml.get("AgentRuntime")
    if not isinstance(agent_runtime, dict):
        return AuthoritativeAgentState(
            agent=normalized,
            available=False,
            identity={},
            runtime={},
            environment={},
            authority={},
            active_mission=_active_mission(missions_pinboard),
            loaded_policies=_loaded_policies(agent_dir, False),
            memory=_memory_state(agent_dir),
            sources={"runtime": stable_path(runtime_path)},
            unavailable_reason="runtime_yaml_unavailable",
        )

    identity = agent_runtime.get("identity")
    if not isinstance(identity, dict):
        identity = {}

    environment = _environment_state(agent_runtime)
    model = agent_runtime.get("model")
    if not isinstance(model, dict):
        model = {}

    authority = {
        "runtime_authority": model.get("runtime_authority") or environment.get("manifest"),
        "environment_authority": environment.get("authority") or "EnvironmentManifest",
        "model_authority": model.get("authority"),
        "agent_owns_runtime_selection": False,
        "selection_mode": model.get("selection_mode"),
        "selection_reason": (
            agent_runtime.get("environment_selection", {}).get("reason")
            if isinstance(agent_runtime.get("environment_selection"), dict)
            else None
        ),
    }

    return AuthoritativeAgentState(
        agent=normalized,
        available=True,
        identity={
            "name": agent_runtime.get("owner") or normalized,
            "role": identity.get("role"),
            "description": identity.get("description"),
        },
        runtime=_runtime_identity(agent_runtime),
        environment=environment,
        authority=authority,
        active_mission=_active_mission(missions_pinboard),
        loaded_policies=_loaded_policies(agent_dir, True),
        memory=_memory_state(agent_dir),
        sources={
            "agent_dir": stable_path(agent_dir),
            "runtime": stable_path(runtime_path),
            "environment_manifest": str(environment.get("manifest") or ""),
            "repository_root": str(DASHBOARD_ROOT),
            "agency_root": str(AGENCY_ROOT),
        },
    )


def classify_authoritative_state_request(prompt: str) -> str | None:
    if is_text_transform_request(prompt):
        return None

    text = " ".join(str(prompt or "").lower().split())
    if not text:
        return None

    repository_markers = (
        "agency/core/runtime",
        "environmentmanifest defined",
        "where is environmentmanifest",
        "where is environment manifest",
        ".py",
        ".gd",
        ".yaml",
        ".json",
        "source code",
        "codebase",
        "repository",
    )
    if any(marker in text for marker in repository_markers):
        return None

    if any(phrase in text for phrase in ("who are you", "what are you", "what is your role", "what's your role")):
        return "identity"

    if "policies" in text and any(word in text for word in ("loaded", "active", "using")):
        return "loaded_policies"

    if "mission" in text and any(word in text for word in ("active", "current")):
        return "active_mission"

    if "environment" in text and any(word in text for word in ("running", "runtime", "what", "where")):
        return "environment"

    machine_environment_markers = (
        "what machine",
        "which machine",
        "what host",
        "which host",
        "hosting dashboard",
        "host dashboard",
        "where is dashboard running",
    )
    if any(marker in text for marker in machine_environment_markers):
        return "environment"

    if "model runtime" in text and any(word in text for word in ("selected", "current", "currently", "configured", "using")):
        return "runtime"

    if "backend" in text and any(word in text for word in ("what", "which", "using", "use")):
        return "runtime"

    if "execution mode" in text or ("mode" in text and "execution" in text):
        return "runtime"

    runtime_authority_markers = (
        "runtime authority",
        "runtime decisions",
        "runtime decision",
        "who owns your runtime",
        "own your runtime",
        "where does your runtime",
        "where do your runtime",
        "runtime selection",
    )
    if any(marker in text for marker in runtime_authority_markers):
        return "runtime_authority"

    if "runtime" in text and any(word in text for word in ("authority", "owner", "owned", "determined")):
        return "runtime_authority"

    runtime_state_markers = (
        "your runtime",
        "describe runtime",
        "describe your runtime",
        "runtime configured",
        "runtime are you using",
        "runtime do you use",
    )
    if any(marker in text for marker in runtime_state_markers):
        return "runtime"

    return None


def answer_authoritative_state_question(
    state: AuthoritativeAgentState,
    topic: str,
) -> str:
    if not state.available:
        return UNAVAILABLE_MESSAGE

    if topic == "identity":
        lines = [str(state.identity.get("name") or state.agent)]
        if state.identity.get("role"):
            lines.append(f"Role: {state.identity['role']}")
        if state.identity.get("description"):
            lines.append(f"Description: {state.identity['description']}")
        return "\n".join(lines)

    if topic == "runtime_authority":
        authority = state.authority
        runtime = state.runtime
        manifest = state.environment.get("manifest")
        return (
            "My runtime is determined by the shared EnvironmentManifest.\n"
            "I do not own runtime selection.\n"
            "The shared runtime determines backend, accelerator, execution mode, "
            "and inference routing.\n"
            f"I consume those decisions: backend={runtime.get('backend')}, "
            f"accelerator={runtime.get('accelerator')}, "
            f"execution_mode={runtime.get('execution_mode')}, "
            f"inference_route={runtime.get('inference_route')}.\n"
            f"Runtime authority: {authority.get('runtime_authority') or manifest}."
        )

    if topic == "runtime":
        runtime = state.runtime
        if not any(runtime.get(key) for key in ("backend", "accelerator", "inference_route", "execution_mode")):
            return UNAVAILABLE_MESSAGE
        return (
            f"Backend: {runtime.get('backend')}\n"
            f"Accelerator: {runtime.get('accelerator')}\n"
            f"Inference route: {runtime.get('inference_route')}\n"
            f"Execution mode: {runtime.get('execution_mode')}"
        )

    if topic == "environment":
        environment = state.environment
        if not environment.get("available"):
            return UNAVAILABLE_MESSAGE
        identity = environment.get("identity") if isinstance(environment.get("identity"), dict) else {}
        machine = identity.get("machine") if isinstance(identity.get("machine"), dict) else {}
        operator = identity.get("operator") if isinstance(identity.get("operator"), dict) else {}
        workspace = machine.get("workspace") if isinstance(machine.get("workspace"), dict) else {}
        return (
            f"Operator account: {operator.get('account')}\n"
            f"Machine: {machine.get('hostname')}\n"
            f"Operating system: {machine.get('operating_system')}\n"
            f"Python environment: {machine.get('python_environment')}\n"
            f"Workspace: {workspace.get('name')} ({workspace.get('root')})"
        )

    if topic == "loaded_policies":
        loaded = [item for item in state.loaded_policies if item.get("loaded")]
        if not loaded:
            return UNAVAILABLE_MESSAGE
        return "Loaded policies: " + ", ".join(item["name"] for item in loaded)

    if topic == "active_mission":
        mission = state.active_mission
        if not mission.get("active"):
            return "No active mission."
        mission_id = mission.get("mission_id") or "unknown mission id"
        intent = mission.get("intent") or "no intent summary"
        return f"Active mission: {mission_id}\nIntent: {intent}"

    return UNAVAILABLE_MESSAGE
