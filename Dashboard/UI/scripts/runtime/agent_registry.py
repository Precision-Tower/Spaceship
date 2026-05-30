from pathlib import Path

from runtime.paths import DASHBOARD_ROOT, UI_ROOT


REGISTRY_PATH = UI_ROOT / "scripts" / "agents" / "registry.yaml"


def _parse_scalar(value: str):
    value = value.strip()
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    return value


def _yaml_lines(text: str):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    return lines


def _parse_block(lines, index: int, indent: int):
    if index >= len(lines):
        return None, index
    if lines[index][1].startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines, index: int, indent: int):
    data = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ValueError(f"Unexpected indentation near: {content}")
        if content.startswith("- "):
            break

        key, separator, value = content.partition(":")
        if separator == "":
            raise ValueError(f"Expected key/value entry near: {content}")
        key = key.strip()
        value = value.strip()

        if value:
            data[key] = _parse_scalar(value)
            index += 1
            continue

        if index + 1 < len(lines) and lines[index + 1][0] > line_indent:
            child, index = _parse_block(lines, index + 1, lines[index + 1][0])
            data[key] = child
        else:
            data[key] = None
            index += 1

    return data, index


def _parse_list(lines, index: int, indent: int):
    data = []
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ValueError(f"Unexpected indentation near: {content}")
        if not content.startswith("- "):
            break

        item = content[2:].strip()
        if item:
            data.append(_parse_scalar(item))
            index += 1
            continue

        if index + 1 < len(lines) and lines[index + 1][0] > line_indent:
            child, index = _parse_block(lines, index + 1, lines[index + 1][0])
            data.append(child)
        else:
            data.append(None)
            index += 1

    return data, index


def parse_yaml_subset(text: str):
    lines = _yaml_lines(text)
    if not lines:
        return {}
    data, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError("Could not parse complete registry YAML.")
    return data


def load_agent_registry(path: str | Path = REGISTRY_PATH):
    registry_path = Path(path)
    data = parse_yaml_subset(registry_path.read_text(encoding="utf-8"))
    registry = data.get("AgentRegistry")
    if not isinstance(registry, dict):
        raise ValueError("AgentRegistry root entry missing.")
    return registry_path, registry


def normalized_agent_registry(path: str | Path = REGISTRY_PATH):
    registry_path, registry = load_agent_registry(path)
    active_agent_id = registry.get("active_agent_id")
    models = registry.get("models") or {}
    agents = registry.get("agents") or {}

    normalized_agents = []
    for agent_id in sorted(agents.keys()):
        agent = agents[agent_id] or {}
        model_id = agent.get("model_id")
        model = models.get(model_id, {}) if model_id else {}
        prompt_path = agent.get("prompt_path")
        model_path = model.get("path")
        prompt_abs = UI_ROOT / "scripts" / str(prompt_path) if prompt_path else None
        model_abs = DASHBOARD_ROOT / str(model_path) if model_path else None

        normalized_agents.append({
            "id": agent_id,
            "active": agent_id == active_agent_id,
            "display_name": agent.get("display_name"),
            "role": agent.get("role"),
            "status": agent.get("status"),
            "prompt_path": prompt_path,
            "prompt_exists": bool(prompt_abs and prompt_abs.exists()),
            "model_id": model_id,
            "model": {
                "label": model.get("label"),
                "path": model_path,
                "path_exists": bool(model_abs and model_abs.exists()),
                "status": model.get("status"),
                "execution_enabled": bool(model.get("execution_enabled", False)),
            },
            "tools": agent.get("tools") or [],
            "blocked_claims": agent.get("blocked_claims") or [],
        })

    return {
        "status": "registry_loaded",
        "registry_path": str(registry_path),
        "authority": registry.get("authority"),
        "version": registry.get("version"),
        "active_agent_id": active_agent_id,
        "models": models,
        "agents": normalized_agents,
    }
