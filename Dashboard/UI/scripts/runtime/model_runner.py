from pathlib import Path

def model_available(model_path: str | Path) -> bool:
    p = Path(model_path)
    return p.exists() and (p / "config.json").exists()

def generate_stub(agent: str, task: str, context: str = "") -> str:
    return f"MODEL_STUB\nagent={agent}\ntask={task}\ncontext_chars={len(context)}\n"
