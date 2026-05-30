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


_SUBPROCESS_RUNNER_CODE = r"""
import json
import sys

payload = json.loads(sys.stdin.read())

try:
    from runtime.model_runner import generate_qwen_text

    result = generate_qwen_text(
        model_path=payload["model_path"],
        prompt=payload["prompt"],
        max_new_tokens=payload["max_new_tokens"],
        temperature=payload["temperature"],
        enable_thinking=payload["enable_thinking"],
    )
    response = {
        "ok": result.ok,
        "status": result.status,
        "text": result.text,
        "reason": result.reason,
    }
except BaseException as exc:
    response = {
        "ok": False,
        "status": "blocked_model_subprocess_error",
        "text": "",
        "reason": f"{type(exc).__name__}: {exc}",
    }

print(json.dumps(response), flush=True)
"""


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
    timeout_seconds: int | float = 120,
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

    process = subprocess.Popen(
        [sys.executable, "-c", _SUBPROCESS_RUNNER_CODE],
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
    model_dir = Path(model_path).resolve()
    if not model_available(model_dir):
        return ModelRunResult(
            ok=False,
            status="blocked_model_not_found",
            reason=f"Local model config not found at {model_dir}",
        )

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:
        return ModelRunResult(
            ok=False,
            status="blocked_model_dependency_unavailable",
            reason=f"{type(exc).__name__}: {exc}",
        )

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir),
            local_files_only=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            str(model_dir),
            torch_dtype="auto",
            device_map="auto",
            local_files_only=True,
        )
    except Exception as exc:
        return ModelRunResult(
            ok=False,
            status="blocked_model_load_failed",
            reason=f"{type(exc).__name__}: {exc}",
        )

    messages = [{"role": "user", "content": prompt}]
    try:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=enable_thinking,
        )
    except TypeError:
        try:
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            text = prompt
    except Exception:
        text = prompt

    try:
        model_inputs = tokenizer([text], return_tensors="pt")
        try:
            model_inputs = model_inputs.to(model.device)
        except Exception:
            pass

        model.eval()
        generate_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": temperature > 0,
            "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
        }
        if temperature > 0:
            generate_kwargs["temperature"] = temperature
            generate_kwargs["top_p"] = 0.9

        generated_ids = model.generate(**model_inputs, **generate_kwargs)
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
        try:
            think_end = len(output_ids) - output_ids[::-1].index(151668)
        except ValueError:
            think_end = 0
        output = tokenizer.decode(
            output_ids[think_end:],
            skip_special_tokens=True,
        ).strip()
    except Exception as exc:
        return ModelRunResult(
            ok=False,
            status="blocked_model_generation_failed",
            reason=f"{type(exc).__name__}: {exc}",
        )

    if not output:
        return ModelRunResult(
            ok=False,
            status="blocked_empty_model_output",
            reason="Model generation completed but returned no decoded text.",
        )

    return ModelRunResult(ok=True, status="generated", text=output)
