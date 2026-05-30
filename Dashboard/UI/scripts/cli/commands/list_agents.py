import json

from runtime.agent_registry import normalized_agent_registry


def run(args):
    registry = normalized_agent_registry()
    print(json.dumps(registry, indent=2))
