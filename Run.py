#!/usr/bin/env python3

import argparse
import json
import subprocess
import time
import traceback
from pathlib import Path

from UI.scripts.agents.core.paths import PathResolver

from UI.scripts.agents.core.engine import WeeboAgent
from UI.scripts.cli import run_command

from UI.Weebo.weebo import main as weebo_main

ROOT = Path(__file__).resolve().parent
UI_ROOT = ROOT / "UI"
SESSION_DIR = UI_ROOT / "scripts" / "sessions"
WATCH_LOG = SESSION_DIR / "run_watch.jsonl"

GODOT_EXE = ROOT / "local" / "godot" / "Godot_v4.6.3-stable_win64_console.exe"
DEFAULT_GGUF = ROOT / "local" / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"

def watch(event_type: str, payload: dict):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event": event_type,
        "payload": payload,
    }
    with WATCH_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def launch_godot():
    watch("godot_launch_requested", {"exe": str(GODOT_EXE), "ui": str(UI_ROOT)})

    if not GODOT_EXE.exists():
        msg = f"GODOT_NOT_FOUND: {GODOT_EXE}"
        watch("godot_launch_failed", {"reason": msg})
        print(msg)
        return 1

    code = subprocess.call([str(GODOT_EXE), "--path", str(UI_ROOT)])
    watch("godot_exited", {"exit_code": code})
    return code


def run_status():
    print("SPACESHIP_READY")
    print(f"root: {ROOT}")
    print(f"ui: {UI_ROOT}")
    print(f"watch_log: {WATCH_LOG}")

    result = run_command(
        "runtime-state",
        resolver=PathResolver(spaceship_root=ROOT),
    )

    if result is not None:
        print(result)

    watch("status_checked", {"root": str(ROOT), "ui": str(UI_ROOT)})
    return 0


def run_cli_command(command: str):
    watch("cli_command_started", {"command": command})
    start_time = time.perf_counter()

    try:
        result = run_command(
        command,
        resolver=PathResolver(spaceship_root=ROOT),
    )

        elapsed = time.perf_counter() - start_time

        watch(
            "cli_command_completed",
            {
                "command": command,
                "elapsed_seconds": round(elapsed, 3),
                "result": result,
            },
        )

        print(f"[COMMAND TIME] {elapsed:.2f} seconds")

        if result is not None:
            print(result)

        return 0

    except Exception as e:
        elapsed = time.perf_counter() - start_time

        watch(
            "cli_command_failed",
            {
                "command": command,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
        )

        print(f"ERR: {e}")
        return 1


def run_agent(prompt: str, no_model: bool = False):
    watch("agent_prompt_started", {"prompt": prompt, "no_model": no_model})
    start_time = time.perf_counter()

    try:
        if no_model:
            agent = WeeboAgent(spaceship_root=ROOT)
        else:
            agent = WeeboAgent(
                model_path=str(DEFAULT_GGUF),
                backend="gguf",
                spaceship_root=ROOT,
            )


        result = agent.process_command(prompt)
        elapsed = time.perf_counter() - start_time

        if result is None:
            result = ""

        result_text = str(result)

        proposal_dir = UI_ROOT / "scripts" / "patches"
        proposal_dir.mkdir(parents=True, exist_ok=True)

        proposal_path = proposal_dir / "latest_agent_proposal.txt"
        proposal_path.write_text(
            f"PROMPT:\n{prompt}\n\n"
            f"ELAPSED_SECONDS:\n{elapsed:.3f}\n\n"
            f"RESULT:\n{result_text}\n",
            encoding="utf-8",
        )

        print(f"[INFERENCE TIME] {elapsed:.2f} seconds")
        print(result_text)

        watch("agent_proposal_written", {"path": str(proposal_path)})

        watch(
            "agent_prompt_completed",
            {
                "prompt": prompt,
                "no_model": no_model,
                "elapsed_seconds": round(elapsed, 3),
                "result_preview": result_text[:1000],
            },
        )

        return 0

    except Exception as e:
        elapsed = time.perf_counter() - start_time

        watch(
            "agent_prompt_failed",
            {
                "prompt": prompt,
                "no_model": no_model,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
        )

        print(f"ERR: {e}")
        return 1


def show_watch_tail(lines: int = 20):
    if not WATCH_LOG.exists():
        print("NO_WATCH_LOG")
        return 0

    rows = WATCH_LOG.read_text(encoding="utf-8", errors="replace").splitlines()

    for row in rows[-lines:]:
        print(row)

    return 0


def main():
    parser = argparse.ArgumentParser(prog="Spaceship")
    sub = parser.add_subparsers(dest="mode")

    sub.add_parser("status")
    sub.add_parser("godot")

    weebo = sub.add_parser("weebo")
    weebo.add_argument("args", nargs=argparse.REMAINDER)

    cmd = sub.add_parser("cmd")
    cmd.add_argument("command", nargs=argparse.REMAINDER)

    ask = sub.add_parser("ask")
    ask.add_argument("--no-model", action="store_true")
    ask.add_argument("prompt", nargs=argparse.REMAINDER)

    watch_cmd = sub.add_parser("watch")
    watch_cmd.add_argument("--lines", type=int, default=20)

    args = parser.parse_args()

    if args.mode is None or args.mode == "status":
        return run_status()

    if args.mode == "godot":
        return launch_godot()
    if args.mode == "weebo":
        return weebo_main(args.args)

    if args.mode == "cmd":
        command = " ".join(args.command).strip()
        if not command:
            print("ERR: missing command")
            return 2
        return run_cli_command(command)

    if args.mode == "ask":
        prompt = " ".join(args.prompt).strip()
        if not prompt:
            print("ERR: missing prompt")
            return 2
        return run_agent(prompt, no_model=args.no_model)

    if args.mode == "watch":
        return show_watch_tail(args.lines)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())