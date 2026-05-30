from pathlib import Path
import datetime

from runtime.agent_registry import normalized_agent_registry
from runtime.model_runner import generate_qwen_text, generate_qwen_text_with_timeout
from runtime.paths import DASHBOARD_ROOT, UI_ROOT, resolve_target_root, scan_files


DEFAULT_MODEL_PATH = DASHBOARD_ROOT / "Tools" / "Models" / "Qwen3-8b"
AGENT_PROMPT_PATH = UI_ROOT / "scripts" / "agents" / "cali.md"
CALI_AGENT_ID = "cali"


def _find_directory(root: Path):
    for rel in ["Models/Shared/Directory.yaml", "Shared/Directory.yaml", "Directory.yaml"]:
        candidate = root / rel
        if candidate.exists():
            return candidate
    matches = sorted(root.rglob("Directory.yaml"))
    return matches[0] if matches else None


def _read_excerpt(path: Path, max_chars: int = 6000) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... excerpt_truncated ..."


def _count_by_extension(files):
    counts = {}
    for rel in files:
        suffix = Path(rel).suffix.lower() or "[no_extension]"
        counts[suffix] = counts.get(suffix, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _count_by_top_folder(files):
    counts = {}
    for rel in files:
        top = rel.split("/", 1)[0]
        counts[top] = counts.get(top, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _recent_files(root: Path, files, limit: int = 16):
    recent = []
    for rel in files:
        path = root / rel
        try:
            stat = path.stat()
        except OSError:
            continue
        recent.append((stat.st_mtime, rel, stat.st_size))
    recent.sort(reverse=True)
    return recent[:limit]


def _candidate_attention_files(files, limit: int = 40):
    markers = [
        "backup",
        "copy",
        "diff",
        "latest",
        "old",
        "temp",
        "tmp",
        "tombstone",
        "updated",
    ]
    found = []
    for rel in files:
        lower = rel.lower()
        if any(marker in lower for marker in markers):
            found.append(rel)
    return found[:limit]


def _build_snapshot(root: Path, max_files: int) -> str:
    files = scan_files(root)
    directory = _find_directory(root)
    max_files = max(1, max_files)

    lines = [
        "DIRECTORY_SNAPSHOT",
        f"root: {root}",
        f"files_detected: {len(files)}",
        "",
        "top_folders:",
    ]
    for name, count in _count_by_top_folder(files)[:24]:
        lines.append(f"- {name}: {count}")

    lines.extend(["", "extensions:"])
    for ext, count in _count_by_extension(files)[:24]:
        lines.append(f"- {ext}: {count}")

    lines.extend(["", "recent_files:"])
    for stamp, rel, size in _recent_files(root, files):
        when = datetime.datetime.fromtimestamp(stamp).isoformat(timespec="seconds")
        lines.append(f"- {when} | {size} bytes | {rel}")

    attention_files = _candidate_attention_files(files)
    lines.extend(["", "candidate_attention_files:"])
    if attention_files:
        lines.extend(f"- {rel}" for rel in attention_files)
    else:
        lines.append("- none_detected_by_name_scan")

    lines.extend(["", f"files_listed_first_{min(max_files, len(files))}:"])
    for rel in files[:max_files]:
        lines.append(f"- {rel}")
    if len(files) > max_files:
        lines.append(f"... truncated {len(files) - max_files} more files")

    lines.extend(["", "directory_yaml_excerpt:"])
    if directory:
        lines.append(f"path: {directory.relative_to(root).as_posix()}")
        lines.append(_read_excerpt(directory))
    else:
        lines.append("blocked: no Directory.yaml found under target root")

    return "\n".join(lines)


def _resolve_cali_model_path() -> Path | None:
    registry = normalized_agent_registry()
    for agent in registry.get("agents", []):
        if agent.get("id") == CALI_AGENT_ID:
            model = agent.get("model", {})
            model_path = model.get("path")
            if model_path:
                return DASHBOARD_ROOT / model_path
            break
    return None


def _build_prompt(agent_prompt: str, snapshot: str) -> str:
    return f"""{agent_prompt}

Task:
Observe the Directory snapshot as Cali. Produce clerical recommendations only.
Use the exact output section names requested in the Cali prompt.

Directory snapshot:
```text
{snapshot}
```
"""


def _print_degraded_observation(status: str, reason: str):
    print(f"status: {status}")
    print("mode: degraded_no_model_generation")
    print()
    print("Active-looking areas")
    print("- blocked: local Cali model observation did not complete.")
    print()
    print("Stale or unclear areas")
    print("- blocked: stale/unclear classification requires model observation or manual review.")
    print()
    print("Changed/suspicious surfaces")
    print("- blocked: changed/suspicious classification requires model observation or manual review.")
    print()
    print("Files needing organization")
    print("- blocked: organization recommendations were not generated.")
    print()
    print("Suggested next clerical action")
    print("- Restore local Python/model execution, then rerun cali-observe-directory.")
    print()
    print("Blocked claims")
    print(f"- model_execution: {status}")
    print(f"- reason: {reason}")
    print("- no canon, validation, engineering truth, or file edit claim was made")


def run(args):
    root = resolve_target_root(args.root)
    model_path = Path(args.model_path).resolve() if args.model_path else _resolve_cali_model_path() or DEFAULT_MODEL_PATH
    max_files = args.max_files
    max_new_tokens = args.max_new_tokens
    timeout_seconds = args.timeout_seconds if hasattr(args, 'timeout_seconds') else None
    dry_run_model_path = args.dry_run_model_path if hasattr(args, 'dry_run_model_path') else False

    print("CALI_OBSERVE_DIRECTORY")
    print(f"root: {root}")
    print(f"model_path: {model_path}")
    
    # Handle --dry-run-model-path flag
    if dry_run_model_path:
        print("status: dry_run_model_path")
        print(f"resolved_model_path: {model_path}")
        return

    print("authority: read_only_observation_not_validation")
    print("edits: none")

    if not AGENT_PROMPT_PATH.exists():
        _print_degraded_observation(
            "blocked_agent_prompt_missing",
            f"Cali prompt not found at {AGENT_PROMPT_PATH}",
        )
        return

    agent_prompt = AGENT_PROMPT_PATH.read_text(encoding="utf-8", errors="replace")
    snapshot = _build_snapshot(root, max_files)
    prompt = _build_prompt(agent_prompt, snapshot)

    if timeout_seconds:
        result = generate_qwen_text_with_timeout(
            model_path=model_path,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            temperature=0.3,
            enable_thinking=False,
            timeout_seconds=timeout_seconds,
        )
    else:
        result = generate_qwen_text(
            model_path=model_path,
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            temperature=0.3,
            enable_thinking=False,
        )

    if not result.ok:
        _print_degraded_observation(result.status, result.reason)
        return

    print("status: observation_generated")
    print()
    print(result.text)
