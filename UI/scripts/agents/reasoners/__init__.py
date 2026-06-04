# agents/reasoners/__init__.py
from UI.scriptsuf import CodeReasoner as GGUFReasoner
from UI.scriptsu import CodeReasoner as GPUReasoner

class ReasonerFactory:
    @staticmethod
    def get_reasoner(model_path: str, backend: str = "gguf"):
        if backend.lower() == "gguf":
            return GGUFReasoner(model_path)
        elif backend.lower() == "gpu":
            return GPUReasoner(model_path)
        raise ValueError(f"Unknown backend: {backend}")

__all__ = ["ReasonerFactory"]