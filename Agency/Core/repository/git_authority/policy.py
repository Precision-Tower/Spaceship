from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any


GIT_HISTORIAN_AND_REFEREE_PRINCIPLE = (
    "Git is CE-OS's historian and referee. CE-OS shall not persist as current "
    "truth anything Git can authoritatively answer at query time. CE-OS may "
    "persist immutable Git references and time-bounded Git observations as "
    "historical evidence."
)

GIT_AUTHORITY_BOUNDARY = "Git Authority Boundary"

DOMAIN_AUTHORITY = MappingProxyType({
    "mission": "Seth",
    "acceptance": "Seth",
    "play_direction": "Gear",
    "next_decision": "Gear",
    "ball_possession": "CE-OS",
    "route_execution": "Cali",
    "repository_contents": "Git",
    "repository_history": "Git",
    "repository_status": "Git",
    "branch_topology": "Git",
    "object_integrity": "Git",
})

TEMPORARY_DIRECT_GIT_EXCEPTIONS = MappingProxyType({
    "Agency/Core/capabilities/engineering/execution.py": "legacy engineering capability executor with injectable git apply runner; migrate in capabilities pass",
    "Agency/Core/work/missions/pipeline/implementation/execution.py": "legacy implementation executor drift checks; migrate in implementation-runtime pass",
    "Agency/Core/work/missions/mission_runtime.py": "legacy mission resourcefulness/status helper; migrate in mission-runtime pass",
})

ALLOWED_REFERENCE_FIELDS = frozenset({
    "repository_id",
    "repository_ref",
    "path",
    "path_ref",
    "commit_oid",
    "tree_oid",
    "blob_oid",
    "baseline_oid",
    "baseline_hashes",
    "before_hashes",
    "after_hashes",
    "proposal_sha256",
    "observation_id",
    "observed_at",
    "git_command",
    "git_exit_code",
    "output_sha256",
    "verification_results",
    "head_oid",
})

PROHIBITED_MUTABLE_GIT_STATE = frozenset({
    "currentbranch",
    "currenthead",
    "headcommit",
    "workingtreeclean",
    "repositoryclean",
    "stagedfiles",
    "unstagedfiles",
    "untrackedfiles",
    "changedfiles",
    "currentdiff",
    "commithistory",
    "mergebase",
    "branchtopology",
    "repositorystatus",
})

HISTORICAL_EVIDENCE_MARKERS = frozenset({
    "_git_authority_type",
    "observation_id",
    "observed_at",
    "git_command",
    "git_exit_code",
    "output_sha256",
})

HISTORICAL_EVIDENCE_CONTAINERS = frozenset({
    "verification_results",
    "git_observations",
    "historical_git_observations",
    "observations",
})


class GitPersistencePolicyError(ValueError):
    pass


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _is_historical_evidence_dict(value: dict[str, Any]) -> bool:
    if value.get("_git_authority_type") == "GitObservation":
        return True
    return bool(HISTORICAL_EVIDENCE_MARKERS.intersection(value.keys())) and "observed_at" in value


def _looks_like_repository_status_view(value: dict[str, Any]) -> bool:
    if value.get("_git_authority_type") == "RepositoryStatusView":
        return True
    keys = {_normalize_key(key) for key in value}
    required = {"repositoryid", "headoid", "detached", "stagedpaths", "unstagedpaths", "untrackedpaths", "conflicts", "clean"}
    return required.issubset(keys)


def _is_allowed_reference_key(key: str) -> bool:
    return key in ALLOWED_REFERENCE_FIELDS or _normalize_key(key) in {_normalize_key(item) for item in ALLOWED_REFERENCE_FIELDS}


def _is_prohibited_current_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in PROHIBITED_MUTABLE_GIT_STATE:
        return True
    if normalized.startswith("current") and ("branch" in normalized or "head" in normalized or "diff" in normalized):
        return True
    if "repository" in normalized and "clean" in normalized:
        return True
    if "workingtree" in normalized and "clean" in normalized:
        return True
    if normalized.endswith("files") and any(part in normalized for part in ("staged", "unstaged", "untracked", "changed")):
        return True
    return False


def ensure_git_persistence_allowed(payload: Any, *, record_name: str = "CE-OS record") -> None:
    """Reject CE-OS records that persist mutable Git state as current truth."""

    def visit(value: Any, path: tuple[str, ...], historical_context: bool = False) -> None:
        if isinstance(value, dict):
            current_key = path[-1] if path else ""
            if current_key in HISTORICAL_EVIDENCE_CONTAINERS:
                historical_context = True
            if _looks_like_repository_status_view(value):
                raise GitPersistencePolicyError(
                    f"{record_name}: RepositoryStatusView is a live Git query result and must not be persisted at {'.'.join(path) or '<root>'}"
                )
            if _is_historical_evidence_dict(value):
                historical_context = True
            for key, child in value.items():
                if key == "_git_authority_type":
                    continue
                if not historical_context and not _is_allowed_reference_key(key) and _is_prohibited_current_key(key):
                    raise GitPersistencePolicyError(
                        f"{record_name}: mutable Git state field '{key}' is prohibited at {'.'.join((*path, key))}"
                    )
                visit(child, (*path, str(key)), historical_context)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, (*path, str(index)), historical_context)

    visit(payload, ())
