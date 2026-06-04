import yaml
from pathlib import Path

# Resolve path to Dashboard/Models/Shared/State.yaml
# Based on: Dashboard/UI/scripts/runtime/cove_listener.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = BASE_DIR / "Models" / "Shared" / "State.yaml"

def get_state():
    """Reads the current operational state from UI.scripts."""
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, 'r') as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def update_state(key, value):
    """Updates a specific key in the state and persists it to YAML."""
    state = get_state()
    
    # Handling for context_buffer to maintain last 5 interactions
    if key == "context_buffer":
        buffer = state.get("context_buffer", [])
        if isinstance(value, list):
            buffer = value
        else:
            buffer.append(value)
        state["context_buffer"] = buffer[-5:]
    else:
        state[key] = value

    # Ensure directory exists and write update
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        yaml.safe_dump(state, f, default_flow_style=False)
