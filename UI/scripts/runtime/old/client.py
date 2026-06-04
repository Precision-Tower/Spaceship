#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path


def send_request_json(request: dict) -> dict:
    """
    Temporary client path.

    This does NOT talk to a background server yet.
    It launches serve.py as a subprocess, sends one JSON line, reads one JSON response,
    then exits.

    Next upgrade: persistent stdin/stdout process manager.
    """
    cmd = [
        sys.executable,
        "-m",
        "UI.scripts.runtime.serve",
    ]

    payload = json.dumps(request) + "\nstop\n"

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )

    stdout, _ = proc.communicate(payload)

    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("> "):
            line = line[2:].strip()

        if not line.startswith("{"):
            continue

        try:
            data = json.loads(line)
        except Exception:
            continue

        if "ok" in data:
            return data

    return {
        "ok": False,
        "error": "no_json_response",
        "raw": stdout,
    }


def ask(
    prompt: str,
    system: str = "You are a concise coding assistant.",
    mode: str = "",
    max_tokens: int = 128,
) -> dict:

    if mode == "literal":
        system = (
            "Output only the literal text. "
            "No explanation. "
            "No greeting. "
            "No follow-up."
        )

    if mode == "proposal":
        system = (
            "You are a repository cleanup assistant. "
            "Output must begin with PROPOSAL:. "
            "Propose exactly one small, specific, low-risk repository improvement. "
            "No broad cleanup plans. No dependency updates. No autonomous edits."
        )

    return send_request_json(
        {
            "mode": mode,
            "system": system,
            "prompt": prompt,
            "max_tokens": max_tokens,
        }
    )

def main():
    parser = argparse.ArgumentParser(prog="weebo-client")
    parser.add_argument("prompt", nargs=argparse.REMAINDER)
    parser.add_argument("--system", default="You are a concise coding assistant.")
    parser.add_argument("--mode", default="")
    parser.add_argument("--max-tokens", type=int, default=128)

    args = parser.parse_args()
    prompt = " ".join(args.prompt).strip()

    if not prompt:
        print(json.dumps({"ok": False, "error": "missing_prompt"}))
        return 2

    result = ask(
        prompt=prompt,
        system=args.system,
        mode=args.mode,
        max_tokens=args.max_tokens,
    )

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())