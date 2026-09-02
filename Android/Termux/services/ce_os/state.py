"""State contract and persistence for the CE-OS Pixel Node."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from .paths import state_file as default_state_file
from .usb import SAFE_USB_MODE, USB_MODES, logical_usb_mode_for_request

REQUESTED_MODES = {"node", "conserve", "bootstrap", "installer"}
POWER_STATES = {"POWERED", "MOBILE", "SURVIVAL"}
THERMAL_SEVERITY = {
    "NOMINAL": 0,
    "LIGHT": 1,
    "MODERATE": 2,
    "SEVERE": 3,
    "CRITICAL": 4,
    "EMERGENCY": 5,
    "SHUTDOWN": 6,
}
PLATFORM_STATES = {"ok", "drift", "unknown"}

CONTROL_PLANE_PRESERVED = {"ssh": "preserved", "hotspot": "preserved"}


@dataclass
class CeOsState:
    requested_mode: str = "node"
    effective_mode: str = "conserve"
    platform_state: str = "unknown"
    requested_usb_mode: str = SAFE_USB_MODE
    usb_mode: str = SAFE_USB_MODE
    allow_compute: int = 0
    power_state: str = "POWERED"
    thermal_state: str = "NOMINAL"
    guardian_reasons: list[str] = field(default_factory=lambda: ["platform_unknown"])
    control_plane: dict[str, str] = field(default_factory=lambda: dict(CONTROL_PLANE_PRESERVED))
    schema_version: int = 1
    phase: str = "Phase 1"
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["allow_compute"] = 1 if self.allow_compute else 0
        return data

    def with_updates(self, **updates: Any) -> "CeOsState":
        return replace(self, **updates)


def default_state() -> CeOsState:
    return CeOsState()


def _string(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    return str(value).strip()


def _normalize_requested_mode(value: Any, errors: list[str], fallback: str) -> str:
    mode = _string(value, fallback).lower()
    if mode in REQUESTED_MODES:
        return mode
    errors.append(f"unknown requested_mode {mode!r}; forced to conserve")
    return "conserve"


def _normalize_power_state(value: Any, errors: list[str]) -> str:
    state = _string(value, "POWERED").upper()
    if state in POWER_STATES:
        return state
    errors.append(f"unknown power_state {state!r}; forced to SURVIVAL")
    return "SURVIVAL"


def _normalize_thermal_state(value: Any, errors: list[str]) -> str:
    state = _string(value, "NOMINAL").upper()
    if state in THERMAL_SEVERITY:
        return state
    errors.append(f"unknown thermal_state {state!r}; forced to MODERATE")
    return "MODERATE"


def _normalize_platform_state(value: Any, errors: list[str]) -> str:
    state = _string(value, "unknown").lower()
    if state in PLATFORM_STATES:
        return state
    errors.append(f"unknown platform_state {state!r}; forced to unknown")
    return "unknown"


def _normalize_requested_usb_mode(value: Any, requested_mode: str, errors: list[str]) -> str:
    expected = logical_usb_mode_for_request(requested_mode)
    mode = _string(value, expected).lower()
    if mode not in USB_MODES:
        errors.append(f"unknown requested_usb_mode {mode!r}; forced to {expected}")
        return expected
    if mode != expected:
        errors.append(f"requested_usb_mode {mode!r} did not match requested_mode {requested_mode!r}; forced to {expected}")
        return expected
    return mode


def _normalize_effective_usb_mode(value: Any, errors: list[str]) -> str:
    mode = _string(value, SAFE_USB_MODE).lower()
    if mode in USB_MODES:
        return mode
    errors.append(f"unknown usb_mode {mode!r}; forced to {SAFE_USB_MODE}")
    return SAFE_USB_MODE


def state_from_mapping(data: Mapping[str, Any], *, safe_requested_fallback: str = "node") -> CeOsState:
    errors: list[str] = []
    requested_mode = _normalize_requested_mode(data.get("requested_mode"), errors, safe_requested_fallback)
    power_state = _normalize_power_state(data.get("power_state"), errors)
    thermal_state = _normalize_thermal_state(data.get("thermal_state"), errors)
    platform_state = _normalize_platform_state(data.get("platform_state"), errors)
    requested_usb_mode = _normalize_requested_usb_mode(data.get("requested_usb_mode"), requested_mode, errors)
    usb_mode = _normalize_effective_usb_mode(data.get("usb_mode"), errors)
    existing_errors = data.get("validation_errors", [])
    if isinstance(existing_errors, list):
        errors = [str(item) for item in existing_errors] + errors

    return CeOsState(
        requested_mode=requested_mode,
        effective_mode=_string(data.get("effective_mode"), "conserve").lower(),
        platform_state=platform_state,
        requested_usb_mode=requested_usb_mode,
        usb_mode=usb_mode,
        allow_compute=1 if data.get("allow_compute") in (1, True, "1", "true", "TRUE") else 0,
        power_state=power_state,
        thermal_state=thermal_state,
        guardian_reasons=[str(item) for item in data.get("guardian_reasons", [])]
        if isinstance(data.get("guardian_reasons"), list)
        else [],
        control_plane=dict(CONTROL_PLANE_PRESERVED),
        schema_version=1,
        phase="Phase 1",
        validation_errors=errors,
    )


def load_state(path: Path | None = None) -> CeOsState:
    target = path or default_state_file()
    if not target.exists():
        return default_state()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        state = default_state().with_updates(requested_mode="conserve")
        state.validation_errors.append(f"state file unreadable: {exc}")
        return state
    if not isinstance(raw, dict):
        state = default_state().with_updates(requested_mode="conserve")
        state.validation_errors.append("state file did not contain a JSON object")
        return state
    return state_from_mapping(raw, safe_requested_fallback="conserve")


def save_state(state: CeOsState, path: Path | None = None) -> Path:
    target = path or default_state_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def request_mode(state: CeOsState, requested_mode: str) -> CeOsState:
    errors: list[str] = []
    mode = _normalize_requested_mode(requested_mode, errors, "conserve")
    return state.with_updates(
        requested_mode=mode,
        requested_usb_mode=logical_usb_mode_for_request(mode),
        validation_errors=list(state.validation_errors) + errors,
    )
