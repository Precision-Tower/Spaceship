__all__ = [
    "build_agent_index",
    "query_agent_index",
    "retrieve_agent_memory",
]


def __getattr__(name: str):
    if name == "build_agent_index":
        from .build_index import build_agent_index

        return build_agent_index

    if name in {"query_agent_index", "retrieve_agent_memory"}:
        from .query_index import query_agent_index, retrieve_agent_memory

        return {
            "query_agent_index": query_agent_index,
            "retrieve_agent_memory": retrieve_agent_memory,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
