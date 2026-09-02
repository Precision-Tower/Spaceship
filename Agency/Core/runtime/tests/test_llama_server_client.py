from __future__ import annotations

import unittest
from unittest.mock import patch

from Agency.Core.runtime import llama_server_client as client
from Agency.Core.runtime.inference_policy import select_inference_policy


class LlamaServerClientTests(unittest.TestCase):
    def test_chat_completion_serializes_non_thinking_policy(self) -> None:
        policy = select_inference_policy(
            "Reply with exactly: OK",
            requested_max_tokens=192,
        )

        with patch.object(client, "_post_json", return_value={"choices": []}) as posted:
            client.chat_completion(
                [{"role": "user", "content": "Reply with exactly: OK"}],
                inference_policy=policy,
            )

        _endpoint, payload = posted.call_args.args[:2]
        self.assertEqual(32, payload["max_tokens"])
        self.assertEqual(0.0, payload["temperature"])
        self.assertEqual({"enable_thinking": False}, payload["chat_template_kwargs"])
        self.assertEqual("none", payload["reasoning_effort"])

    def test_chat_completion_serializes_thinking_policy(self) -> None:
        policy = select_inference_policy(
            "Review Agency/Core/runtime/llama_server_client.py",
            context_route="code_question",
            configured_reasoning_tokens=768,
        )

        with patch.object(client, "_post_json", return_value={"choices": []}) as posted:
            client.chat_completion(
                [{"role": "user", "content": "Review a file"}],
                inference_policy=policy,
            )

        _endpoint, payload = posted.call_args.args[:2]
        self.assertEqual(1024, payload["max_tokens"])
        self.assertEqual({"enable_thinking": True}, payload["chat_template_kwargs"])
        self.assertEqual("medium", payload["reasoning_effort"])

    def test_chat_completion_requires_explicit_policy(self) -> None:
        with self.assertRaisesRegex(ValueError, "inference_policy_required"):
            client.chat_completion([{"role": "user", "content": "hello"}])

    def test_chat_completion_uses_policy_over_legacy_arguments(self) -> None:
        policy = select_inference_policy("Reply with exactly: OK")

        with patch.object(client, "_post_json", return_value={"choices": []}) as posted:
            client.chat_completion(
                [{"role": "user", "content": "Reply with exactly: OK"}],
                max_tokens=999,
                temperature=1.0,
                inference_policy=policy,
            )

        _endpoint, payload = posted.call_args.args[:2]
        self.assertEqual(32, payload["max_tokens"])
        self.assertEqual(0.0, payload["temperature"])

    def test_empty_length_completion_is_truncated_not_success(self) -> None:
        raw = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": ""},
                }
            ]
        }

        payload = client.completion_diagnostics(raw)

        self.assertFalse(payload["ok"])
        self.assertEqual("truncated_generation", payload["status"])
        self.assertEqual("length", payload["finish_reason"])

    def test_nonempty_length_completion_is_not_marked_successful(self) -> None:
        raw = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": "partial"},
                }
            ]
        }

        payload = client.completion_diagnostics(raw)

        self.assertFalse(payload["ok"])
        self.assertEqual("truncated_generation", payload["status"])
        self.assertEqual("partial", payload["content"])

    def test_empty_stop_completion_is_empty_response(self) -> None:
        raw = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "  "},
                }
            ]
        }

        payload = client.completion_diagnostics(raw)

        self.assertFalse(payload["ok"])
        self.assertEqual("empty_response", payload["status"])

    def test_malformed_response_is_not_success(self) -> None:
        payload = client.completion_diagnostics({"unexpected": True})

        self.assertFalse(payload["ok"])
        self.assertEqual("malformed_response", payload["status"])

    def test_ask_promotes_completion_metadata(self) -> None:
        policy = select_inference_policy("Reply with exactly: OK")
        raw = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "OK"},
                }
            ],
            "model": "test-model",
            "usage": {"completion_tokens": 1},
        }
        with patch.object(client, "chat_completion", return_value=raw):
            payload = client.ask("Reply with exactly: OK", agent="Editor", inference_policy=policy)

        self.assertTrue(payload["ok"])
        self.assertEqual("completed", payload["completion_status"])
        self.assertEqual("stop", payload["finish_reason"])
        self.assertEqual("exact_response", payload["inference_policy"]["route"])


if __name__ == "__main__":
    unittest.main()
