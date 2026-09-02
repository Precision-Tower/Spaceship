from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from Agency.Core.repository.git_authority.contracts import GitAuthorityError, GitObservation, RepositoryRef
from Agency.Core.foundation.paths import DASHBOARD_ROOT


DEFAULT_TIMEOUT_SECONDS = 30


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_id(root: Path) -> str:
    resolved = root.resolve()
    return "gitrepo-" + __import__("hashlib").sha256(str(resolved).encode("utf-8", errors="replace")).hexdigest()[:16]


def _run_git_raw(root: Path, args: list[str], *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    if not root.exists():
        raise GitAuthorityError("repository_missing", f"Repository root does not exist: {root}", {"root": str(root)})
    if not root.is_dir():
        raise GitAuthorityError("repository_root_not_directory", f"Repository root is not a directory: {root}", {"root": str(root)})
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitAuthorityError(
            "git_command_timeout",
            f"Git command timed out after {timeout}s",
            {"command": ["git", *args], "timeout_seconds": timeout, "stdout": exc.stdout, "stderr": exc.stderr},
        ) from exc
    except FileNotFoundError as exc:
        raise GitAuthorityError("git_executable_missing", "Git executable was not found.", {"command": ["git", *args]}) from exc


def repository_ref(root: str | Path | None = None) -> RepositoryRef:
    requested = Path(root) if root is not None else DASHBOARD_ROOT
    resolved = requested.resolve()
    proc = _run_git_raw(resolved, ["rev-parse", "--show-toplevel"], timeout=10)
    if proc.returncode != 0:
        raise GitAuthorityError(
            "not_git_repository",
            f"Path is not a Git repository: {resolved}",
            {"root": str(resolved), "stderr": proc.stderr.strip()},
        )
    git_root = Path(proc.stdout.strip()).resolve()
    return RepositoryRef(repository_id=_repo_id(git_root), root_path=str(git_root))


def run_git_observation(repository: RepositoryRef, args: list[str], *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> GitObservation:
    if not args or any(not isinstance(arg, str) for arg in args):
        raise GitAuthorityError("invalid_git_arguments", "Git arguments must be a non-empty list of strings.", {"args": args})
    root = repository.root.resolve()
    observed_at = now_utc()
    head_oid = None
    if args[:2] != ["rev-parse", "HEAD"]:
        try:
            head_proc = _run_git_raw(root, ["rev-parse", "HEAD"], timeout=10)
            if head_proc.returncode == 0:
                head_oid = head_proc.stdout.strip() or None
        except GitAuthorityError:
            head_oid = None
    proc = _run_git_raw(root, args, timeout=timeout)
    return GitObservation.build(
        repository_id=repository.repository_id,
        observed_at=observed_at,
        git_command=("git", *args),
        git_exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        head_oid=head_oid,
        timeout_seconds=timeout,
    )


def check_patch(repository: RepositoryRef, patch_path: str | Path, *, timeout: int = 60) -> GitObservation:
    return run_git_observation(repository, ["apply", "--check", str(Path(patch_path))], timeout=timeout)


def apply_patch(repository: RepositoryRef, patch_path: str | Path, *, timeout: int = 60) -> GitObservation:
    return run_git_observation(repository, ["apply", str(Path(patch_path))], timeout=timeout)


def diff_check(repository: RepositoryRef, *, timeout: int = 60) -> GitObservation:
    return run_git_observation(repository, ["diff", "--check"], timeout=timeout)


def status_short(repository: RepositoryRef, *, timeout: int = 30) -> GitObservation:
    return run_git_observation(repository, ["status", "--short"], timeout=timeout)
