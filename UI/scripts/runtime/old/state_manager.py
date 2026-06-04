from pathlib import Path
import json

from UI.scripts.agents.core.paths import SESSION_DIR


def save_session(name: str, data: dict):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSION_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_session(name: str):
    path = SESSION_DIR / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class StateManager:
    def __init__(self, filename: str = "state.json"):
        self.path = SESSION_DIR / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not self.path.exists():
            return {}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self, state: dict) -> None:
        self.path.write_text(
            json.dumps(state, indent=2),
            encoding="utf-8",
        )

    def get(self, key: str, default=None):
        return self.load().get(key, default)

    def set(self, key: str, value) -> dict:
        state = self.load()
        state[key] = value
        self.save(state)
        return state
