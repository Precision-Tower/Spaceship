from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class GitAuthorityError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass(frozen=True)
class RepositoryRef:
    repository_id: str
    root_path: str

    @property
    def root(self) -> Path:
        return Path(self.root_path)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GitObjectRef:
    repository_id: str
    oid: str
    object_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GitPathRef:
    repository_id: str
    path: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GitObservation:
    observation_id: str
    repository_id: str
    observed_at: str
    git_command: tuple[str, ...]
    git_exit_code: int
    stdout: str
    stderr: str
    output_sha256: str
    head_oid: str | None = None
    timeout_seconds: int | None = None

    @classmethod
    def build(
        cls,
        *,
        repository_id: str,
        observed_at: str,
        git_command: tuple[str, ...],
        git_exit_code: int,
        stdout: str,
        stderr: str,
        head_oid: str | None = None,
        timeout_seconds: int | None = None,
    ) -> "GitObservation":
        digest = hashlib.sha256((stdout + "\n---stderr---\n" + stderr).encode("utf-8", errors="replace")).hexdigest()
        seed = f"{repository_id}|{observed_at}|{' '.join(git_command)}|{git_exit_code}|{digest}"
        observation_id = "gitobs-" + hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:16]
        return cls(
            observation_id=observation_id,
            repository_id=repository_id,
            observed_at=observed_at,
            git_command=git_command,
            git_exit_code=git_exit_code,
            stdout=stdout,
            stderr=stderr,
            output_sha256=digest,
            head_oid=head_oid,
            timeout_seconds=timeout_seconds,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["_git_authority_type"] = "GitObservation"
        data["git_command"] = list(self.git_command)
        return data


@dataclass(frozen=True)
class RepositoryStatusView:
    repository_id: str
    head_oid: str | None
    branch: str | None
    detached: bool
    staged_paths: tuple[str, ...]
    unstaged_paths: tuple[str, ...]
    untracked_paths: tuple[str, ...]
    conflicts: tuple[str, ...]
    clean: bool
    observation: GitObservation

    def to_dict(self) -> dict[str, Any]:
        return {
            "_git_authority_type": "RepositoryStatusView",
            "repository_id": self.repository_id,
            "head_oid": self.head_oid,
            "branch": self.branch,
            "detached": self.detached,
            "staged_paths": list(self.staged_paths),
            "unstaged_paths": list(self.unstaged_paths),
            "untracked_paths": list(self.untracked_paths),
            "conflicts": list(self.conflicts),
            "clean": self.clean,
            "observation": self.observation.to_dict(),
        }
