from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class InlineError(Exception):
    pass


def qps_binary() -> str:
    env_qps = os.environ.get("QPS")
    if env_qps:
        candidate = Path(env_qps).expanduser()
        if candidate.is_file():
            return str(candidate)

    repo_root = Path(__file__).resolve().parents[2]
    repo_qps = repo_root / "qps" / "cpp" / "build-pixel" / "qps"
    if repo_qps.is_file():
        return str(repo_qps)

    path_qps = shutil.which("qps")
    if path_qps:
        return path_qps

    raise InlineError("qps executable not found")


def extract_source(surface: str) -> str:
    if not surface.startswith("[<"):
        raise InlineError("QPS Inline must begin with [<")

    quote = False
    escape = False
    bracket_depth = 0
    paren_depth = 0
    brace_depth = 0
    index = 2

    while index < len(surface):
        char = surface[index]

        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                quote = False
            index += 1
            continue

        if char == '"':
            quote = True
            index += 1
            continue

        if char == "(":
            paren_depth += 1
        elif char == ")":
            if paren_depth > 0:
                paren_depth -= 1
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            if brace_depth > 0:
                brace_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            if bracket_depth > 0:
                bracket_depth -= 1
            elif paren_depth == 0 and brace_depth == 0:
                trailing = surface[index + 1 :]
                if trailing.strip():
                    raise InlineError(
                        "unexpected text after QPS Inline closing ]"
                    )
                return surface[2:index]

        index += 1

    if quote:
        raise InlineError("unterminated string in QPS Inline")

    raise InlineError("QPS Inline is missing closing ]")


def execute(surface: str) -> int:
    source = extract_source(surface)
    cwd = Path.cwd()
    qps = qps_binary()

    fd, name = tempfile.mkstemp(
        prefix=".qps-inline-",
        suffix=".qps",
        dir=cwd,
        text=True,
    )
    transient = Path(name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(source)
            if source and not source.endswith("\n"):
                handle.write("\n")

        result = subprocess.run(
            [qps, str(transient)],
            cwd=cwd,
            check=False,
        )

        return int(result.returncode)
    finally:
        try:
            transient.unlink()
        except FileNotFoundError:
            pass
