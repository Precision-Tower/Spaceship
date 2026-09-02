from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence


ResolveWorkspacePath = Callable[[str], Path]
StablePath = Callable[[Path], str]
DiffPaths = Callable[[str], list[str]]
ValidateDiffPaths = Callable[[str], None]
GitApplyBase = Callable[[], tuple[Path, list[str]]]
RunProcess = Callable[..., subprocess.CompletedProcess[str]]
ActionExecutor = Callable[[dict[str, Any]], dict[str, Any]]


def write_file_action(
    action: dict[str, Any],
    *,
    resolve_workspace_path: ResolveWorkspacePath,
    stable_path: StablePath,
) -> dict[str, Any]:
    action_type = action.get("type")

    if action_type not in {
        "create_file",
        "write_file",
    }:
        raise ValueError(
            f"unsupported_write_action: {action_type}"
        )

    target = resolve_workspace_path(
        str(action.get("path", ""))
    )

    content = str(action.get("content", ""))

    overwrite = bool(
        action.get(
            "overwrite",
            action_type == "write_file",
        )
    )

    if (
        action_type == "create_file"
        and target.exists()
        and not overwrite
    ):
        raise FileExistsError(
            f"target_exists: {stable_path(target)}"
        )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        content,
        encoding="utf-8",
    )

    return {
        "type": action_type,
        "status": "applied",
        "path": stable_path(target),
        "bytes_written": len(
            content.encode("utf-8")
        ),
    }


def validate_diff_paths(
    diff_text: str,
    *,
    diff_paths: DiffPaths,
    resolve_workspace_path: ResolveWorkspacePath,
) -> None:
    for raw_path in diff_paths(diff_text):
        resolve_workspace_path(raw_path)


def git_apply_base(
    *,
    dashboard_root: Path,
    run: RunProcess,
) -> tuple[Path, list[str]]:
    proc = run(
        [
            "git",
            "rev-parse",
            "--show-toplevel",
        ],
        cwd=str(dashboard_root),
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return dashboard_root, [
            "git",
            "apply",
        ]

    git_root = Path(
        proc.stdout.strip()
    ).resolve()

    resolved_dashboard_root = (
        dashboard_root.resolve()
    )

    try:
        directory = (
            resolved_dashboard_root
            .relative_to(git_root)
            .as_posix()
        )
    except ValueError:
        return dashboard_root, [
            "git",
            "apply",
        ]

    if directory in {"", "."}:
        return git_root, [
            "git",
            "apply",
        ]

    return git_root, [
        "git",
        "apply",
        f"--directory={directory}",
    ]


def patch_action(
    action: dict[str, Any],
    *,
    resolve_workspace_path: ResolveWorkspacePath,
    stable_path: StablePath,
    validate_diff_paths: ValidateDiffPaths,
    git_apply_base: GitApplyBase,
    run: RunProcess,
) -> dict[str, Any]:
    action_type = action.get("type")

    if action_type not in {
        "apply_patch",
        "propose_patch",
    }:
        raise ValueError(
            f"unsupported_patch_action: {action_type}"
        )

    if "diff" in action:
        diff_text = str(
            action.get("diff", "")
        )
        diff_label = "inline_diff"
    else:
        diff_path = resolve_workspace_path(
            str(action.get("diff_path", ""))
        )

        diff_text = diff_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        diff_label = stable_path(diff_path)

    if not diff_text.strip():
        raise ValueError(
            "empty_diff_rejected"
        )

    validate_diff_paths(diff_text)

    cwd, git_apply = git_apply_base()

    check = run(
        [
            *git_apply,
            "--check",
            "-",
        ],
        cwd=str(cwd),
        input=diff_text,
        capture_output=True,
        text=True,
    )

    if check.returncode != 0:
        raise RuntimeError(
            "patch_check_failed: "
            f"{check.stderr.strip()}"
        )

    applied = run(
        [
            *git_apply,
            "--verbose",
            "-",
        ],
        cwd=str(cwd),
        input=diff_text,
        capture_output=True,
        text=True,
    )

    if applied.returncode != 0:
        raise RuntimeError(
            "patch_apply_failed: "
            f"{applied.stderr.strip()}"
        )

    combined_output = (
        f"{applied.stdout}\n"
        f"{applied.stderr}"
    )

    if "Skipped patch" in combined_output:
        raise RuntimeError(
            "patch_apply_failed: git skipped "
            "one or more patch paths"
        )

    return {
        "type": action_type,
        "status": "applied",
        "diff": diff_label,
    }


def apply_action(
    action: dict[str, Any],
    *,
    write_file_action: ActionExecutor,
    patch_action: ActionExecutor,
) -> dict[str, Any]:
    action_type = action.get("type")

    if action_type in {
        "create_file",
        "write_file",
    }:
        return write_file_action(action)

    if action_type in {
        "apply_patch",
        "propose_patch",
    }:
        return patch_action(action)

    raise ValueError(
        f"unsupported_action_type: {action_type}"
    )
