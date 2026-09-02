from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path
from typing import Any

from Agency.Core.runtime.runtime_config import (
    ModelServerConfig as Config,
    load_model_server_config,
)
from Agency.Core.runtime.environment import environment_payload_for_ui

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]


def default_config() -> Config:
    return load_model_server_config()


START_TIMEOUT = 90.0
STOP_TIMEOUT = 10.0


def emit(payload: dict[str, Any], code: int = 0) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return code


def tail(path: Path, limit: int = 3000) -> str:
    try:
        return path.read_bytes()[-limit:].decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def read_pid(path: Path) -> tuple[int | None, str]:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None, "missing"
    except OSError as exc:
        return None, f"unreadable: {exc}"
    try:
        pid = int(text)
    except ValueError:
        return None, f"invalid: {text!r}"
    return (pid, "present") if pid > 0 else (None, f"invalid pid: {pid}")


def write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(f"{pid}\n", encoding="utf-8")
    os.replace(tmp, path)


def remove_pid(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def process_exists(pid: int) -> bool:
    return Path(f"/proc/{pid}").exists()


def cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [x.decode("utf-8", errors="replace") for x in raw.split(b"\0") if x]


def canon(path: str | Path) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return str(path)


def after(args: list[str], key: str) -> str | None:
    try:
        idx = args.index(key)
    except ValueError:
        return None
    return args[idx + 1] if idx + 1 < len(args) else None


def is_managed(pid: int, cfg: Config) -> tuple[bool, str]:
    args = cmdline(pid)
    if not args:
        return False, "cmdline unreadable"
    if canon(args[0]) != canon(cfg.server_path):
        return False, f"executable mismatch: {args[0]}"
    if canon(after(args, "--model") or "") != canon(cfg.model_path):
        return False, "model argument mismatch"
    if after(args, "--host") != cfg.host:
        return False, "host argument mismatch"
    if after(args, "--port") != str(cfg.port):
        return False, "port argument mismatch"
    if after(args, "--ctx-size") != str(cfg.ctx_size):
        return False, "context argument mismatch"
    if after(args, "--n-gpu-layers") != str(cfg.gpu_layers):
        return False, "gpu layer argument mismatch"
    return True, "managed"


def is_stale_managed(pid: int, cfg: Config) -> tuple[bool, str]:
    args = cmdline(pid)
    if not args:
        return False, "cmdline unreadable"
    if canon(args[0]) != canon(cfg.server_path):
        return False, f"executable mismatch: {args[0]}"
    if after(args, "--host") != cfg.host:
        return False, "host argument mismatch"
    if after(args, "--port") != str(cfg.port):
        return False, "port argument mismatch"

    mismatches: list[str] = []
    if canon(after(args, "--model") or "") != canon(cfg.model_path):
        mismatches.append("model")
    if after(args, "--ctx-size") != str(cfg.ctx_size):
        mismatches.append("context")
    if after(args, "--n-gpu-layers") != str(cfg.gpu_layers):
        mismatches.append("gpu_layers")

    if not mismatches:
        return False, "managed"
    return True, "configuration drift: " + ", ".join(mismatches)


def managed_pids(cfg: Config) -> list[int]:
    found: list[int] = []
    for item in Path("/proc").iterdir():
        if item.name.isdigit():
            pid = int(item.name)
            ok, _reason = is_managed(pid, cfg)
            if ok:
                found.append(pid)
    return sorted(found)


def decode_ipv4(hex_ip: str) -> str:
    return socket.inet_ntoa(bytes.fromhex(hex_ip)[::-1])


def listeners(port: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = Path("/proc/net/tcp").read_text(encoding="utf-8").splitlines()[1:]
    except OSError:
        return rows
    for line in lines:
        parts = line.split()
        if len(parts) < 10 or parts[3] != "0A":
            continue
        local = parts[1]
        host_hex, port_hex = local.rsplit(":", 1)
        try:
            local_port = int(port_hex, 16)
        except ValueError:
            continue
        if local_port == port:
            rows.append({"address": decode_ipv4(host_hex), "port": local_port})
    return rows


def localhost_only(rows: list[dict[str, Any]], cfg: Config) -> bool:
    return all(str(row.get("address")) == cfg.host for row in rows)


def health(cfg: Config, timeout: float = 2.0) -> tuple[bool, str, dict[str, Any] | None]:
    try:
        with urllib.request.urlopen(f"{cfg.endpoint}/health", timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return False, f"health request failed: {exc}", None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = {"raw": body}
    ok = data.get("status") == "ok" or data.get("ok") is True
    return bool(ok), "healthy" if ok else f"unexpected health response: {body[:240]}", data


def _environment_payload() -> dict[str, Any]:
    try:
        return environment_payload_for_ui()
    except Exception as exc:
        return {
            "status": "environment_manifest_unavailable",
            "reason": f"{type(exc).__name__}: {exc}",
            "authority": "EnvironmentManifest",
        }


def base(cfg: Config) -> dict[str, Any]:
    server_exists = cfg.server_path.is_file() and os.access(cfg.server_path, os.X_OK)
    model_exists = cfg.model_path.is_file()
    return {
        "status": "stopped",
        "configured": bool(server_exists and model_exists),
        "healthy": False,
        "pid": None,
        "endpoint": cfg.endpoint,
        "chat_endpoint": cfg.chat_endpoint,
        "model_path": str(cfg.model_path),
        "model_filename": cfg.model_path.name,
        "server_path": str(cfg.server_path),
        "log_path": str(cfg.log_path),
        "pid_path": str(cfg.pid_path),
        "host": cfg.host,
        "port": cfg.port,
        "ctx_size": cfg.ctx_size,
        "model_context_tokens": cfg.ctx_size,
        "n_gpu_layers": cfg.gpu_layers,
        "runtime_profiles_path": str(cfg.runtime_profiles_path),
        "environment_manifest": _environment_payload(),
        "runtime_profile": cfg.profile_name,
        "model_path_source": cfg.model_path_source,
        "context_source": cfg.context_source,
        "gpu_layers_source": cfg.gpu_layers_source,
        "server_path_source": cfg.server_path_source,
        "server_exists": server_exists,
        "model_exists": model_exists,
        "process_running": False,
        "process_verified": False,
        "stale_managed_pid": None,
        "configuration_drift_detected": False,
        "configuration_drift": "",
        "listeners": [],
        "localhost_only": True,
        "reason": "",
    }


def status_payload(cfg: Config | None = None) -> dict[str, Any]:
    cfg = cfg or default_config()
    payload = base(cfg)
    reasons: list[str] = []
    if not payload["server_exists"]:
        reasons.append(f"llama-server binary missing or not executable: {cfg.server_path}")
    if not payload["model_exists"]:
        reasons.append(f"model file missing: {cfg.model_path}")

    pid, pid_state = read_pid(cfg.pid_path)
    payload["pid_file_state"] = pid_state
    rows = listeners(cfg.port)
    payload["listeners"] = rows
    payload["localhost_only"] = localhost_only(rows, cfg)

    managed = managed_pids(cfg)
    payload["managed_pids"] = managed
    verified_pid: int | None = None
    stale_pid: int | None = None
    if pid is not None and process_exists(pid):
        payload["process_running"] = True
        ok, reason = is_managed(pid, cfg)
        if ok:
            verified_pid = pid
        else:
            stale, stale_reason = is_stale_managed(pid, cfg)
            if stale:
                stale_pid = pid
                payload["stale_managed_pid"] = pid
                payload["configuration_drift_detected"] = True
                payload["configuration_drift"] = stale_reason
                reasons.append(f"pid file points to stale managed process {pid}: {stale_reason}")
            else:
                reasons.append(f"pid file points to unrelated process {pid}: {reason}")
    elif pid is not None:
        reasons.append(f"stale pid file points to missing process {pid}")

    if verified_pid is None and managed:
        verified_pid = managed[0]
        payload["process_running"] = True

    payload["pid"] = verified_pid
    payload["process_verified"] = verified_pid is not None
    is_healthy, health_reason, health_data = health(cfg)
    payload["healthy"] = is_healthy
    payload["health_response"] = health_data

    if not payload["configured"]:
        payload["status"] = "error"
        reasons.append("model server is not configured")
    elif rows and not payload["localhost_only"]:
        payload["status"] = "error"
        reasons.append(f"port {cfg.port} is listening beyond localhost")
    elif is_healthy and verified_pid is not None:
        payload["status"] = "ready"
        payload["reason"] = "ready"
        return payload
    elif stale_pid is not None:
        payload["status"] = "configuration_drift"
    elif is_healthy:
        payload["status"] = "error"
        reasons.append("healthy endpoint exists but process identity is not verified")
    elif verified_pid is not None:
        try:
            age = time.time() - cfg.pid_path.stat().st_mtime
        except OSError:
            age = START_TIMEOUT + 1.0
        payload["status"] = "starting" if age <= START_TIMEOUT else "error"
        reasons.append(health_reason)
    elif rows:
        payload["status"] = "error"
        reasons.append(f"port {cfg.port} is occupied by an unverified process")
    else:
        payload["status"] = "stopped" if payload["configured"] else "error"
        reasons.append("llama-server is not running" if payload["configured"] else health_reason)

    payload["reason"] = "; ".join(x for x in reasons if x)
    return payload


def validate(cfg: Config) -> tuple[bool, str]:
    if cfg.host != "127.0.0.1":
        return False, "refusing to bind model server outside localhost"
    if not cfg.server_path.is_file() or not os.access(cfg.server_path, os.X_OK):
        return False, f"llama-server binary missing or not executable: {cfg.server_path}"
    if not cfg.model_path.is_file():
        return False, f"model file missing: {cfg.model_path}"
    return True, "configured"


def start_server(cfg: Config | None = None) -> tuple[dict[str, Any], int]:
    cfg = cfg or default_config()
    ok, reason = validate(cfg)
    if not ok:
        payload = status_payload(cfg)
        payload.update({"status": "error", "reason": reason})
        return payload, 1

    current = status_payload(cfg)
    if current["status"] == "ready":
        if current.get("pid"):
            write_pid(cfg.pid_path, int(current["pid"]))
        current["reason"] = "already ready; duplicate start prevented"
        return current, 0
    if current.get("stale_managed_pid"):
        stopped, code = stop_server(cfg)
        if code:
            return stopped, code
        current = status_payload(cfg)
    if current.get("listeners"):
        current["status"] = "error"
        current["reason"] = current.get("reason") or f"port {cfg.port} is occupied"
        return current, 1

    pid, _pid_state = read_pid(cfg.pid_path)
    if pid is not None and (not process_exists(pid) or not is_managed(pid, cfg)[0]):
        remove_pid(cfg.pid_path)

    cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(DASHBOARD_ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    command = [str(cfg.server_path), "--model", str(cfg.model_path), "--host", cfg.host, "--port", str(cfg.port), "--ctx-size", str(cfg.ctx_size), "--n-gpu-layers", str(cfg.gpu_layers)]
    log_file = cfg.log_path.open("ab", buffering=0)
    try:
        proc = subprocess.Popen(command, cwd=str(DASHBOARD_ROOT), env=env, stdin=subprocess.DEVNULL, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    except OSError as exc:
        log_file.close()
        payload = status_payload(cfg)
        payload.update({"status": "error", "reason": f"failed to launch llama-server: {exc}"})
        return payload, 1

    write_pid(cfg.pid_path, proc.pid)
    deadline = time.time() + START_TIMEOUT
    last_reason = "waiting for health endpoint"
    while time.time() < deadline:
        if proc.poll() is not None:
            log_file.close()
            remove_pid(cfg.pid_path)
            payload = status_payload(cfg)
            payload.update({"status": "error", "reason": f"llama-server exited during startup with code {proc.returncode}. {tail(cfg.log_path)}"})
            return payload, 1
        ok, last_reason, _data = health(cfg, 2.0)
        if ok:
            log_file.close()
            payload = status_payload(cfg)
            payload["reason"] = "ready"
            return payload, 0
        time.sleep(0.5)

    try:
        os.kill(proc.pid, signal.SIGTERM)
    except OSError:
        pass
    log_file.close()
    remove_pid(cfg.pid_path)
    payload = status_payload(cfg)
    payload.update({"status": "error", "reason": f"startup timed out: {last_reason}. {tail(cfg.log_path)}"})
    return payload, 1


def wait_exit(pid: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not process_exists(pid):
            return True
        time.sleep(0.1)
    return not process_exists(pid)


def stop_server(cfg: Config | None = None) -> tuple[dict[str, Any], int]:
    cfg = cfg or default_config()
    state = status_payload(cfg)
    pid = state.get("pid")
    stopping_stale = False
    if not isinstance(pid, int) and isinstance(state.get("stale_managed_pid"), int):
        pid = int(state["stale_managed_pid"])
        stopping_stale = True
    if not isinstance(pid, int):
        file_pid, _ = read_pid(cfg.pid_path)
        if file_pid is not None and not process_exists(file_pid):
            remove_pid(cfg.pid_path)
        if state.get("healthy") or state.get("listeners"):
            state.update({"status": "error", "reason": state.get("reason") or f"refusing to stop unverified process on port {cfg.port}"})
            return state, 1
        state.update({"status": "stopped", "reason": "already stopped", "pid": None})
        return state, 0

    ok, reason = is_managed(pid, cfg)
    if not ok:
        stale, stale_reason = is_stale_managed(pid, cfg)
        if not stale:
            state.update({"status": "error", "reason": f"refusing to kill unrelated process {pid}: {reason}"})
            return state, 1
        stopping_stale = True

    escalated = False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError as exc:
        state.update({"status": "error", "reason": f"failed to terminate llama-server pid {pid}: {exc}"})
        return state, 1

    if not wait_exit(pid, STOP_TIMEOUT):
        escalated = True
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError as exc:
            state.update({"status": "error", "reason": f"failed to kill llama-server pid {pid}: {exc}"})
            return state, 1
        if not wait_exit(pid, 3.0):
            state.update({"status": "error", "reason": f"llama-server pid {pid} did not exit after SIGKILL"})
            return state, 1

    remove_pid(cfg.pid_path)
    deadline = time.time() + 5.0
    remaining = status_payload(cfg)
    while time.time() < deadline:
        remaining = status_payload(cfg)
        if not remaining.get("listeners"):
            stopped_reason = "stopped stale managed process" if stopping_stale else "stopped"
            if escalated:
                stopped_reason += " after SIGKILL escalation"
            remaining.update({"status": "stopped", "reason": stopped_reason, "pid": None})
            return remaining, 0
        time.sleep(0.2)
    remaining.update({"status": "error", "reason": f"port {cfg.port} is still listening after stop"})
    return remaining, 1


def restart_server(cfg: Config | None = None) -> tuple[dict[str, Any], int]:
    cfg = cfg or default_config()
    stopped, code = stop_server(cfg)
    return (stopped, code) if code else start_server(cfg)


def reconcile_server(cfg: Config | None = None) -> tuple[dict[str, Any], int]:
    cfg = cfg or default_config()
    current = status_payload(cfg)
    if current["status"] == "ready":
        current["reason"] = "already reconciled"
        return current, 0
    if current.get("stale_managed_pid"):
        return start_server(cfg)
    if current.get("pid_file_state") not in {"missing", "present"}:
        remove_pid(cfg.pid_path)
        return start_server(cfg)
    if current["status"] == "stopped" and current.get("configured"):
        return start_server(cfg)
    current.update({
        "status": "error",
        "reason": current.get("reason") or "no safe model-server reconciliation action is available",
    })
    return current, 1


def missing_model_self_test() -> tuple[dict[str, Any], int]:
    cfg = replace(
        default_config(),
        model_path=DASHBOARD_ROOT / "local" / "__missing_model_for_manager_self_test__.gguf",
        model_path_source="self_test",
    )
    ok, reason = validate(cfg)
    payload = status_payload(cfg)
    payload.update({"status": "error" if not ok else payload["status"], "reason": reason if not ok else "unexpectedly configured"})
    return payload, 1 if not ok else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m Agency.Core.runtime.model_server_manager")
    parser.add_argument("command", choices=["status", "start", "stop", "restart", "reconcile", "self-test-missing-model"])
    args = parser.parse_args(argv)
    if args.command == "status":
        return emit(status_payload(), 0)
    if args.command == "start":
        return emit(*start_server())
    if args.command == "stop":
        return emit(*stop_server())
    if args.command == "restart":
        return emit(*restart_server())
    if args.command == "reconcile":
        return emit(*reconcile_server())
    if args.command == "self-test-missing-model":
        return emit(*missing_model_self_test())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
