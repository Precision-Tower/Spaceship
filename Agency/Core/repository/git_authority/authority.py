from __future__ import annotations

from pathlib import Path

from Agency.Core.repository.git_authority.commands import run_git_observation
from Agency.Core.repository.git_authority.contracts import GitAuthorityError, GitObjectRef, GitPathRef, RepositoryRef, RepositoryStatusView
from Agency.Core.repository.git_authority.commands import repository_ref


def normalize_repo_path(repository: RepositoryRef, path: str | Path) -> GitPathRef:
    root = repository.root.resolve()
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        rel = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise GitAuthorityError("path_outside_repository", f"Path escapes repository root: {path}", {"path": str(path), "root": str(root)}) from exc
    return GitPathRef(repository_id=repository.repository_id, path=rel)


def get_head(repository: RepositoryRef) -> GitObjectRef:
    observation = run_git_observation(repository, ["rev-parse", "HEAD"], timeout=10)
    if observation.git_exit_code != 0:
        raise GitAuthorityError("head_unavailable", "Git HEAD could not be resolved.", {"stderr": observation.stderr})
    return GitObjectRef(repository_id=repository.repository_id, oid=observation.stdout.strip(), object_type="commit")


def resolve_ref(repository: RepositoryRef, ref: str) -> GitObjectRef:
    observation = run_git_observation(repository, ["rev-parse", "--verify", ref], timeout=10)
    if observation.git_exit_code != 0:
        raise GitAuthorityError("ref_unresolved", f"Git ref could not be resolved: {ref}", {"ref": ref, "stderr": observation.stderr})
    return GitObjectRef(repository_id=repository.repository_id, oid=observation.stdout.strip(), object_type="commit")


def object_exists(repository: RepositoryRef, oid: str) -> bool:
    observation = run_git_observation(repository, ["cat-file", "-e", oid], timeout=10)
    return observation.git_exit_code == 0


def is_ancestor(repository: RepositoryRef, ancestor_oid: str, descendant_oid: str) -> bool:
    observation = run_git_observation(repository, ["merge-base", "--is-ancestor", ancestor_oid, descendant_oid], timeout=20)
    if observation.git_exit_code in {0, 1}:
        return observation.git_exit_code == 0
    raise GitAuthorityError("ancestor_query_failed", "Git ancestry query failed.", {"stderr": observation.stderr})


def get_merge_base(repository: RepositoryRef, left_oid: str, right_oid: str) -> GitObjectRef:
    observation = run_git_observation(repository, ["merge-base", left_oid, right_oid], timeout=20)
    if observation.git_exit_code != 0:
        raise GitAuthorityError("merge_base_unavailable", "Git merge-base query failed.", {"stderr": observation.stderr})
    return GitObjectRef(repository_id=repository.repository_id, oid=observation.stdout.strip(), object_type="commit")


def get_blob_oid(repository: RepositoryRef, path: str | Path, revision: str | None = None) -> GitObjectRef:
    path_ref = normalize_repo_path(repository, path)
    if revision:
        observation = run_git_observation(repository, ["rev-parse", f"{revision}:{path_ref.path}"], timeout=10)
    else:
        observation = run_git_observation(repository, ["hash-object", "--", path_ref.path], timeout=10)
    if observation.git_exit_code != 0:
        raise GitAuthorityError("blob_oid_unavailable", f"Git blob OID unavailable for {path_ref.path}", {"stderr": observation.stderr})
    return GitObjectRef(repository_id=repository.repository_id, oid=observation.stdout.strip(), object_type="blob")


def get_diff(repository: RepositoryRef, *, staged: bool = False, paths: list[str] | None = None) -> str:
    args = ["diff"]
    if staged:
        args.append("--cached")
    if paths:
        args.append("--")
        args.extend(normalize_repo_path(repository, path).path for path in paths)
    observation = run_git_observation(repository, args, timeout=30)
    if observation.git_exit_code != 0:
        raise GitAuthorityError("diff_unavailable", "Git diff failed.", {"stderr": observation.stderr})
    return observation.stdout


def _branch_state(repository: RepositoryRef) -> tuple[str | None, bool]:
    branch = run_git_observation(repository, ["symbolic-ref", "--quiet", "--short", "HEAD"], timeout=10)
    if branch.git_exit_code == 0:
        return branch.stdout.strip() or None, False
    return None, True


def _parse_status_paths(stdout: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    staged: set[str] = set()
    unstaged: set[str] = set()
    untracked: set[str] = set()
    conflicts: set[str] = set()
    for line in stdout.splitlines():
        if not line:
            continue
        if line.startswith("?? "):
            untracked.add(line[3:])
            continue
        if len(line) < 3:
            continue
        xy = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if "U" in xy or xy in {"AA", "DD"}:
            conflicts.add(path)
        if xy[0] not in {" ", "?", "!"}:
            staged.add(path)
        if xy[1] not in {" ", "?", "!"}:
            unstaged.add(path)
    return tuple(sorted(staged)), tuple(sorted(unstaged)), tuple(sorted(untracked)), tuple(sorted(conflicts))


def get_status(repository: RepositoryRef) -> RepositoryStatusView:
    head = None
    try:
        head = get_head(repository).oid
    except GitAuthorityError:
        head = None
    branch, detached = _branch_state(repository)
    observation = run_git_observation(repository, ["status", "--porcelain=v1"], timeout=30)
    if observation.git_exit_code != 0:
        raise GitAuthorityError("status_unavailable", "Git status failed.", {"stderr": observation.stderr})
    staged, unstaged, untracked, conflicts = _parse_status_paths(observation.stdout)
    return RepositoryStatusView(
        repository_id=repository.repository_id,
        head_oid=head,
        branch=branch,
        detached=detached,
        staged_paths=staged,
        unstaged_paths=unstaged,
        untracked_paths=untracked,
        conflicts=conflicts,
        clean=not (staged or unstaged or untracked or conflicts),
        observation=observation,
    )


def get_changed_paths(repository: RepositoryRef) -> tuple[str, ...]:
    status = get_status(repository)
    return tuple(sorted(set(status.staged_paths) | set(status.unstaged_paths) | set(status.untracked_paths) | set(status.conflicts)))


def check_patch(repository: RepositoryRef, patch_path: str | Path):
    from Agency.Core.repository.git_authority.commands import check_patch as _check_patch

    return _check_patch(repository, patch_path)
