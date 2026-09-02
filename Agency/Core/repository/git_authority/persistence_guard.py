from __future__ import annotations

from typing import Any

from Agency.Core.repository.git_authority.policy import GitPersistencePolicyError, ensure_git_persistence_allowed


def guard_ceos_persistence(payload: Any, *, record_name: str = "CE-OS record") -> None:
    ensure_git_persistence_allowed(payload, record_name=record_name)


__all__ = ["GitPersistencePolicyError", "guard_ceos_persistence"]
