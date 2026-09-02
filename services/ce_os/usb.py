"""Logical USB mode handling for Phase 1.

This module deliberately models USB state only. It never writes ConfigFS, UDC,
or any live gadget path.
"""

from __future__ import annotations

SAFE_USB_MODE = "none"
USB_MODES = {SAFE_USB_MODE, "bootstrap", "installer"}
USB_MODE_BY_CE_OS_MODE = {
    "node": SAFE_USB_MODE,
    "conserve": SAFE_USB_MODE,
    "bootstrap": "bootstrap",
    "installer": "installer",
}

USB_MODE_DESCRIPTIONS = {
    SAFE_USB_MODE: "No CE-OS USB payload is effectively selected.",
    "bootstrap": "Future read-only CE-OS bootstrap media mode; Phase 1 state only.",
    "installer": "Future bootable Ubuntu LTS/CE-OS installer mode; Phase 1 state only.",
}


def logical_usb_mode_for_request(requested_mode: str) -> str:
    return USB_MODE_BY_CE_OS_MODE.get(requested_mode, SAFE_USB_MODE)


def effective_usb_mode_for_mode(effective_mode: str) -> str:
    return USB_MODE_BY_CE_OS_MODE.get(effective_mode, SAFE_USB_MODE)


def usb_status(usb_mode: str, requested_usb_mode: str | None = None) -> dict[str, object]:
    mode = usb_mode if usb_mode in USB_MODES else SAFE_USB_MODE
    requested = requested_usb_mode if requested_usb_mode in USB_MODES else SAFE_USB_MODE
    return {
        "requested_usb_mode": requested,
        "usb_mode": mode,
        "description": USB_MODE_DESCRIPTIONS[mode],
        "phase1_state_only": True,
        "live_configfs_mutation": False,
        "requires_human_approval_for_live_change": True,
    }
