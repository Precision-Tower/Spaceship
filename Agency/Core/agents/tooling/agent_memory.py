from __future__ import annotations

import time
import yaml

from Agency.Core.foundation.paths import AGENTS_ROOT, stable_path

def list_agents() -> list[str]:
    agents: list[str] = []

    for path in AGENTS_ROOT.iterdir():
        if not path.is_dir():
            continue

        sources = path / "memory" / "sources.yaml"
        if sources.exists():
            agents.append(path.name)

    return sorted(agents)

def show_short_term_memory(agent_name: str) -> int:
    memory_file = AGENTS_ROOT / agent_name / "memory" / "short_term.yaml"

    print("SHORT_TERM_MEMORY")
    print(f"agent: {agent_name}")
    print(f"path: {stable_path(memory_file)}")

    if not memory_file.exists():
        print("status: missing")
        return 1

    print("status: present")
    print()
    print(memory_file.read_text(encoding="utf-8", errors="replace"))
    return 0

def append_short_term_memory(agent_name: str, note: str) -> int:
    memory_file = AGENTS_ROOT / agent_name / "memory" / "short_term.yaml"

    print("SHORT_TERM_MEMORY_APPEND")
    print(f"agent: {agent_name}")
    print(f"path: {stable_path(memory_file)}")

    if not memory_file.exists():
        print("status: missing")
        return 1

    data = yaml.safe_load(memory_file.read_text(encoding="utf-8")) or {}
    root = data.setdefault("ShortTermMemory", {})
    events = root.setdefault("recent_events", [])

    events.append({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "operator",
        "note": note,
        "authority": "short_term_memory_not_authority",
    })

    memory_file.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )

    print("status: appended")
    return 0

def clear_short_term_memory(agent_name: str, *, approved: bool = False) -> int:
    memory_file = AGENTS_ROOT / agent_name / "memory" / "short_term.yaml"

    print("SHORT_TERM_MEMORY_CLEAR")
    print(f"agent: {agent_name}")
    print(f"path: {stable_path(memory_file)}")

    if not memory_file.exists():
        print("status: missing")
        return 1

    data = yaml.safe_load(memory_file.read_text(encoding="utf-8")) or {}
    root = data.setdefault("ShortTermMemory", {})

    root["recent_events"] = []
    root["unresolveds"] = []
    root["next_suggested_action"] = None

    memory_file.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )

    print("status: cleared")
    return 0

def build_all_indexes() -> int:
    from Agency.Core.agents.tooling.Chroma import build_agent_index

    agents = list_agents()

    if not agents:
        print("NO_AGENTS_WITH_MEMORY_SOURCES")
        return 1

    failures = 0

    for agent in agents:
        print(f"\n=== BUILD {agent} ===")
        code = build_agent_index(agent)
        if code != 0:
            failures += 1

    if failures:
        print(f"AGENT_MEMORY_BUILD_ALL_FAILED: {failures}")
        return 1

    print("AGENT_MEMORY_BUILD_ALL_PASS")
    return 0
