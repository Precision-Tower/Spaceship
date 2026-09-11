#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import pty
import selectors
import signal
import socketserver
import struct
import subprocess
import sys
import termios
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_REPO_ROOT = Path("/home/spaztic/Core/Dashboard")
DEFAULT_HOME = Path("/home/spaztic")


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[OperatorPtyService] {_now()} {message}", flush=True)


@dataclass
class PtySession:
    session_id: str
    process: subprocess.Popen[bytes]
    master_fd: int
    cwd: Path
    created_at: float
    state: str = "running"
    exit_code: int | None = None
    output: bytearray = field(default_factory=bytearray)
    lock: threading.Lock = field(default_factory=threading.Lock)
    reader: threading.Thread | None = None
    rows: int = 30
    cols: int = 100

    @property
    def pid(self) -> int:
        return int(self.process.pid)

    def append_output(self, data: bytes) -> None:
        with self.lock:
            self.output.extend(data)

    def drain_output(self) -> str:
        with self.lock:
            data = bytes(self.output)
            self.output.clear()
        return data.decode("utf-8", errors="replace")

    def poll_state(self) -> None:
        code = self.process.poll()
        if code is not None and self.state == "running":
            self.state = "exited"
            self.exit_code = code


class PtySessionManager:
    def __init__(self, repo_root: Path, home: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.home = home.resolve()
        self.sessions: dict[str, PtySession] = {}
        self.lock = threading.Lock()
        self.shutting_down = False

    def create_session(self, rows: int = 30, cols: int = 100, cwd: str | None = None) -> dict[str, Any]:
        workdir = self.repo_root if not cwd else Path(cwd).resolve()
        if workdir != self.repo_root and self.repo_root not in workdir.parents:
            raise ValueError(f"cwd escapes Dashboard root: {cwd}")
        if not workdir.exists() or not workdir.is_dir():
            raise ValueError(f"cwd does not exist: {workdir}")

        master_fd, slave_fd = pty.openpty()
        self._set_winsize(master_fd, rows, cols)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["HOME"] = str(self.home)
        inherited_path = os.environ.get("PATH", "")
        runtime_bin = self.home / "miniconda3" / "envs" / "weebo_env" / "bin"
        path_parts = [str(runtime_bin)] if runtime_bin.exists() else []
        path_parts.extend(part for part in inherited_path.split(os.pathsep) if part)
        env["PATH"] = os.pathsep.join(path_parts)
        env["PS1"] = r"\u@\h:\w\$ "
        existing_pythonpath = env.get("PYTHONPATH", "")
        pythonpath_parts = [part for part in existing_pythonpath.split(os.pathsep) if part]
        if str(self.repo_root) not in pythonpath_parts:
            pythonpath_parts.insert(0, str(self.repo_root))
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        qps_terminal_rc = self.repo_root / "qps" / "bin" / "terminal.bash"

        if not qps_terminal_rc.is_file():
            raise ValueError(
                f"missing QPS terminal bridge: {qps_terminal_rc}"
            )

        process = subprocess.Popen(
            [
                "/bin/bash",
                "--noprofile",
                "--rcfile",
                str(qps_terminal_rc),
                "-i",
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=str(workdir),
            env=env,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        os.close(slave_fd)

        session_id = f"term-{uuid.uuid4().hex[:12]}"
        session = PtySession(
            session_id=session_id,
            process=process,
            master_fd=master_fd,
            cwd=workdir,
            created_at=time.time(),
            rows=rows,
            cols=cols,
        )
        reader = threading.Thread(target=self._reader_loop, args=(session,), daemon=True)
        session.reader = reader

        with self.lock:
            self.sessions[session_id] = session
        reader.start()
        log(f"created session={session_id} pid={process.pid} cwd={workdir}")
        return self._session_payload(session)

    def write_input(self, session_id: str, data: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        session.poll_state()
        if session.state != "running":
            raise ValueError(f"session is not running: {session_id}")
        os.write(session.master_fd, data.encode("utf-8", errors="replace"))
        return {"ok": True, "session_id": session_id, "bytes": len(data.encode("utf-8", errors="replace"))}

    def read_output(self, session_id: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        session.poll_state()
        payload = self._session_payload(session)
        payload["output"] = session.drain_output()
        return payload

    def resize_session(self, session_id: str, rows: int, cols: int) -> dict[str, Any]:
        session = self._get_session(session_id)
        rows = max(1, min(int(rows), 200))
        cols = max(1, min(int(cols), 400))
        self._set_winsize(session.master_fd, rows, cols)
        session.rows = rows
        session.cols = cols
        return {"ok": True, "session_id": session_id, "rows": rows, "cols": cols}

    def close_session(self, session_id: str) -> dict[str, Any]:
        with self.lock:
            session = self.sessions.pop(session_id, None)
        if session is None:
            return {"ok": True, "session_id": session_id, "state": "missing"}
        self._terminate_session(session)
        log(f"closed session={session_id} pid={session.pid} state={session.state} exit={session.exit_code}")
        return {"ok": True, "session_id": session_id, "state": session.state, "pid": session.pid}

    def list_sessions(self) -> dict[str, Any]:
        with self.lock:
            sessions = list(self.sessions.values())
        for session in sessions:
            session.poll_state()
        return {"ok": True, "sessions": [self._session_payload(session) for session in sessions]}

    def shutdown(self) -> None:
        if self.shutting_down:
            return
        self.shutting_down = True
        with self.lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for session in sessions:
            self._terminate_session(session)
        log("shutdown complete")

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        action = str(request.get("action", ""))
        if action == "ping":
            return {"ok": True, "status": "ready", "host_only": True}
        if action == "create_session":
            return {"ok": True, **self.create_session(
                rows=int(request.get("rows", 30)),
                cols=int(request.get("cols", 100)),
                cwd=request.get("cwd"),
            )}
        if action == "write_input":
            return self.write_input(str(request.get("session_id", "")), str(request.get("input", "")))
        if action == "read_output":
            return {"ok": True, **self.read_output(str(request.get("session_id", "")))}
        if action == "resize_session":
            return self.resize_session(
                str(request.get("session_id", "")),
                int(request.get("rows", 30)),
                int(request.get("cols", 100)),
            )
        if action == "close_session":
            return self.close_session(str(request.get("session_id", "")))
        if action == "list_sessions":
            return self.list_sessions()
        raise ValueError(f"unknown action: {action}")

    def _get_session(self, session_id: str) -> PtySession:
        with self.lock:
            session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"unknown session: {session_id}")
        return session

    def _reader_loop(self, session: PtySession) -> None:
        while not self.shutting_down:
            try:
                data = os.read(session.master_fd, 4096)
            except OSError:
                break
            if not data:
                break
            session.append_output(data)
        session.poll_state()
        if session.state == "running":
            session.state = "exited"
            session.exit_code = session.process.poll()
        session.append_output(f"\r\n[session exited: {session.exit_code}]\r\n".encode("utf-8"))

    def _terminate_session(self, session: PtySession) -> None:
        session.poll_state()
        if session.state == "running":
            try:
                os.killpg(os.getpgid(session.pid), signal.SIGHUP)
            except ProcessLookupError:
                pass
            except Exception as exc:
                log(f"SIGHUP failed for pid={session.pid}: {exc}")
            try:
                session.process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(session.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
                except Exception as exc:
                    log(f"SIGTERM failed for pid={session.pid}: {exc}")
                try:
                    session.process.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(session.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    session.process.wait(timeout=1.5)
        session.poll_state()
        try:
            os.close(session.master_fd)
        except OSError:
            pass

    def _session_payload(self, session: PtySession) -> dict[str, Any]:
        return {
            "session_id": session.session_id,
            "pid": session.pid,
            "state": session.state,
            "exit_code": session.exit_code,
            "cwd": str(session.cwd),
            "created_at": session.created_at,
            "rows": session.rows,
            "cols": session.cols,
        }

    @staticmethod
    def _set_winsize(fd: int, rows: int, cols: int) -> None:
        rows = max(1, min(int(rows), 200))
        cols = max(1, min(int(cols), 400))
        packed = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, packed)


class PtyRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(1024 * 1024)
        if not raw:
            return
        try:
            request = json.loads(raw.decode("utf-8"))
            response = self.server.manager.dispatch(request)  # type: ignore[attr-defined]
        except Exception as exc:
            response = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=5),
            }
        self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))
        self.wfile.flush()


class ThreadedPtyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler_class, manager: PtySessionManager) -> None:
        self.manager = manager
        super().__init__(server_address, handler_class)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OperatorShell localhost PTY service")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--home", default=str(DEFAULT_HOME))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print(f"Refusing non-localhost bind: {args.host}", file=sys.stderr)
        return 2

    manager = PtySessionManager(Path(args.repo_root), Path(args.home))
    server = ThreadedPtyServer((args.host, int(args.port)), PtyRequestHandler, manager)

    def stop(_signum=None, _frame=None) -> None:
        log("shutdown requested")
        manager.shutdown()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    host, port = server.server_address[:2]
    log(f"listening host={host} port={port} repo={manager.repo_root}")
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        manager.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
