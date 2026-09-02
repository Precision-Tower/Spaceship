from __future__ import annotations

from typing import Any

from Agency.Core.runtime.llama_server_client import ask as llama_server_ask


def ask(
    prompt: str,
    *,
    agent_name: str,
    system_context: str = "",
    max_new_tokens: int = 256,
    runtime: str = "llama_server",
    inference_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_runtime = str(runtime or "").strip().lower()
    if normalized_runtime == "llama_server":
        combined_prompt = f"""
        You are answering from LOCAL CONTEXT only.

        Important:
        - "Recent short-term memory" counts as loaded memory.
        - Ignore "No retrieved memory results" if Recent short-term memory contains entries.
        - Do not say you cannot access context. The context is below.

        LOCAL CONTEXT:
        {system_context}

        USER QUESTION:
        {prompt}

        Answer directly from Recent short-term memory when relevant.
        """

        result = llama_server_ask(
            combined_prompt,
            agent=agent_name,
            max_tokens=max_new_tokens,
            inference_policy=inference_policy,
        )

        return {
            "authority": "remote_model_draft_not_truth",
            "runtime": "llama_server",
            "backend": "llama_server",
            "ok": bool(result.get("ok")),
            "status": result.get("status", "remote_response"),
            "reason": result.get("reason", ""),
            "draft": result.get("draft", ""),
            "finish_reason": result.get("finish_reason"),
            "completion_status": result.get("completion_status"),
            "inference_policy": result.get("inference_policy") or inference_policy,
            "remote": result,
            "max_new_tokens": max_new_tokens,
        }

    raise ValueError(f"unsupported_runtime: {runtime}")
