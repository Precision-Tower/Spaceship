from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


EXACT_RESPONSE_RE = re.compile(
    r"^\s*(?:respond|reply|return|output)\s+with\s+exactly:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)

_TEXT_TRANSFORM_RE = re.compile(
    r"^\s*(?:please\s+)?(?:rewrite|rephrase|revise|edit|proofread|polish|clarify|improve)\b",
    re.IGNORECASE,
)
_MAKE_CLEAR_RE = re.compile(
    r"^\s*(?:please\s+)?make\s+(?:this|the)\s+(?:sentence|text|paragraph)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InferencePolicy:
    route: str
    requires_model: bool
    allow_authoritative_state: bool
    enable_thinking: bool
    max_tokens: int
    temperature: float
    output_contract: str
    completion_validation: tuple[str, ...]
    reasoning_effort: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["completion_validation"] = list(self.completion_validation)
        return payload


def coerce_policy(policy: InferencePolicy | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(policy, InferencePolicy):
        return policy.to_dict()
    if isinstance(policy, Mapping):
        required = {
            "route",
            "requires_model",
            "allow_authoritative_state",
            "enable_thinking",
            "max_tokens",
            "temperature",
            "output_contract",
            "completion_validation",
            "reasoning_effort",
            "reason",
        }
        missing = sorted(required - set(policy))
        if missing:
            raise ValueError(f"inference_policy_missing_fields: {', '.join(missing)}")
        payload = dict(policy)
        payload["completion_validation"] = list(payload.get("completion_validation") or [])
        return payload
    raise TypeError(f"unsupported_inference_policy: {type(policy).__name__}")


def exact_response_text(prompt: str) -> str | None:
    match = EXACT_RESPONSE_RE.match(str(prompt or ""))
    if not match:
        return None
    exact = match.group("text").strip()
    if len(exact) >= 2 and exact[0] == exact[-1] and exact[0] in {"'", '"'}:
        exact = exact[1:-1].strip()
    return exact or None


def is_text_transform_request(prompt: str) -> bool:
    text = str(prompt or "").strip()
    if not text:
        return False
    prefix = text.split(":", 1)[0]
    return bool(_TEXT_TRANSFORM_RE.search(prefix) or _MAKE_CLEAR_RE.search(prefix))


def _bounded(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def _thinking_budget(
    requested_max_tokens: int,
    configured_reasoning_tokens: int,
    configured_patch_tokens: int,
    *,
    patch: bool = False,
) -> int:
    floor = 1024
    configured = max(configured_reasoning_tokens, configured_patch_tokens if patch else 0)
    return max(requested_max_tokens, configured, floor)


def select_inference_policy(
    prompt: str,
    *,
    context_route: str = "general",
    requested_max_tokens: int = 192,
    configured_reasoning_tokens: int = 192,
    configured_patch_tokens: int = 512,
    patch_recommendation_mode: bool = False,
    authoritative_topic: str | None = None,
) -> InferencePolicy:
    if authoritative_topic:
        return InferencePolicy(
            route=f"authoritative_state:{authoritative_topic}",
            requires_model=False,
            allow_authoritative_state=True,
            enable_thinking=False,
            max_tokens=0,
            temperature=0.0,
            output_contract="authoritative_state",
            completion_validation=("authoritative_state_available",),
            reasoning_effort="none",
            reason="authoritative_state_intent",
        )

    if context_route == "identity":
        return InferencePolicy(
            route="identity",
            requires_model=False,
            allow_authoritative_state=True,
            enable_thinking=False,
            max_tokens=0,
            temperature=0.0,
            output_contract="runtime_identity",
            completion_validation=("runtime_identity_available",),
            reasoning_effort="none",
            reason="identity_answer_from_runtime_state",
        )

    if exact_response_text(prompt) is not None:
        return InferencePolicy(
            route="exact_response",
            requires_model=True,
            allow_authoritative_state=False,
            enable_thinking=False,
            max_tokens=_bounded(requested_max_tokens, 1, 32),
            temperature=0.0,
            output_contract="exact_visible_text",
            completion_validation=("visible_content", "finish_reason_not_length"),
            reasoning_effort="none",
            reason="exact_response_requires_small_deterministic_completion",
        )

    if is_text_transform_request(prompt):
        return InferencePolicy(
            route="rewrite",
            requires_model=True,
            allow_authoritative_state=False,
            enable_thinking=False,
            max_tokens=max(requested_max_tokens, 160),
            temperature=0.2,
            output_contract="rewritten_text",
            completion_validation=("visible_content", "finish_reason_not_length"),
            reasoning_effort="none",
            reason="text_transformation_should_not_query_authoritative_state",
        )

    if patch_recommendation_mode:
        return InferencePolicy(
            route="patch_recommendation",
            requires_model=True,
            allow_authoritative_state=False,
            enable_thinking=True,
            max_tokens=_thinking_budget(
                requested_max_tokens,
                configured_reasoning_tokens,
                configured_patch_tokens,
                patch=True,
            ),
            temperature=0.2,
            output_contract="fenced_unified_diff",
            completion_validation=("visible_content", "finish_reason_not_length", "patch_contract"),
            reasoning_effort="medium",
            reason="patch_recommendation_requires_analysis_and_sufficient_visible_budget",
        )

    if context_route in {"code_question", "architecture", "action_request"}:
        return InferencePolicy(
            route=context_route,
            requires_model=True,
            allow_authoritative_state=False,
            enable_thinking=True,
            max_tokens=_thinking_budget(
                requested_max_tokens,
                configured_reasoning_tokens,
                configured_patch_tokens,
            ),
            temperature=0.3,
            output_contract="analysis_draft",
            completion_validation=("visible_content", "finish_reason_not_length"),
            reasoning_effort="medium",
            reason=f"{context_route}_benefits_from_reasoning_policy",
        )

    if context_route == "workspace_status":
        return InferencePolicy(
            route="workspace_status",
            requires_model=True,
            allow_authoritative_state=False,
            enable_thinking=False,
            max_tokens=max(requested_max_tokens, 160),
            temperature=0.2,
            output_contract="workspace_status_draft",
            completion_validation=("visible_content", "finish_reason_not_length"),
            reasoning_effort="none",
            reason="workspace_status_prefers_direct_non_reasoning_summary",
        )

    return InferencePolicy(
        route="short_direct_answer",
        requires_model=True,
        allow_authoritative_state=True,
        enable_thinking=False,
        max_tokens=max(requested_max_tokens, 192),
        temperature=0.3,
        output_contract="direct_answer",
        completion_validation=("visible_content", "finish_reason_not_length"),
        reasoning_effort="none",
        reason="general_request_defaults_to_non_reasoning_direct_answer",
    )


def health_check_policy() -> InferencePolicy:
    return InferencePolicy(
        route="health_check",
        requires_model=True,
        allow_authoritative_state=False,
        enable_thinking=False,
        max_tokens=4,
        temperature=0.0,
        output_contract="health_token",
        completion_validation=("visible_content", "finish_reason_not_length"),
        reasoning_effort="none",
        reason="health_check_requires_minimal_visible_output",
    )
