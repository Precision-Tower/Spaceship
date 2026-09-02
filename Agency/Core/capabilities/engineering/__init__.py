"""
Shared engineering capability for factory-created agents.

This package is the canonical destination for engineering behavior currently
owned by the historical agent implementation.

Migration invariant:
    No behavior is considered extracted until its legacy agent implementation
    has been deleted and callers use this package directly.
"""

from Agency.Core.capabilities.engineering.capability import (
    ENGINEERING_CAPABILITY,
)

__all__ = ["ENGINEERING_CAPABILITY"]
