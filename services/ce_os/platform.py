"""Read-only platform verification for the approved CE-OS Pixel."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .paths import platform_manifest_file, platform_state_file

OK = "ok"
DRIFT = "drift"
UNKNOWN = "unknown"

PASS = "pass"
FAIL = "fail"
MISSING = "missing"
INFO = "info"

PLATFORM_LOCK_PATH = "/data/adb/service.d/ce-os-platform-lock.sh"
MAGISK_VERSION_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)(?=$|[^0-9.])")
Runner = Callable[[list[str], float], str | None]


@dataclass(frozen=True)
class PlatformCheck:
    name: str
    expected: Any
    observed: Any
    status: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "expected": self.expected,
            "observed": self.observed,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True)
class PlatformResult:
    platform_state: str
    checks: list[PlatformCheck]
    manifest_path: str
    observation_source: str
    root_checks_allowed: bool = False

    @property
    def ok(self) -> bool:
        return self.platform_state == OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform_state": self.platform_state,
            "ok": self.ok,
            "manifest_path": self.manifest_path,
            "observation_source": self.observation_source,
            "root_checks_allowed": self.root_checks_allowed,
            "checks": [check.to_dict() for check in self.checks],
        }


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    target = path or platform_manifest_file()
    return json.loads(target.read_text(encoding="utf-8"))


def parse_platform_state(text: str) -> dict[str, str]:
    observed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        normalized_key = key.strip().lower().replace("-", "_").replace(".", "_")
        observed[normalized_key] = value.strip()
    return observed


def normalize_bool(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "working", "present", "executable", "unlocked", "orange"}:
        return True
    if text in {"0", "false", "no", "n", "off", "absent", "missing", "locked", "green"}:
        return False
    return None


def normalize_bootloader_unlocked(value: Any) -> bool | None:
    return normalize_bool(value)


def normalize_platform_lock_state(value: Any) -> tuple[bool, bool] | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"executable", "present_executable", "present+executable", "present executable"}:
        return True, True
    if text in {"present", "exists", "not_executable", "not-executable"}:
        return True, False
    if text in {"missing", "absent", "not_found", "not-found"}:
        return False, False
    parsed = normalize_bool(text)
    if parsed is not None:
        return parsed, parsed
    return None


def normalize_magisk_version(value: Any) -> str | None:
    if value is None:
        return None
    match = MAGISK_VERSION_RE.match(str(value))
    if not match:
        return None
    return match.group(1)


def normalize_platform_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    observed = {str(key).strip().lower().replace("-", "_").replace(".", "_"): value for key, value in observation.items()}

    bootloader_value = observed.get("bootloader_unlocked")
    if bootloader_value is None:
        bootloader_value = observed.get("vbmeta_device_state") or observed.get("bootloader_state")
    bootloader_unlocked = normalize_bootloader_unlocked(bootloader_value)
    if bootloader_unlocked is not None:
        observed["bootloader_unlocked"] = "true" if bootloader_unlocked else "false"

    lock_state = observed.get("platform_lock_state")
    if lock_state is None:
        lock_state = observed.get("platform_lock_present")
    normalized_lock = normalize_platform_lock_state(lock_state)
    if normalized_lock is not None:
        present, executable = normalized_lock
        observed["platform_lock_present"] = "true" if present else "false"
        observed.setdefault("platform_lock_executable", "true" if executable else "false")

    executable = normalize_bool(observed.get("platform_lock_executable"))
    if executable is not None:
        observed["platform_lock_executable"] = "true" if executable else "false"

    magisk_version = normalize_magisk_version(observed.get("magisk_version"))
    if magisk_version is not None:
        observed["magisk_version_normalized"] = magisk_version

    return observed


def load_platform_observation(path: Path | None = None, *, allow_root_checks: bool = False) -> tuple[dict[str, Any], str]:
    target = path or platform_state_file()
    if target.exists():
        return normalize_platform_observation(parse_platform_state(target.read_text(encoding="utf-8"))), str(target)
    return collect_local_platform(allow_root_checks=allow_root_checks), "local-read-only"


def _run_read_only(command: list[str], timeout: float = 2.0) -> str | None:
    if shutil.which(command[0]) is None:
        return None
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _getprop(runner: Runner, name: str) -> str | None:
    return runner(["getprop", name], 2.0)


def _platform_lock_script(path: str = PLATFORM_LOCK_PATH) -> str:
    quoted = shlex.quote(path)
    return f"if [ -x {quoted} ]; then echo executable; elif [ -e {quoted} ]; then echo present; else echo missing; fi"


def _record_platform_lock(observed: dict[str, Any], lock_state: str | None, *, authoritative_missing: bool) -> None:
    if not lock_state:
        return

    normalized = normalize_platform_lock_state(lock_state)
    if normalized is None:
        return

    present, executable = normalized

    # An unprivileged Termux shell cannot authoritatively distinguish
    # "missing" from "not accessible" under /data/adb.  Only record an
    # absent lock when the observation was performed with root authority.
    if not present and not authoritative_missing:
        return

    observed["platform_lock_state"] = lock_state
    observed["platform_lock_present"] = "true" if present else "false"
    observed["platform_lock_executable"] = "true" if executable else "false"


def collect_local_platform(*, allow_root_checks: bool = False, runner: Runner = _run_read_only) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    prop_map = {
        "device": "ro.product.device",
        "build": "ro.build.id",
        "build_number": "ro.build.version.incremental",
        "current_slot": "ro.boot.slot_suffix",
        "update_engine_status": "init.svc.update_engine",
    }
    for key, prop in prop_map.items():
        value = _getprop(runner, prop)
        if value:
            observed[key] = value

    bootloader_state = _getprop(runner, "ro.boot.vbmeta.device_state") or _getprop(runner, "ro.boot.verifiedbootstate")
    if bootloader_state:
        observed["bootloader_state"] = bootloader_state
        bootloader_unlocked = normalize_bootloader_unlocked(bootloader_state)
        if bootloader_unlocked is not None:
            observed["bootloader_unlocked"] = "true" if bootloader_unlocked else "false"

    if not observed:
        return observed

    # Ordinary status/platform observation remains unprivileged.
    # Explicit verification is allowed to cross the Magisk boundary.
    if allow_root_checks:
        magisk_version = runner(["su", "-c", "magisk -v"], 3.0)
    else:
        magisk_version = runner(["magisk", "-v"], 2.0)

    if magisk_version:
        observed["magisk_version"] = magisk_version
        normalized_magisk = normalize_magisk_version(magisk_version)
        if normalized_magisk:
            observed["magisk_version_normalized"] = normalized_magisk

    lock_script = _platform_lock_script()
    if allow_root_checks:
        _record_platform_lock(
            observed,
            runner(["su", "-c", lock_script], 3.0),
            authoritative_missing=True,
        )
        root_uid = runner(["su", "-c", "id -u"], 3.0)
        if root_uid is not None:
            observed["root_available"] = "true" if root_uid == "0" else "false"
    else:
        _record_platform_lock(
            observed,
            runner(["sh", "-c", lock_script], 2.0),
            authoritative_missing=False,
        )

    return normalize_platform_observation(observed)


def _check(
    name: str,
    expected: Any,
    observed: Any,
    predicate: Callable[[Any, Any], bool] | None = None,
) -> PlatformCheck:
    if observed is None or observed == "":
        return PlatformCheck(name, expected, observed, MISSING, "observation missing")
    passed = predicate(expected, observed) if predicate else str(expected) == str(observed)
    status = PASS if passed else FAIL
    message = "matched" if passed else "platform drift detected"
    return PlatformCheck(name, expected, observed, status, message)


def _bool_check(name: str, expected: bool, observed: Any) -> PlatformCheck:
    parsed = normalize_bool(observed)
    if parsed is None:
        return PlatformCheck(name, expected, observed, MISSING, "boolean observation missing or invalid")
    status = PASS if parsed is expected else FAIL
    return PlatformCheck(name, expected, parsed, status, "matched" if status == PASS else "platform drift detected")


def _magisk_version_matches(expected: Any, observed: Any) -> bool:
    expected_version = normalize_magisk_version(expected)
    observed_version = normalize_magisk_version(observed)
    return expected_version is not None and observed_version is not None and expected_version == observed_version


def _info_check(name: str, observed: Any, message: str) -> PlatformCheck:
    return PlatformCheck(name, "reported", observed, INFO, message)


def verify_platform(
    manifest: Mapping[str, Any] | None = None,
    observation: Mapping[str, Any] | None = None,
    *,
    manifest_path: Path | None = None,
    observation_source: str = "provided",
    root_checks_allowed: bool = False,
) -> PlatformResult:
    manifest_target = manifest_path or platform_manifest_file()
    manifest_data = dict(manifest) if manifest is not None else load_manifest(manifest_target)
    observed = normalize_platform_observation(dict(observation)) if observation is not None else load_platform_observation(allow_root_checks=root_checks_allowed)[0]

    device = manifest_data.get("device", {})
    android = manifest_data.get("android", {})
    security = manifest_data.get("security", {})

    checks = [
        _bool_check("approved_platform_manifest", True, manifest_data.get("approved")),
        _check("device", device.get("codename"), observed.get("device")),
        _check("build", android.get("build"), observed.get("build")),
        _check("build_number", android.get("build_number"), observed.get("build_number")),
        _info_check("current_slot", observed.get("current_slot"), "operational state only; not platform integrity"),
        _bool_check("bootloader_unlocked", bool(security.get("bootloader_unlocked")), observed.get("bootloader_unlocked")),
        _bool_check("root_available", bool(security.get("root_expected")), observed.get("root_available")),
        _check("magisk_version", security.get("magisk_version"), observed.get("magisk_version"), _magisk_version_matches),
        _check("update_engine_status", security.get("update_engine_status"), observed.get("update_engine_status")),
        _bool_check("platform_lock_present", True, observed.get("platform_lock_present")),
        _bool_check("platform_lock_executable", bool(security.get("platform_lock_executable", True)), observed.get("platform_lock_executable")),
    ]

    integrity_statuses = {check.status for check in checks if check.status != INFO}
    if FAIL in integrity_statuses:
        platform_state = DRIFT
    elif MISSING in integrity_statuses:
        platform_state = UNKNOWN
    else:
        platform_state = OK

    return PlatformResult(
        platform_state=platform_state,
        checks=checks,
        manifest_path=str(manifest_target),
        observation_source=observation_source,
        root_checks_allowed=root_checks_allowed,
    )


def verify_from_config(*, allow_root_checks: bool = False) -> PlatformResult:
    observation, source = load_platform_observation(allow_root_checks=allow_root_checks)
    return verify_platform(observation=observation, observation_source=source, root_checks_allowed=allow_root_checks)
