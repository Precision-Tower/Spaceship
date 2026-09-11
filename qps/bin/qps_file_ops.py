#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


PATH_CHARS = "A-Za-z0-9_./-"
STRING_LITERAL_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


class QpsFileOpsError(Exception):
    pass


@dataclass(frozen=True)
class ReferenceMatch:
    file: str
    line: int
    column: int
    text: str
    kind: str = "exact"


@dataclass(frozen=True)
class ReplacementPlan:
    file: str
    text: str
    replacements: int


def fail(label: str, message: str) -> int:
    print(f"{label}=FAIL {message}", file=sys.stderr)
    return 1


def run_command(args: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise QpsFileOpsError(detail or f"command failed: {' '.join(args)}")
    return result


def run_git(root: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return run_command(["git", *args], root, check=check)


def repository_root(cwd: Path) -> Path:
    result = run_command(
        ["git", "rev-parse", "--show-toplevel"],
        cwd,
    )
    if result.returncode != 0:
        raise QpsFileOpsError("current directory is not inside a Git worktree")

    root = Path(result.stdout.strip()).resolve()
    if not (root / "_index.qps").is_file():
        raise QpsFileOpsError("repository authority is ambiguous: _index.qps not found at Git root")
    if not (root / "qps" / "_index.qps").is_file():
        raise QpsFileOpsError("repository authority is ambiguous: qps/_index.qps not found")

    return root


def qps_binary(root: Path) -> str:
    env_qps = os.environ.get("QPS")
    if env_qps:
        candidate = Path(env_qps).expanduser()
        if candidate.is_file():
            return str(candidate)

    repo_qps = root / "qps" / "cpp" / "build-pixel" / "qps"
    if repo_qps.is_file():
        return str(repo_qps)

    path_qps = shutil.which("qps")
    if path_qps:
        return path_qps

    raise QpsFileOpsError("qps executable not found")


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_repo_path(root: Path, cwd: Path, value: str) -> tuple[Path, str]:
    raw = Path(value).expanduser()
    path = raw if raw.is_absolute() else cwd / raw
    path = path.resolve(strict=False)

    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise QpsFileOpsError(f"path is outside the CE-OS worktree: {value}") from exc

    return path, relative.as_posix()


def require_qps_file_path(path: Path, label: str) -> None:
    if path.suffix != ".qps":
        raise QpsFileOpsError(f"{label} must be a .qps file: {path}")


def is_tracked(root: Path, path: str) -> bool:
    result = run_git(root, ["ls-files", "--error-unmatch", "--", path])
    return result.returncode == 0


def cached_state(root: Path) -> bytes:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise QpsFileOpsError(detail or "unable to read Git index state")
    return result.stdout


def repository_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise QpsFileOpsError(detail or "unable to list repository files")

    files: list[str] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        name = raw.decode("utf-8", errors="surrogateescape")
        path = root / name
        if path.is_file():
            files.append(Path(name).as_posix())

    return sorted(dict.fromkeys(files))


def read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def write_text_atomic(path: Path, text: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.qps-file-ops-",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise



def is_index_qps(path: str) -> bool:
    return path == "_index.qps" or path.endswith("/_index.qps")


def relative_reference(from_directory: Path, target: Path) -> str:
    return os.path.relpath(target, from_directory).replace(os.sep, "/")


def exact_reference_pattern(path_text: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![{PATH_CHARS}]){re.escape(path_text)}(?![{PATH_CHARS}])")


def find_references(root: Path, query: str) -> list[ReferenceMatch]:
    pattern = exact_reference_pattern(query)
    query_path = root / query
    matches: list[ReferenceMatch] = []

    for name in repository_files(root):
        text = read_text(root / name)
        if text is None:
            continue

        lines = text.splitlines()
        for line_number, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                matches.append(
                    ReferenceMatch(
                        file=name,
                        line=line_number,
                        column=match.start() + 1,
                        text=line.strip(),
                    )
                )

        if not is_index_qps(name):
            continue

        relative_query = relative_reference((root / name).parent, query_path)
        if relative_query == query:
            continue

        for line_number, line in enumerate(lines, 1):
            for match in STRING_LITERAL_RE.finditer(line):
                if match.group(1) != relative_query:
                    continue
                matches.append(
                    ReferenceMatch(
                        file=name,
                        line=line_number,
                        column=match.start(1) + 1,
                        text=line.strip(),
                        kind="relative-index",
                    )
                )

    return sorted(matches, key=lambda item: (item.file, item.line, item.column, item.kind))


def print_matches(matches: list[ReferenceMatch]) -> None:
    for match in matches:
        snippet = match.text
        if len(snippet) > 180:
            snippet = snippet[:177] + "..."
        kind = "" if match.kind == "exact" else f" [{match.kind}]"
        print(f"{match.file}:{match.line}:{match.column}{kind} {snippet}")


def validate_qps_file(qps: str, path: Path, root: Path) -> None:
    result = run_command([qps, str(path), "--check"], root)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise QpsFileOpsError(detail or f"QPS validation failed: {relpath(path, root)}")


def command_check(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: qps check <file.qps>", file=sys.stderr)
        return 1

    cwd = Path.cwd().resolve()
    try:
        root = repository_root(cwd)
        path, _ = resolve_repo_path(root, cwd, argv[1])
        require_qps_file_path(path, "check target")
        if not path.is_file():
            raise QpsFileOpsError(f"check target not found: {relpath(path, root)}")
        validate_qps_file(qps_binary(root), path, root)
        print("CHECK=PASS")
        print(f"file={relpath(path, root)}")
        print("surface=qps <file.qps> --check")
        return 0
    except QpsFileOpsError as error:
        return fail("CHECK", str(error))


def parse_refs_args(argv: list[str]) -> tuple[bool, str] | None:
    if len(argv) == 2:
        return False, argv[1]
    if len(argv) == 3 and argv[1] == "--absent":
        return True, argv[2]
    if len(argv) == 3 and argv[2] == "--absent":
        return True, argv[1]
    return None


def command_refs(argv: list[str]) -> int:
    parsed = parse_refs_args(argv)
    if parsed is None:
        print("Usage: qps refs [--absent] <path>", file=sys.stderr)
        return 1

    absent, query_text = parsed
    cwd = Path.cwd().resolve()
    try:
        root = repository_root(cwd)
        _, query = resolve_repo_path(root, cwd, query_text)
        matches = find_references(root, query)

        if absent and matches:
            print("REFS=FAIL stale references remain", file=sys.stderr)
            print(f"query={query}", file=sys.stderr)
            print(f"count={len(matches)}", file=sys.stderr)
            for match in matches:
                snippet = match.text
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."
                kind = "" if match.kind == "exact" else f" [{match.kind}]"
                print(f"{match.file}:{match.line}:{match.column}{kind} {snippet}", file=sys.stderr)
            return 1

        print("REFS=PASS")
        print(f"query={query}")
        print(f"mode={'absent' if absent else 'present'}")
        print(f"count={len(matches)}")
        print_matches(matches)
        return 0
    except QpsFileOpsError as error:
        return fail("REFS", str(error))



def replace_index_string_literals(text: str, old_value: str, new_value: str) -> tuple[str, int]:
    replacements = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacements
        if match.group(1) != old_value:
            return match.group(0)
        replacements += 1
        return '"' + new_value + '"'

    return STRING_LITERAL_RE.sub(replace, text), replacements

def build_replacement_plan(root: Path, old_ref: str, new_ref: str) -> list[ReplacementPlan]:
    pattern = exact_reference_pattern(old_ref)
    plans: list[ReplacementPlan] = []
    old_path = root / old_ref
    new_path = root / new_ref

    for name in repository_files(root):
        text = read_text(root / name)
        if text is None:
            continue

        new_text, replacements = pattern.subn(new_ref, text)

        if is_index_qps(name):
            base_directory = (root / name).parent
            old_value = relative_reference(base_directory, old_path)
            new_value = relative_reference(base_directory, new_path)
            if old_value != old_ref:
                new_text, relative_replacements = replace_index_string_literals(
                    new_text,
                    old_value,
                    new_value,
                )
                replacements += relative_replacements

        if replacements:
            plans.append(ReplacementPlan(name, new_text, replacements))

    return plans


def validate_candidate_text(qps: str, root: Path, relative: str, text: str) -> None:
    path = root / relative
    fd, candidate_name = tempfile.mkstemp(
        prefix=f".{path.name}.candidate-",
        suffix=".qps",
        dir=path.parent,
        text=True,
    )
    candidate = Path(candidate_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        validate_qps_file(qps, candidate, root)
    finally:
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass


def validate_candidates_before_mutation(qps: str, root: Path, source_rel: str, destination_rel: str, plans: list[ReplacementPlan]) -> None:
    planned_text = {plan.file: plan.text for plan in plans}
    qps_relatives = {destination_rel, *(plan.file for plan in plans if plan.file.endswith(".qps"))}

    for relative in sorted(qps_relatives):
        if relative == source_rel:
            text = planned_text.get(relative)
            if text is not None:
                validate_candidate_text(qps, root, relative, text)
            else:
                validate_qps_file(qps, root / source_rel, root)
            continue

        text = planned_text.get(relative)
        if text is not None:
            validate_candidate_text(qps, root, relative, text)
        elif relative == destination_rel:
            validate_qps_file(qps, root / source_rel, root)


def apply_replacements(root: Path, source_rel: str, destination_rel: str, plans: list[ReplacementPlan]) -> list[str]:
    changed: list[str] = []
    for plan in plans:
        target_rel = destination_rel if plan.file == source_rel else plan.file
        write_text_atomic(root / target_rel, plan.text)
        changed.append(target_rel)
    return sorted(dict.fromkeys(changed))


def run_diff_check(root: Path) -> None:
    result = run_git(root, ["diff", "--check"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise QpsFileOpsError(detail or "git diff --check failed")


def print_status(root: Path, paths: list[str]) -> None:
    unique = sorted(dict.fromkeys(paths))
    result = run_git(root, ["status", "--short", "--", *unique])
    lines = result.stdout.splitlines()
    if not lines:
        print("status=clean-for-targets")
        return
    print("status:")
    for line in lines:
        print(f"  {line}")


def command_move(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: qps move <old.qps> <new.qps>", file=sys.stderr)
        return 1

    cwd = Path.cwd().resolve()
    try:
        root = repository_root(cwd)
        source, source_rel = resolve_repo_path(root, cwd, argv[1])
        destination, destination_rel = resolve_repo_path(root, cwd, argv[2])

        require_qps_file_path(source, "move source")
        require_qps_file_path(destination, "move destination")

        if not source.is_file():
            raise QpsFileOpsError(f"move source not found: {source_rel}")
        if destination.exists() or destination.is_symlink():
            raise QpsFileOpsError(f"move destination already exists: {destination_rel}")
        if not destination.parent.is_dir():
            raise QpsFileOpsError(f"move destination parent not found: {relpath(destination.parent, root)}")
        if is_tracked(root, destination_rel):
            raise QpsFileOpsError(f"move destination is already tracked: {destination_rel}")

        source_state = "tracked" if is_tracked(root, source_rel) else "untracked"
        before_index = cached_state(root)
        qps = qps_binary(root)
        plans = build_replacement_plan(root, source_rel, destination_rel)
        replacements = sum(plan.replacements for plan in plans)

        validate_candidates_before_mutation(qps, root, source_rel, destination_rel, plans)

        source.rename(destination)
        changed = apply_replacements(root, source_rel, destination_rel, plans)
        if destination_rel not in changed:
            changed.append(destination_rel)
        changed = sorted(dict.fromkeys(changed))

        for relative in sorted(path for path in changed if path.endswith(".qps")):
            validate_qps_file(qps, root / relative, root)

        stale = find_references(root, source_rel)
        if stale:
            print("MOVE=FAIL stale references remain after mutation", file=sys.stderr)
            print(f"source={source_rel}", file=sys.stderr)
            print(f"destination={destination_rel}", file=sys.stderr)
            print(f"stale_count={len(stale)}", file=sys.stderr)
            for match in stale:
                kind = "" if match.kind == "exact" else f" [{match.kind}]"
                print(f"{match.file}:{match.line}:{match.column}{kind} {match.text}", file=sys.stderr)
            return 1

        run_diff_check(root)

        after_index = cached_state(root)
        if before_index != after_index:
            raise QpsFileOpsError("Git index changed; qps move must not stage")

        print("MOVE=PASS")
        print(f"source={source_rel}")
        print(f"destination={destination_rel}")
        print(f"source_state={source_state}")
        print("move_mode=filesystem")
        print("index=unchanged")
        print(f"references_updated={replacements}")
        print("stale_references=0")
        print("validated:")
        for relative in sorted(path for path in changed if path.endswith(".qps")):
            print(f"  {relative}")
        print("diff_check=PASS")
        print("changed:")
        for relative in changed:
            print(f"  {relative}")
        print_status(root, [source_rel, destination_rel, *changed])
        return 0
    except QpsFileOpsError as error:
        return fail("MOVE", str(error))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: qps <check|refs|move> ...", file=sys.stderr)
        return 1

    command = argv[1]
    if command == "check":
        return command_check(argv[1:])
    if command == "refs":
        return command_refs(argv[1:])
    if command == "move":
        return command_move(argv[1:])

    print("Usage: qps <check|refs|move> ...", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
