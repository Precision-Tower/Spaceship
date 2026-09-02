from Agency.Core.agents.tooling.create_agent import create_agent

__all__ = [
    "create_agent",
    "build_agent_index",
    "query_agent_index",
]


def __getattr__(name: str):
    if name in {"build_agent_index", "query_agent_index"}:
        from Agency.Core.agents.tooling.Chroma import build_agent_index, query_agent_index

        return {
            "build_agent_index": build_agent_index,
            "query_agent_index": query_agent_index,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
