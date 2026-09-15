"""CodeGo command executor.

Pure-local bash execution. The old CodeGo POSTed commands to an HTTP
bridge on 127.0.0.1:8787; that bridge is gone. This module runs the
command directly via subprocess and returns a structured result.
"""

import subprocess

import config


def extract_block(text):
    """Pull the first %%VOC%%..%%VOC%% block out of `text`.

    Returns the inner command string with surrounding whitespace
    stripped, or None if no complete block is present.
    """
    if not text:
        return None

    lines = text.splitlines()
    capturing = False
    captured = []

    for line in lines:
        stripped = line.strip()
        if stripped == config.VOC_MARKER:
            if capturing:
                block = "\n".join(captured).strip()
                return block if block else None
            capturing = True
            captured = []
            continue
        if capturing:
            captured.append(line)

    # Unterminated block -- treat as no block.
    return None


def is_stop(text):
    """True if the model's reply contains the STOP_SYSTEM marker."""
    if not text:
        return False
    return config.STOP_SYSTEM in text


def run_bash(cmd, cwd=None, timeout=config.BASH_TIMEOUT_SEC):
    """Run `cmd` as a bash script and return a result dict.

    Keys:
      stdout    -- captured standard output (str)
      stderr    -- captured standard error (str)
      exit_code -- process exit status (int, or -1 for timeout)
    """
    result = {"stdout": "", "stderr": "", "exit_code": 0}

    if not cmd or not cmd.strip():
        return result

    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result["stdout"] = proc.stdout or ""
        result["stderr"] = proc.stderr or ""
        result["exit_code"] = proc.returncode
    except subprocess.TimeoutExpired as e:
        result["stdout"] = (e.stdout or "") if isinstance(e.stdout, str) else ""
        result["stderr"] = "TIMEOUT after {}s".format(timeout)
        result["exit_code"] = -1
    except Exception as e:
        result["stderr"] = "EXECUTOR ERROR: {}".format(e)
        result["exit_code"] = -1

    return result


def format_output(result):
    """Render a run_bash result as a single trimmed string.

    stdout comes first, then stderr. Empty sections are skipped.
    An exit code line is appended when the command did not succeed,
    so the model always knows whether it should trust the output.
    """
    parts = []

    stdout = (result.get("stdout") or "").strip()
    stderr = (result.get("stderr") or "").strip()

    if stdout:
        parts.append(stdout)
    if stderr:
        parts.append(stderr)

    body = "\n".join(parts).strip()

    code = result.get("exit_code", 0)
    if code != 0:
        tail = "[exit_code={}]".format(code)
        body = (body + "\n" + tail).strip() if body else tail

    if not body:
        body = "(command produced no output)"

    return body
