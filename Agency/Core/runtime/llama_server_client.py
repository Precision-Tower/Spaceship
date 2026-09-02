from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Mapping

from Agency.Core.runtime.inference_policy import InferencePolicy, coerce_policy
from Agency.Core.runtime.runtime_config import load_model_server_config


def _runtime_url() -> str:
    config = load_model_server_config()
    endpoint = getattr(config, "endpoint", None)

    if not endpoint:
        raise RuntimeError("Configured llama-server runtime has no endpoint")

    return str(endpoint).rstrip("/")


def _post_json(endpoint: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    runtime_url = _runtime_url()
    url = f"{runtime_url}/{endpoint.lstrip('/')}"
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "status": "remote_unreachable",
            "node_url": runtime_url,
            "reason": str(exc),
        }


def _get_json(endpoint: str, timeout: int = 5) -> dict[str, Any]:
    runtime_url = _runtime_url()
    url = f"{runtime_url}/{endpoint.lstrip('/')}"

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "status": "remote_unreachable",
            "node_url": runtime_url,
            "reason": str(exc),
        }


def status() -> dict[str, Any]:
    runtime_url = _runtime_url()
    payload = _get_json("health")

    if payload.get("status") == "ok":
        return {
            "ok": True,
            "status": "healthy",
            "node_url": runtime_url,
            "backend": "llama.cpp",
            "raw": payload,
        }

    return payload


def chat_completion(
    messages: list[dict[str, str]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
    inference_policy: InferencePolicy | Mapping[str, Any] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    """Send an OpenAI-compatible chat-completion request to the resolved runtime."""
    if inference_policy is None:
        raise ValueError("inference_policy_required")

    policy = coerce_policy(inference_policy)
    # max_tokens and temperature remain accepted for older callers, but the
    # serialized request is governed by the upstream inference policy.
    request_max_tokens = int(policy["max_tokens"])
    request_temperature = float(policy["temperature"])
    enable_thinking = bool(policy["enable_thinking"])
    reasoning_effort = str(policy.get("reasoning_effort") or ("medium" if enable_thinking else "none"))

    return _post_json(
        "v1/chat/completions",
        {
            "messages": messages,
            "max_tokens": request_max_tokens,
            "temperature": request_temperature,
            "chat_template_kwargs": {
                "enable_thinking": enable_thinking,
            },
            "reasoning_effort": reasoning_effort,
        },
        timeout=timeout,
    )


def completion_diagnostics(raw: dict[str, Any]) -> dict[str, Any]:
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        return {
            "ok": False,
            "status": "malformed_response",
            "reason": "llama-server response did not contain choices",
            "content": "",
            "finish_reason": None,
        }

    first = choices[0]
    if not isinstance(first, dict):
        return {
            "ok": False,
            "status": "malformed_response",
            "reason": "llama-server choice was not an object",
            "content": "",
            "finish_reason": None,
        }

    finish_reason = first.get("finish_reason")
    message = first.get("message")
    if not isinstance(message, dict):
        return {
            "ok": False,
            "status": "malformed_response",
            "reason": "llama-server choice did not contain a message object",
            "content": "",
            "finish_reason": finish_reason,
        }

    content = message.get("content")
    if not isinstance(content, str):
        return {
            "ok": False,
            "status": "malformed_response",
            "reason": "llama-server message content was not text",
            "content": "",
            "finish_reason": finish_reason,
        }

    if finish_reason == "length":
        return {
            "ok": False,
            "status": "truncated_generation",
            "reason": "llama-server stopped because the completion token budget was exhausted",
            "content": content,
            "finish_reason": finish_reason,
        }

    if not content.strip():
        return {
            "ok": False,
            "status": "empty_response",
            "reason": "llama-server returned no visible assistant content",
            "content": content,
            "finish_reason": finish_reason,
        }

    return {
        "ok": True,
        "status": "completed",
        "reason": "",
        "content": content,
        "finish_reason": finish_reason,
    }


def ask(
    prompt: str,
    *,
    agent: str,
    max_tokens: int | None = None,
    system_context: str | None = None,
    inference_policy: InferencePolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if inference_policy is None:
        raise ValueError("inference_policy_required")

    policy = coerce_policy(inference_policy)
    messages: list[dict[str, str]] = []

    if system_context:
        messages.append({
            "role": "system",
            "content": system_context,
        })

    messages.append({
        "role": "user",
        "content": prompt,
    })

    raw = chat_completion(
        messages,
        max_tokens=max_tokens if max_tokens is not None else int(policy["max_tokens"]),
        temperature=float(policy["temperature"]),
        inference_policy=policy,
    )

    if raw.get("ok") is False:
        payload = dict(raw)
        payload.setdefault("agent", agent)
        payload.setdefault("inference_target", "local")
        payload.setdefault("runtime", "llama_server")
        payload.setdefault("backend", "llama.cpp")
        payload["inference_policy"] = policy
        return payload

    completion = completion_diagnostics(raw)
    response = completion["content"]

    return {
        "ok": completion["ok"],
        "status": completion["status"],
        "reason": completion["reason"],
        "agent": agent,
        "inference_target": "local",
        "runtime": "llama_server",
        "backend": "llama.cpp",
        "draft": response,
        "response": response,
        "model": raw.get("model"),
        "usage": raw.get("usage"),
        "timings": raw.get("timings"),
        "finish_reason": completion["finish_reason"],
        "completion_status": completion["status"],
        "inference_policy": policy,
        "raw": raw,
    }


def read(path: str) -> dict[str, Any]:
    return _post_json("file/read", {"path": path})


def write(path: str, content: str) -> dict[str, Any]:
    return _post_json("file/write", {
        "path": path,
        "content": content,
    })
