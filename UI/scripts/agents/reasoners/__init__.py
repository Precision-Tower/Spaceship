from UI.scripts.agents.reasoners.gguf import CodeReasoner as GGUFReasoner
from UI.scripts.agents.reasoners.gpu import CodeReasoner as GPUReasoner


class ReasonerFactory:
    @staticmethod
    def get_reasoner(model_path: str, backend: str = "gguf"):
        backend = backend.lower()

        if backend == "gguf":
            return GGUFReasoner(model_path)

        if backend == "gpu":
            return GPUReasoner(model_path)

        raise ValueError(f"Unknown backend: {backend}")


__all__ = ["ReasonerFactory", "GGUFReasoner", "GPUReasoner"]