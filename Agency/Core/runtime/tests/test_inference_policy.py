from __future__ import annotations

import unittest
from unittest.mock import patch

from Agency.Core.runtime.inference_policy import (
    select_inference_policy,
)


class InferencePolicyTests(unittest.TestCase):
    def test_exact_response_disables_thinking_and_uses_small_budget(self) -> None:
        policy = select_inference_policy(
            "Reply with exactly: EDITOR_4B_OK",
            requested_max_tokens=192,
        )

        self.assertEqual("exact_response", policy.route)
        self.assertTrue(policy.requires_model)
        self.assertFalse(policy.allow_authoritative_state)
        self.assertFalse(policy.enable_thinking)
        self.assertEqual("none", policy.reasoning_effort)
        self.assertEqual(32, policy.max_tokens)

    def test_rewrite_disables_thinking_and_authoritative_interception(self) -> None:
        policy = select_inference_policy(
            "Rewrite this sentence for clarity: The runtime should load the model based on the environment.",
            context_route="action_request",
            requested_max_tokens=192,
        )

        self.assertEqual("rewrite", policy.route)
        self.assertTrue(policy.requires_model)
        self.assertFalse(policy.allow_authoritative_state)
        self.assertFalse(policy.enable_thinking)
        self.assertEqual("none", policy.reasoning_effort)

    def test_analytical_routes_enable_thinking_with_sufficient_budget(self) -> None:
        policy = select_inference_policy(
            "Review Agency/Core/runtime/llama_server_client.py and identify concrete failure modes.",
            context_route="code_question",
            requested_max_tokens=192,
            configured_reasoning_tokens=192,
        )

        self.assertEqual("code_question", policy.route)
        self.assertTrue(policy.enable_thinking)
        self.assertEqual("medium", policy.reasoning_effort)
        self.assertGreaterEqual(policy.max_tokens, 1024)

    def test_patch_policy_uses_configured_patch_budget(self) -> None:
        policy = select_inference_policy(
            "Produce a unified diff for Agency/Core/runtime/llama_server_client.py",
            context_route="code_question",
            requested_max_tokens=192,
            configured_reasoning_tokens=1024,
            configured_patch_tokens=1024,
            patch_recommendation_mode=True,
        )

        self.assertEqual("patch_recommendation", policy.route)
        self.assertTrue(policy.enable_thinking)
        self.assertEqual(1024, policy.max_tokens)
        self.assertIn("patch_contract", policy.completion_validation)

    def test_authoritative_policy_requires_no_model(self) -> None:
        policy = select_inference_policy(
            "What environment is this agent running in?",
            authoritative_topic="environment",
        )

        self.assertEqual("authoritative_state:environment", policy.route)
        self.assertFalse(policy.requires_model)
        self.assertFalse(policy.enable_thinking)
        self.assertEqual(0, policy.max_tokens)


class CodeReasonerCompatibilityTests(unittest.TestCase):
    def test_generate_convenience_entry_point_selects_explicit_policy(self) -> None:
        from Agency.Core.runtime.reasoners.gguf import CodeReasoner, GGUFRunResult

        reasoner = CodeReasoner("model.gguf")
        with patch.object(
            CodeReasoner,
            "generate_result",
            return_value=GGUFRunResult(ok=True, status="draft_generated", text="OK"),
        ) as generate_result:
            text = reasoner.generate("", "Reply with exactly: OK", max_new_tokens=32)

        self.assertEqual("OK", text)
        policy = generate_result.call_args.kwargs["inference_policy"]
        self.assertEqual("exact_response", policy.route)
        self.assertFalse(policy.enable_thinking)


if __name__ == "__main__":
    unittest.main()
