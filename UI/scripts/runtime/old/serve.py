#!/usr/bin/env python3

import argparse
import json
import time
from pathlib import Path

from UI.scripts.agents.reasoners.gguf import CodeReasoner


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = ROOT / "local" / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def sanitize_literal(text: str) -> str:
    return text.strip().splitlines()[0].strip()

def sanitize_proposal(text: str) -> str:
    cleaned = text.strip()
    if not cleaned.startswith("PROPOSAL:"):
        return "REJECTED_OUTPUT"
    return cleaned

def serve(model_path: Path):
    print(f"[{now()}] WEEBO_SERVER_START")
    print(f"[{now()}] model: {model_path}")

    reasoner = CodeReasoner(str(model_path))

    if not reasoner.load():
        print(f"[{now()}] MODEL_LOAD_FAILED")
        return 1

    print(f"[{now()}] MODEL_READY")
    print("Send one JSON object per line.")
    print('{"mode":"literal","system":"Output only the literal text.","prompt":"READY","max_tokens":8}')
    print("CTRL+C to stop.")

    while True:
        try:
            line = input("> ").strip()

            if not line:
                continue

            if line.lower() in {"exit", "quit", "stop"}:
                print(f"[{now()}] SERVER_STOP")
                return 0

            started = time.perf_counter()

            try:
                request = json.loads(line)
            except Exception as e:
                print(json.dumps({
                    "ok": False,
                    "error": f"invalid_json: {e}",
                }))
                continue

            mode = request.get("mode", "")
            system = request.get("system") or "You are a concise coding assistant."
            prompt = request.get("prompt") or ""
            max_tokens = int(request.get("max_tokens") or 128)

            if not prompt:
                print(json.dumps({
                    "ok": False,
                    "error": "missing_prompt",
                }))
                continue

            text = reasoner.generate(
                system_context=system,
                user_prompt=prompt,
                max_new_tokens=max_tokens,
            )

            if mode == "literal":
                text = sanitize_literal(text)
            elif mode == "proposal":
                text = sanitize_proposal(text)

            elapsed = time.perf_counter() - started

            print(json.dumps({
                "ok": True,
                "mode": mode,
                "elapsed_seconds": round(elapsed, 3),
                "text": text,
            }))

        except KeyboardInterrupt:
            print(f"\n[{now()}] SERVER_STOP")
            return 0

        except Exception as e:
            print(json.dumps({
                "ok": False,
                "error": str(e),
            }))


def main():
    parser = argparse.ArgumentParser(prog="weebo-serve")
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL),
        help="Path to GGUF model",
    )

    args = parser.parse_args()
    return serve(Path(args.model).resolve())


if __name__ == "__main__":
    raise SystemExit(main())