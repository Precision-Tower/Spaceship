"""Guardian decision model for CE-OS Phase 1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .state import CONTROL_PLANE_PRESERVED, CeOsState, THERMAL_SEVERITY
from .usb import logical_usb_mode_for_request

SAFE_EFFECTIVE_MODE = "conserve"
USB_REALIZATION_MODES = {"bootstrap", "installer"}


@dataclass(frozen=True)
class GuardianDecision:
    requested_mode: str
    effective_mode: str
    requested_usb_mode: str
    usb_mode: str
    allow_compute: int
    reasons: list[str]
    control_plane: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_mode": self.requested_mode,
            "effective_mode": self.effective_mode,
            "requested_usb_mode": self.requested_usb_mode,
            "usb_mode": self.usb_mode,
            "allow_compute": self.allow_compute,
            "reasons": list(self.reasons),
            "control_plane": dict(self.control_plane),
        }


def _append_once(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def evaluate_state(state: CeOsState) -> CeOsState:
    reasons: list[str] = []
    compute_denied = False
    mode_denied = False
    requested_usb_mode = logical_usb_mode_for_request(state.requested_mode)

    if state.platform_state == "drift":
        compute_denied = True
        mode_denied = True
        _append_once(reasons, "platform_drift")
    elif state.platform_state != "ok":
        compute_denied = True
        mode_denied = True
        _append_once(reasons, "platform_unknown")

    if state.power_state == "SURVIVAL":
        compute_denied = True
        mode_denied = True
        _append_once(reasons, "power_survival")
    elif state.power_state == "MOBILE":
        compute_denied = True
        _append_once(reasons, "power_mobile")
        if state.requested_mode in USB_REALIZATION_MODES:
            mode_denied = True
            _append_once(reasons, "usb_power_mobile")

    thermal_denied = THERMAL_SEVERITY.get(state.thermal_state, 99) >= THERMAL_SEVERITY["SEVERE"]
    if thermal_denied:
        compute_denied = True
        _append_once(reasons, f"thermal_{state.thermal_state.lower()}")
        if state.requested_mode in USB_REALIZATION_MODES:
            mode_denied = True
            _append_once(reasons, f"usb_thermal_{state.thermal_state.lower()}")

    if state.requested_mode == "conserve":
        compute_denied = True
        _append_once(reasons, "requested_conserve")

    if state.validation_errors:
        compute_denied = True
        mode_denied = True
        _append_once(reasons, "state_validation_error")

    if state.requested_mode == "conserve" or mode_denied:
        effective_mode = SAFE_EFFECTIVE_MODE
    else:
        effective_mode = state.requested_mode

    allow_compute = 0 if compute_denied else 1
    if not reasons:
        reasons.append("compute_allowed")

    return state.with_updates(
        requested_usb_mode=requested_usb_mode,
        effective_mode=effective_mode,
        allow_compute=allow_compute,
        # usb_mode is observed hardware state. Guardian decides whether
        # a requested mode is permitted; it does not claim USB ownership.
        usb_mode=state.usb_mode,
        guardian_reasons=reasons,
        control_plane=dict(CONTROL_PLANE_PRESERVED),
    )


def decision_for_state(state: CeOsState) -> GuardianDecision:
    evaluated = evaluate_state(state)
    return GuardianDecision(
        requested_mode=evaluated.requested_mode,
        effective_mode=evaluated.effective_mode,
        requested_usb_mode=evaluated.requested_usb_mode,
        usb_mode=evaluated.usb_mode,
        allow_compute=evaluated.allow_compute,
        reasons=list(evaluated.guardian_reasons),
        control_plane=dict(evaluated.control_plane),
    )
