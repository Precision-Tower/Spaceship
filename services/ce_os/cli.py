"""Command line interface for CE-OS Phase 1."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterable

from .guardian import decision_for_state, evaluate_state
from .platform import PlatformResult, verify_from_config
from .state import REQUESTED_MODES, CeOsState, load_state, request_mode, save_state
from .usb import usb_status


def _json_ready(value: Any) -> Any:
    if isinstance(value, CeOsState):
        return value.to_dict()
    if isinstance(value, PlatformResult):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(_json_ready(payload), indent=2, sort_keys=True))


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)


def _emit_mapping(title: str, mapping: dict[str, Any]) -> None:
    print(title)
    for key, value in mapping.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for inner_key, inner_value in value.items():
                print(f"  {inner_key}: {_format_scalar(inner_value)}")
        else:
            print(f"{key}: {_format_scalar(value)}")


def _emit_checks(result: PlatformResult) -> None:
    print(f"platform_state: {result.platform_state}")
    print(f"manifest_path: {result.manifest_path}")
    print(f"observation_source: {result.observation_source}")
    print(f"root_checks_allowed: {_format_scalar(result.root_checks_allowed)}")
    for check in result.checks:
        print(
            f"check {check.name}: {check.status} "
            f"expected={check.expected!r} observed={check.observed!r}"
        )


def _emit(args: argparse.Namespace, title: str, payload: dict[str, Any]) -> None:
    if args.json:
        _emit_json(payload)
    else:
        _emit_mapping(title, _json_ready(payload))


def _state_payload(state: CeOsState) -> dict[str, Any]:
    return {"state": state.to_dict()}


def cmd_status(args: argparse.Namespace) -> int:
    state = evaluate_state(load_state())
    _emit(args, "CE-OS status", _state_payload(state))
    return 0


def cmd_mode(args: argparse.Namespace) -> int:
    state = load_state()
    if args.requested_mode:
        state = evaluate_state(request_mode(state, args.requested_mode))
        save_state(state)
    else:
        state = evaluate_state(state)
    payload = {
        "requested_mode": state.requested_mode,
        "effective_mode": state.effective_mode,
        "requested_usb_mode": state.requested_usb_mode,
        "usb_mode": state.usb_mode,
        "allow_compute": state.allow_compute,
        "guardian_reasons": state.guardian_reasons,
    }
    _emit(args, "CE-OS mode", payload)
    return 0


def cmd_power(args: argparse.Namespace) -> int:
    state = evaluate_state(load_state())
    payload = {
        "power_state": state.power_state,
        "allow_compute": state.allow_compute,
        "effective_mode": state.effective_mode,
        "guardian_reasons": state.guardian_reasons,
        "control_plane": state.control_plane,
    }
    _emit(args, "CE-OS power", payload)
    return 0


def cmd_thermal(args: argparse.Namespace) -> int:
    state = evaluate_state(load_state())
    payload = {
        "thermal_state": state.thermal_state,
        "allow_compute": state.allow_compute,
        "effective_mode": state.effective_mode,
        "guardian_reasons": state.guardian_reasons,
        "control_plane": state.control_plane,
    }
    _emit(args, "CE-OS thermal", payload)
    return 0


def cmd_guardian(args: argparse.Namespace) -> int:
    decision = decision_for_state(load_state())
    _emit(args, "CE-OS guardian", {"guardian": decision.to_dict()})
    return 0


def cmd_platform(args: argparse.Namespace) -> int:
    result = verify_from_config(allow_root_checks=False)
    if args.json:
        _emit_json({"platform": result})
    else:
        _emit_checks(result)
    return 0 if result.ok else 1


def cmd_usb_status(args: argparse.Namespace) -> int:
    state = evaluate_state(load_state())
    _emit(args, "CE-OS USB status", {"usb": usb_status(state.usb_mode, state.requested_usb_mode)})
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    platform = verify_from_config(allow_root_checks=True)
    state = load_state().with_updates(platform_state=platform.platform_state)
    evaluated = evaluate_state(state)
    ok = platform.ok and not evaluated.validation_errors
    payload = {
        "ok": ok,
        "phase": "Phase 1",
        "state": evaluated.to_dict(),
        "platform": platform.to_dict(),
        "live_pixel_mutation": False,
    }
    if args.json:
        _emit_json(payload)
    else:
        _emit_mapping("CE-OS verify", {"ok": ok, "phase": "Phase 1", "live_pixel_mutation": False})
        _emit_mapping("state", evaluated.to_dict())
        _emit_checks(platform)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ce-os", description="CE-OS Pixel Node Phase 1 control CLI")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    subcommands = parser.add_subparsers(dest="command", required=True)

    status = subcommands.add_parser("status", help="show full CE-OS state")
    status.set_defaults(handler=cmd_status)

    mode = subcommands.add_parser("mode", help="show or request a CE-OS mode")
    mode.add_argument("requested_mode", nargs="?", choices=sorted(REQUESTED_MODES))
    mode.set_defaults(handler=cmd_mode)

    power = subcommands.add_parser("power", help="show power policy state")
    power.set_defaults(handler=cmd_power)

    thermal = subcommands.add_parser("thermal", help="show thermal policy state")
    thermal.set_defaults(handler=cmd_thermal)

    guardian = subcommands.add_parser("guardian", help="show guardian decision")
    guardian.set_defaults(handler=cmd_guardian)

    platform = subcommands.add_parser("platform", help="verify approved platform state without root-required checks")
    platform.set_defaults(handler=cmd_platform)

    usb = subcommands.add_parser("usb", help="show USB logical state")
    usb_subcommands = usb.add_subparsers(dest="usb_command", required=True)
    usb_status_command = usb_subcommands.add_parser("status", help="show USB logical mode")
    usb_status_command.set_defaults(handler=cmd_usb_status)

    verify = subcommands.add_parser("verify", help="run Phase 1 local verification; explicit command may use root-required read-only checks")
    verify.set_defaults(handler=cmd_verify)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
