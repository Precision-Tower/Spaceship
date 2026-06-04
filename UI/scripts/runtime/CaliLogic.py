import yaml
from UI.scriptshlib import Path
from UI.scripts.cove_listener import get_state, update_state

# Resolve path to Dashboard/Models/Shared/CE-OSv1.yaml
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONSTRAINTS_FILE = BASE_DIR / "Models" / "Shared" / "CE-OSv1.yaml"

class CaliLogic:
    """
    The Teacher Interface Layer.
    Responsible for interpreting and providing high-level access to the Shared State.
    Acts as the single point of interpretation for State.yaml.
    """

    @staticmethod
    def get_summary() -> str:
        """Returns a human-readable summary of the current system state."""
        state = get_state()
        status = state.get("system_status", "unknown")
        last_task = state.get("last_task", "none")
        buffer_size = len(state.get("context_buffer", []))
        log_level = state.get("log_level", "info")
        
        return (
            f"System Status: {status}\n"
            f"Log Level: {log_level}\n"
            f"Last Task: {last_task}\n"
            f"Context Buffer: {buffer_size}/5 entries"
        )

    @staticmethod
    def _load_constraints() -> dict:
        """Loads axiomatic rules from UI.scriptsOSv1.yaml."""
    def _load_constraints() -> tuple[dict, str]:
        """Loads axiomatic rules from UI.scriptsOSv1.yaml. Returns (data, error_msg)."""
        if not CONSTRAINTS_FILE.exists():
            return {}
            return {}, "constraints_file_missing"
        try:
            with open(CONSTRAINTS_FILE, 'r') as f:
                data = yaml.safe_load(f)
                return data.get("constraints", {}) if isinstance(data, dict) else {}
        except Exception:
            return {}
                if not isinstance(data, dict) or "constraints" not in data:
                    return {}, "constraints_malformed"
                return data.get("constraints", {}), ""
        except Exception as e:
            return {}, f"load_exception: {str(e)}"

    @staticmethod
    def reason(intent: str, lane: str = "global") -> dict:
        """
        Performs internal reasoning/lexical analysis before state mutation.
        Validates intent against CE-OSv1.yaml constraints, scoped by lane.
        """
        update_state("log_level", "reasoning")
        constraints = CaliLogic._load_constraints()
        constraints, error = CaliLogic._load_constraints()
        
        # Fail-closed: require intent and successful constraint load
        is_valid = bool(intent and len(intent.strip()) > 0 and constraints)
        reason_failure = ""
        reason_failure = error

        if not constraints:
            reason_failure = "system_error: constraints_not_loaded"
        elif constraints.get("global_mutation_lock", False):
            is_valid = False
            reason_failure = "global_mutation_lock_active"

        if is_valid:
            # Gather forbidden patterns: global + lane-specific
            forbidden = list(constraints.get("forbidden_patterns", []))
            lane_data = constraints.get("lanes", {}).get(lane, {})
            forbidden.extend(lane_data.get("forbidden_patterns", []))

            # Lexical Constraint Check
            for pattern in forbidden:
                if pattern in intent.lower():
                    is_valid = False
                    reason_failure = f"forbidden_pattern[{lane}]: {pattern.strip()}"
                    break
        
        # Persist reasoning trace to context buffer
        status_str = "valid" if is_valid else f"invalid ({reason_failure})" if reason_failure else "invalid"
        trace = f"REASONING [{lane}]: Analyzing intent '{intent}' -> status={status_str} [rules={len(constraints)}]"
        update_state("context_buffer", trace)
        
        update_state("log_level", "info")
        return {"ok": is_valid, "reason": reason_failure}

    @staticmethod
    def record_interaction(purpose: str, detail: str, lane: str = "global") -> dict:
        """Updates the state with a new interaction event after reasoning, scoped by lane."""
        result = CaliLogic.reason(detail, lane)
        if result["ok"]:
            event_desc = f"{purpose} -> {detail}"
            update_state("last_task", purpose)
            update_state("context_buffer", event_desc)
            update_state("system_status", "active")
        return result

    @staticmethod
    def set_system_status(status: str):
        """Directly updates the system status (initialized/idle/active)."""
        constraints = CaliLogic._load_constraints()
        constraints, _ = CaliLogic._load_constraints()

        if constraints.get("global_mutation_lock", False):
            update_state("context_buffer", "REASONING [global]: Status update blocked by global_mutation_lock")
            return

        allowed = constraints.get("allowed_status_values", [])
        
        if allowed and status not in allowed:
            trace = f"REASONING [global]: Rejection -> Invalid status '{status}'"
            update_state("context_buffer", trace)
            update_state("system_status", "error")
            return
            
        update_state("system_status", status)

    @staticmethod
    def get_context_history() -> list:
        """Returns the rolling context buffer."""
        return get_state().get("context_buffer", [])