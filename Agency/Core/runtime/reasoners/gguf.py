from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from pathlib import Path
from Agency.Core.runtime.inference_policy import (
    InferencePolicy,
    health_check_policy,
    select_inference_policy,
)
from Agency.Core.runtime.llama_server_client import chat_completion, completion_diagnostics


AUTHORITY = "draft_generation_only_not_truth"


@dataclass(frozen=True)
class GGUFRunResult:
    ok: bool
    status: str
    authority: str = AUTHORITY
    text: str = ""
    reason: str = ""
    model_path: str = ""
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    completion_status: str | None = None
    inference_policy: dict[str, Any] | None = None


class CodeReasoner:
    def __init__(self, model_path: str | Path):
        self.model_path = str(Path(model_path).expanduser())

    def load_result(self) -> GGUFRunResult:
        policy = health_check_policy()
        raw = chat_completion(
            [
                {"role": "system", "content": "Health check."},
                {"role": "user", "content": "Say OK only."},
            ],
            max_tokens=policy.max_tokens,
            temperature=policy.temperature,
            inference_policy=policy,
            timeout=10,
        )

        if raw.get("ok") is False:
            return GGUFRunResult(
                ok=False,
                status="ExpectedFailure",
                reason=(
                    "llama-server unavailable: "
                    f"{raw.get('reason', raw.get('status', 'unknown failure'))}"
                ),
                model_path=self.model_path,
            )

        return GGUFRunResult(
            ok=True,
            status="loaded",
            model_path=self.model_path,
            usage={"backend": "llama_server_chat"},
        )

    def load(self) -> bool:
        return self.load_result().ok

    def generate_result(
        self,
        system_context: str,
        user_prompt: str,
        max_new_tokens: int = 192,
        inference_policy: InferencePolicy | dict[str, Any] | None = None,
    ) -> GGUFRunResult:
        if inference_policy is None:
            raise ValueError("inference_policy_required")

        policy_payload = (
            inference_policy.to_dict()
            if isinstance(inference_policy, InferencePolicy)
            else dict(inference_policy)
        )
        data = chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        system_context.strip()
                        or "You are a local Dashboard draft generator."
                    ),
                },
                {
                    "role": "user",
                    "content": user_prompt.strip(),
                },
            ],
            max_tokens=max_new_tokens,
            temperature=float(policy_payload.get("temperature", 0.3)),
            inference_policy=policy_payload,
            timeout=180,
        )

        if data.get("ok") is False:
            return GGUFRunResult(
                ok=False,
                status="ExpectedFailure",
                reason=(
                    "llama-server request failed: "
                    f"{data.get('reason', data.get('status', 'unknown failure'))}"
                ),
                model_path=self.model_path,
            )

        completion = completion_diagnostics(data)
        text = str(completion.get("content") or "").strip()

        return GGUFRunResult(
            ok=bool(completion["ok"]),
            status="draft_generated" if completion["ok"] else str(completion["status"]),
            text=text,
            reason=str(completion.get("reason") or ""),
            model_path=self.model_path,
            usage={
                "backend": "llama_server_chat",
                "raw_usage": data.get("usage", {}),
                "timings": data.get("timings", {}),
            },
            finish_reason=completion.get("finish_reason"),
            completion_status=str(completion["status"]),
            inference_policy=policy_payload,
        )

    def generate(
        self,
        system_context: str,
        user_prompt: str,
        max_new_tokens: int = 192,
    ) -> str:
        policy = select_inference_policy(
            user_prompt,
            requested_max_tokens=max_new_tokens,
        )
        result = self.generate_result(
            system_context,
            user_prompt,
            max_new_tokens,
            inference_policy=policy,
        )
        if result.ok:
            return result.text
        return f"{result.status}: {result.reason}"
