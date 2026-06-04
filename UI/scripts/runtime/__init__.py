"""
Runtime support package.

Active runtime interfaces:
- model_runner
- agent_registry

Legacy runtime modules have been moved to runtime/old.
"""

from .model_runner import generate_qwen_text, generate_qwen_text_with_timeout
from .agent_registry import normalized_agent_registry

__all__ = [
    "generate_qwen_text",
    "generate_qwen_text_with_timeout",
    "normalized_agent_registry",
]