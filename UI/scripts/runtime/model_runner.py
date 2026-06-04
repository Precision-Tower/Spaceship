from __future__ import annotations
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys

def model_available(model_path: str | Path) -> bool:
    p = Path(model_path)
    return p.exists() and (p / "config.json").exists()

def generate_stub(agent: str, task: str, context: str = "") -> str:
    return f"MODEL_STUB\nagent={agent}\ntask={task}\ncontext_chars={len(context)}\n"

@dataclass
class ModelRunResult:
    ok: bool
    status: str
    text: str = ""
    reason: str = ""

def _get_model_python_cmd() -> list[str]:
    """
    Resolves the command to run the heavy model environment.
    Priority:
    1. CALI_MODEL_PYTHON environment variable.
    2. local.runtime.yaml configuration.
    3. Standard path discovery (~/miniconda3, ~/anaconda3).
    4. 'conda run -n cali-model python' fallback.
    """
    env_path = os.environ.get("CALI_MODEL_PYTHON")
    if env_path:
        print(f"DISCOVERY: Using CALI_MODEL_PYTHON env var: {env_path}", file=sys.stderr)
        return [env_path]

    yaml_path = Path(__file__).parent / "local.runtime.yaml"
    if yaml_path.exists():
        try:
            content = yaml_path.read_text()
            for line in content.splitlines():
                if line.strip().startswith("cali_model_python:"):
                    path = line.split(":", 1)[1].strip()
                    print(f"DISCOVERY: Using local.runtime.yaml: {path}", file=sys.stderr)
                    return [path]
        except Exception as e:
            print(f"DISCOVERY: Failed to read local.runtime.yaml: {e}", file=sys.stderr)

    home = os.path.expanduser("~")
    suffix = "bin/python" if os.name != "nt" else "python.exe"
    standard_roots = [
        os.path.join(home, "miniconda3"),
        os.path.join(home, "anaconda3"),
        os.path.join(home, "opt/anaconda3"),
        "C:\\ProgramData\\miniconda3",
    ]
    
    for root in standard_roots:
        path = os.path.join(root, "envs", "cali-model", suffix)
        if os.path.exists(path):
            print(f"DISCOVERY: Auto-discovered runtime at: {path}", file=sys.stderr)
            return [path]

    conda_exec = "conda"
    if os.name == "nt":
        for root in standard_roots:
            p = os.path.join(root, "Scripts", "conda.exe")
            if os.path.exists(p):
                conda_exec = p
                break

    print("DISCOVERY: Falling back to 'conda run -n cali-model'", file=sys.stderr)
    return [conda_exec, "run", "-n", "cali-model", "--no-capture-output", "python"]
def _result_from_payload(payload: dict) -> ModelRunResult:
    return ModelRunResult(
        ok=bool(payload.get("ok")),
        status=str(payload.get("status", "blocked_model_subprocess_error")),
        text=str(payload.get("text", "")),
        reason=str(payload.get("reason", "")),
    )


def _decode_subprocess_result(stdout: str, stderr: str, returncode: int) -> ModelRunResult:
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            return _result_from_payload(json.loads(candidate))
        except json.JSONDecodeError:
            continue

    reason_parts = [f"Model subprocess exited with code {returncode}."]
    if stderr.strip():
        reason_parts.append(f"stderr: {stderr.strip()[-1200:]}")
    if stdout.strip():
        reason_parts.append(f"stdout: {stdout.strip()[-1200:]}")
    return ModelRunResult(
        ok=False,
        status="blocked_model_subprocess_failed",
        reason=" ".join(reason_parts),
    )


def generate_qwen_text_with_timeout(
    model_path: str | Path,
    prompt: str,
    max_new_tokens: int = 900,
    temperature: float = 0.3,
    enable_thinking: bool = False,
    timeout_seconds: int | float | None = 120,
) -> ModelRunResult:
    payload = {
        "model_path": str(Path(model_path).resolve()),
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
        "temperature": temperature,
        "enable_thinking": enable_thinking,
    }
    env = os.environ.copy()
    scripts_root = str(Path(__file__).resolve().parents[1])
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        scripts_root
        if not existing_pythonpath
        else scripts_root + os.pathsep + existing_pythonpath
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    python_cmd = _get_model_python_cmd()
    script_path = Path(__file__).parent.resolve() / "isolated_inference.py"

    process = subprocess.Popen(
        python_cmd + [str(script_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        stdout, stderr = process.communicate(
            input=json.dumps(payload),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        return ModelRunResult(
            ok=False,
            status="timeout_exceeded",
            reason=f"Model generation did not complete within {timeout_seconds} seconds",
        )

    return _decode_subprocess_result(stdout, stderr, process.returncode)

def generate_qwen_text(
    model_path: str | Path,
    prompt: str,
    max_new_tokens: int = 900,
    temperature: float = 0.3,
    enable_thinking: bool = False,
) -> ModelRunResult:
    return generate_qwen_text_with_timeout(
        model_path=model_path,
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        enable_thinking=enable_thinking,
        timeout_seconds=120,
    )
