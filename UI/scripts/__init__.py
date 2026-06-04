"""
Core System Package.

Unified public interface for agents, CLI, and runtime.
"""

from . import agents
from . import cli
from . import runtime

__version__ = "2.0.0"

__all__ = ["agents", "cli", "runtime"]