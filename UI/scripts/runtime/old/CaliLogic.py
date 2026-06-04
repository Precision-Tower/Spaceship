import yaml
from pathlib import Path

from UI.scripts.runtime.cove_listener import get_state, update_state


BASE_DIR = Path(__file__).resolve().parents[3]
CONSTRAINTS_FILE = BASE_DIR / "Models" / "Shared" / "CE-OSv1.yaml"


class CaliLogic:
    """
    Teacher Interface Layer.

    Interprets shared state and applies lightweight constraint checks before
    state mutation. This is not validation authority.
    """

    @staticmethod
    def get_summary() -> str:
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
    def _load_constraints() -> tuple[dict, str]:
        if not CONSTRAINTS_FILE.exists():
            return {}, "constraints_file_missing"

        try:
            with open(CONSTRAINTS_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                return {}, "constraints_malformed"

            constraints = data.get("constraints", {})
            if not isinstance(constraints, dict):
                return {}, "constraints_malformed"

            return constraints, ""

        except Exception as e:
            return {}, f"load_exception: {e}"

    @staticmethod
    def reason(intent: str, lane: str = "global") -> dict:
        update_state("log_level", "reasoning")

        constraints, error = CaliLogic._load_constraints()
        is_valid = bool(intent and intent.strip() and constraints)
        reason_failure = error

        if not constraints:
            is_valid = False
            reason_failure = reason_failure or "system_error: constraints_not_loaded"
        elif constraints.get("global_mutation_lock", False):
            is_valid = False
            reason_failure = "global_mutation_lock_active"

        if is_valid:
            forbidden = list(constraints.get("forbidden_patterns", []))
            lane_data = constraints.get("lanes", {}).get(lane, {})
            forbidden.extend(lane_data.get("forbidden_patterns", []))

            lowered = intent.lower()
            for pattern in forbidden:
                if str(pattern).lower() in lowered:
                    is_valid = False
                    reason_failure = f"forbidden_pattern[{lane}]: {pattern}"
                    break

        status_str = (
            "valid"
            if is_valid
            else f"invalid ({reason_failure})"
            if reason_failure
            else "invalid"
        )

        trace = (
            f"REASONING [{lane}]: Analyzing intent '{intent}' "
            f"-> status={status_str} [rules={len(constraints)}]"
        )
        update_state("context_buffer", trace)
        update_state("log_level", "info")

        return {"ok": is_valid, "reason": reason_failure}

    @staticmethod
    def record_interaction(purpose: str, detail: str, lane: str = "global") -> dict:
        result = CaliLogic.reason(detail, lane)

        if result["ok"]:
            event_desc = f"{purpose} -> {detail}"
            update_state("last_task", purpose)
            update_state("context_buffer", event_desc)
            update_state("system_status", "active")

        return result

    @staticmethod
    def set_system_status(status: str) -> None:
        constraints, _ = CaliLogic._load_constraints()

        if constraints.get("global_mutation_lock", False):
            update_state(
                "context_buffer",
                "REASONING [global]: Status update blocked by global_mutation_lock",
            )
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
        return get_state().get("context_buffer", [])
