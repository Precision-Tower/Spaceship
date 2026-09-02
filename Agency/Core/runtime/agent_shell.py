from __future__ import annotations

import argparse
import contextlib
import io
import sys

import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import re
import shlex

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
AGENCY_ROOT = DASHBOARD_ROOT / "Agency"

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Agency.Core.capabilities.agent_policy import resolve_policy_capabilities
from Agency.Core.repository.git_authority import GitAuthorityError, get_status, repository_ref

AGENT_NAME = "Agent"
AGENT_DIR = AGENCY_ROOT / "Agents" / AGENT_NAME
AGENT_CAPABILITIES = {}



def _snapshot_fact_block(snapshot_text: str) -> str:
    facts = {
        "Agency files": "not observed",
        "UI files": "not observed",
        "Engineering files": "not observed",
        "Workbench files": "not observed",
        "Workbench packet files": "not observed",
        "Workbench rendering files": "not observed",
        "Workbench viewport interaction files": "not observed",
        "Workbench scene files": "not observed",
        "Git modified files": "not observed",
        "Git untracked files": "not observed",
        "Modified file list": "not observed",
        "Untracked file list": "not observed",
    }

    current_section = None
    current_name = None

    for raw in snapshot_text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped == "scanned:":
            current_section = "scanned"
            current_name = None
            continue

        if stripped in {"git:", "git_observation:"}:
            current_section = "git"
            current_name = None
            continue

        if current_section == "scanned":
            if line.startswith("    ") and stripped.endswith(":") and not line.startswith("      "):
                current_name = stripped[:-1]
                continue

            if current_name and stripped.startswith("file_count:"):
                value = stripped.split(":", 1)[1].strip()
                name_map = {
                    "Agency": "Agency files",
                    "UI": "UI files",
                    "Engineering": "Engineering files",
                    "Workbench": "Workbench files",
                    "Workbench_packet": "Workbench packet files",
                    "Workbench_rendering": "Workbench rendering files",
                    "Workbench_viewport_interaction": "Workbench viewport interaction files",
                    "Workbench_scenes": "Workbench scene files",
                }
                if current_name in name_map:
                    facts[name_map[current_name]] = value

        if current_section == "git":
            if stripped.startswith("modified_count:"):
                facts["Git modified files"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("untracked_count:"):
                facts["Git untracked files"] = stripped.split(":", 1)[1].strip()
            elif stripped == "modified:":
                current_name = "modified_list"
                facts["Modified file list"] = []
            elif stripped == "untracked:":
                current_name = "untracked_list"
                facts["Untracked file list"] = []
            elif stripped.startswith("- ") and current_name == "modified_list":
                facts["Modified file list"].append(stripped[2:].strip("'\""))
            elif stripped.startswith("- ") and current_name == "untracked_list":
                facts["Untracked file list"].append(stripped[2:].strip("'\""))

    modified_list = facts["Modified file list"]
    untracked_list = facts["Untracked file list"]

    if isinstance(modified_list, list):
        modified_text = ", ".join(modified_list) if modified_list else "none observed"
    else:
        modified_text = modified_list

    if isinstance(untracked_list, list):
        untracked_text = ", ".join(untracked_list) if untracked_list else "none observed"
    else:
        untracked_text = untracked_list

    return "\n".join([
        "=== AUTHORITATIVE OBSERVED STATE ===",
        "Authority: workspace_snapshot_not_validation",
        "",
        f"Agency files: {facts['Agency files']}",
        f"UI files: {facts['UI files']}",
        f"Engineering files: {facts['Engineering files']}",
        f"Workbench files: {facts['Workbench files']}",
        f"Workbench packet files: {facts['Workbench packet files']}",
        f"Workbench rendering files: {facts['Workbench rendering files']}",
        f"Workbench viewport interaction files: {facts['Workbench viewport interaction files']}",
        f"Workbench scene files: {facts['Workbench scene files']}",
        "",
        "Required Workbench Observed lines when Workbench is in scope:",
        f"- Workbench files: {facts['Workbench files']}",
        f"- Workbench packet files: {facts['Workbench packet files']}",
        f"- Workbench rendering files: {facts['Workbench rendering files']}",
        f"- Workbench viewport interaction files: {facts['Workbench viewport interaction files']}",
        f"- Workbench scene files: {facts['Workbench scene files']}",
        "",
        f"Git modified files: {facts['Git modified files']}",
        f"Git untracked files: {facts['Git untracked files']}",
        f"Modified file list: {modified_text}",
        f"Untracked file list: {untracked_text}",
        "",
        "Rules:",
        "- Do not contradict the authoritative observed state.",
        "- Do not infer remote sync status from local snapshot facts.",
        "- Observed must list only facts from the authoritative observed state block or explicit tool output.",
        "- Do not put available commands in Observed.",
        "- Do not claim repository health unless a health command result is supplied.",
        "- Do not claim there are no unresolved issues; say none were observed in the current snapshot.",
        "- Next inspection target must name exactly one concrete inspection target.",
        "- Valid next inspection targets include: git status --short, modified file list, untracked file list, current_workspace_snapshot.yaml, or test-all output.",
        "- Never say inspect the repository generically.",
        "- Never use the phrase inspect the repository generically.",
    ])


def _direct_file_context_from_prompt(prompt: str, max_chars_per_file: int = 2500, max_total_chars: int = 6000) -> str:
    matches = re.findall(r'[\w./-]+\.(?:gd|py|yaml|yml|json|tscn|md|txt)', prompt)
    seen = []
    for value in matches:
        path = Path(value)
        if path.is_absolute():
            continue
        full = DASHBOARD_ROOT / path
        try:
            resolved = full.resolve()
            if not str(resolved).startswith(str(DASHBOARD_ROOT)):
                continue
            if resolved.exists() and resolved.is_file() and path.as_posix() not in seen:
                seen.append(path.as_posix())
        except Exception:
            continue

    if not seen:
        return ""

    parts = ["=== DIRECT FILE CONTEXT ===", "Authority: observed_file_contents_not_validation", ""]
    total = 0

    for rel in seen[:4]:
        full = DASHBOARD_ROOT / rel
        text = full.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars_per_file:
            text = text[:max_chars_per_file] + "\n...[truncated]"
        block = f"--- {rel} ---\n{text}\n"
        if total + len(block) > max_total_chars:
            break
        parts.append(block)
        total += len(block)

    parts.append("Rules:")
    parts.append("- When direct file context is present, Observed may summarize those file contents.")
    parts.append("- Do not claim behavior was executed unless tool output is supplied.")
    parts.append("- Do not propose changes unless explicitly asked.")
    return "\n".join(parts)

def configure(agent_name: str) -> None:
    global AGENT_NAME, AGENT_DIR, AGENT_CAPABILITIES
    AGENT_NAME = agent_name
    AGENT_DIR = AGENCY_ROOT / "Agents" / AGENT_NAME

    policy_path = AGENT_DIR / "action_policy.yaml"
    AGENT_CAPABILITIES = (
        resolve_policy_capabilities(policy_path, AGENT_NAME)
        if policy_path.exists()
        else {}
    )


def status() -> dict:
    from Agency.Core.runtime.authoritative_state import authoritative_state

    state = authoritative_state(
        AGENT_NAME,
        agents_root=AGENCY_ROOT / "Agents",
    )
    return {
        "ok": state.available,
        "status": (
            "authoritative_runtime_state"
            if state.available
            else "authoritative_state_unavailable"
        ),
        "agent": AGENT_NAME,
        "authority": "authoritative_state",
        "capabilities": list(AGENT_CAPABILITIES),
        "state": state.to_dict(),
    }


def _print_help() -> None:
    print(f"{AGENT_NAME} terminal commands:")
    print("  /status")
    print("  /memory")
    print("  /refresh")
    print("  /observe")
    print("  /mission <create|status|list|show|resume|inspect|plan|scope-add|replan|resourcefulness|propose|review|implement|verify> ...")
    print("  /review latest       legacy ActionPacket review")
    print("  /propose <task>")
    print("  /analyze refs <text>")
    print("  /analyze tree <path>")
    print("  /greenlight latest   legacy ActionPacket review + apply")
    print("  /apply latest        legacy ActionPacket apply")
    print("  /raw on|off")
    print("  /tool <command> [args...]")
    print("  /tools")
    print("  /exit")


def _print_status(raw: bool) -> None:
    payload = status()
    if raw:
        print(json.dumps(payload, indent=2))
        return

    state = payload.get("state", {})
    identity = state.get("identity", {}) if isinstance(state, dict) else {}
    runtime = state.get("runtime", {}) if isinstance(state, dict) else {}
    authority = state.get("authority", {}) if isinstance(state, dict) else {}
    mission = state.get("active_mission", {}) if isinstance(state, dict) else {}
    policies = state.get("loaded_policies", []) if isinstance(state, dict) else []
    memory = state.get("memory", {}) if isinstance(state, dict) else {}
    sources = state.get("sources", {}) if isinstance(state, dict) else {}

    print(f"{AGENT_NAME} status")

    if not payload.get("ok"):
        print("")
        print("Authoritative runtime state is not currently available.")
        return

    print("")
    print("Identity")
    print(f"  name: {identity.get('name')}")
    print(f"  role: {identity.get('role')}")
    if identity.get("description"):
        print(f"  description: {identity.get('description')}")

    print("")
    print("Runtime")
    print(f"  backend: {runtime.get('backend')}")
    print(f"  accelerator: {runtime.get('accelerator')}")
    print(f"  inference_route: {runtime.get('inference_route')}")
    print(f"  execution_mode: {runtime.get('execution_mode')}")

    print("")
    print("Authority")
    print(f"  runtime: {authority.get('environment_authority')}")
    print(f"  runtime_authority: {authority.get('runtime_authority')}")
    print(f"  agent_owns_runtime_selection: {authority.get('agent_owns_runtime_selection')}")

    print("")
    print("Mission")
    if mission.get("active"):
        print(f"  active: {mission.get('mission_id') or mission.get('intent')}")
    else:
        print("  active: none")

    print("")
    print("Policies")
    loaded = [item for item in policies if isinstance(item, dict) and item.get("loaded")]
    if loaded:
        for item in loaded:
            print(f"  {item.get('name')}")
    else:
        print("  none")

    print("")
    print("Memory")
    print(f"  vector_store: {'enabled' if memory.get('vector_store_enabled') else 'disabled'}")
    print(f"  sources: {memory.get('sources_file')}")
    print(f"  chroma: {memory.get('chroma')}")

    print("")
    print("Diagnostics")
    print(f"  repository_root: {sources.get('repository_root')}")
    print(f"  agent_dir: {sources.get('agent_dir')}")


def _print_agent_answer(prompt: str, raw: bool) -> int:
    from Agency.Core.runtime.model_service import ask_agent

    try:
        with contextlib.redirect_stderr(io.StringIO()):
            snapshot_path = (
                AGENT_DIR
                / "state"
                / "current_workspace_snapshot.yaml"
            )

            if snapshot_path.exists():
                snapshot_text = snapshot_path.read_text(encoding="utf-8")
                repository_health_context = (
                    "Available command, not an observed fact:\n"
                    "python -m Agency.Core.interfaces.cli.dashboard_cli test-all --root .\n\n"
                    "Rule:\n"
                    "Do not place available commands in Observed.\n"
                    "When explicitly asked about repository health, say health requires running the health command unless its output is already supplied.\n\n"
                )
                fact_block = _snapshot_fact_block(snapshot_text)
                direct_file_context = _direct_file_context_from_prompt(prompt)

                grounded_prompt = (
                    repository_health_context +
                    fact_block +
                    "\n\n" +
                    direct_file_context +
                    "\n\n"
                    "Raw workspace snapshot follows for reference only.\n"
                    "The authoritative observed state block above overrides retrieved memory and raw summary interpretation.\n\n"
                    f"{snapshot_text}\n\n"
                    "Required output discipline:\n"
                    "Observed must only contain extracted observed facts.\n"
                    "When Workbench facts are present, Observed must include Workbench files, Workbench packet files, Workbench rendering files, Workbench viewport interaction files, and Workbench scene files.\n"
                    "Do not replace file counts with vague labels like packet loading or viewport rendering surfaces.\n"
                    "Inferred must contain only cautious conclusions derived from observed facts, or the literal word None.\n"
                    "Inferred must not mention unresolved issues, unresolved tasks, repository health, remote sync, or validation.\n"
                    "Unresolved must not say None.\n"
                    "Unresolved must say: No unresolved issues were observed in the current workspace snapshot.\n"
                    "Next inspection target must be one concrete target, not generic repository inspection.\n\n"
                    f"User request:\n{prompt}"
                )
            else:
                grounded_prompt = prompt

            t0 = time.perf_counter()
            payload = ask_agent(AGENT_NAME, grounded_prompt, max_new_tokens=512)
            inference_seconds = time.perf_counter() - t0

    except Exception as exc:
        print(f"{AGENT_NAME} unavailable: {type(exc).__name__}: {exc}")
        return 1

    if raw:
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1

    if payload.get("ok"):
        provenance = payload.get("response_provenance")
        label = {
            "authoritative_state": "Authoritative State",
            "repository_evidence": "Repository Evidence",
            "repository_evidence_with_synthesis": "Repository Evidence",
            "model_inference": "Inference",
        }.get(provenance, "Inference")
        print(f"[{label}] {inference_seconds:.3f} s")
        print(str(payload.get("draft", "")).strip())
        return 0

    print(f"{AGENT_NAME} unavailable: {payload.get('reason') or payload.get('status')}")
    return 1


def _print_observe(raw: bool = False) -> int:
    snapshot_path = AGENT_DIR / "state" / "current_workspace_snapshot.yaml"
    if not snapshot_path.exists():
        print("No workspace snapshot found. Run /refresh first.")
        return 1

    snapshot_text = snapshot_path.read_text(encoding="utf-8")
    fact_block = _snapshot_fact_block(snapshot_text)

    if raw:
        print(json.dumps({
            "agent": AGENT_NAME,
            "fact_block": fact_block,
            "authority": "workspace_snapshot_not_validation",
        }, indent=2))
        return 0

    print(f"{AGENT_NAME} observation")
    print(fact_block)
    return 0

def _print_memory(raw: bool) -> None:
    from Agency.Core.agents.tooling.Chroma import retrieve_agent_memory

    try:
        with contextlib.redirect_stderr(io.StringIO()):
            rows = retrieve_agent_memory(AGENT_NAME, f"{AGENT_NAME} current memory status", n_results=5)
    except Exception as exc:
        print(f"{AGENT_NAME} memory unavailable: {type(exc).__name__}: {exc}")
        return

    payload = {
        "agent": AGENT_NAME,
        "memory_results_loaded": len(rows),
        "top_paths": [row.get("path", "UNKNOWN") for row in rows],
        "authority": "retrieval_only_not_source_authority",
    }

    if raw:
        print(json.dumps(payload, indent=2))
        return

    print(f"{AGENT_NAME} memory")
    print(f"  results: {len(rows)}")
    if rows:
        print("  top paths:")
        for row in rows:
            print(f"    - {row.get('path', 'UNKNOWN')}")
    print("  authority: retrieval_only_not_source_authority")

def _refresh(raw: bool) -> int:
    from Agency.Core.agents.tooling.Chroma import build_agent_index

    dashboard_root = DASHBOARD_ROOT
    state_dir = AGENT_DIR / "state"
    snapshot_path = state_dir / "current_workspace_snapshot.yaml"

    scan_roots = {
        "Agency": dashboard_root / "Agency",
        "UI": dashboard_root / "UI",
        "Engineering": dashboard_root / "Engineering",
        "Workbench": dashboard_root / "UI" / "Workbench",
        "Workbench_packet": dashboard_root / "UI" / "Workbench" / "packet",
        "Workbench_rendering": dashboard_root / "UI" / "Workbench" / "rendering",
        "Workbench_viewport_interaction": dashboard_root / "UI" / "Workbench" / "interaction",
        "Workbench_scenes": dashboard_root / "UI" / "Workbench" / "scenes",
        "Workbench_primitives": dashboard_root / "UI" / "Workbench" / "primitives",
        "Workbench_rendering": dashboard_root / "UI" / "Workbench" / "rendering",
        "Engineering_primitives": dashboard_root / "Engineering" / "Physics",
    }

    scanned = {}
    for name, path in scan_roots.items():
        files = [
            p for p in path.rglob("*")
            if p.is_file()
            and ".git" not in p.parts
            and "__pycache__" not in p.parts
            and "Chroma" not in p.parts
        ] if path.exists() else []

        scanned[name] = {
            "path": str(path.relative_to(dashboard_root)),
            "exists": path.exists(),
            "file_count": len(files),
            "files": [str(f.relative_to(dashboard_root)) for f in files[:25]],
        }

    modified = []
    untracked = []
    git_observation = {
        "authority": "historical_git_observation_not_current_truth",
        "error": None,
        "modified_count": 0,
        "untracked_count": 0,
        "modified": [],
        "untracked": [],
    }
    try:
        status_view = get_status(repository_ref(dashboard_root))
        modified = sorted(set(status_view.staged_paths) | set(status_view.unstaged_paths))
        untracked = list(status_view.untracked_paths)
        git_observation.update({
            "observation_id": status_view.observation.observation_id,
            "observed_at": status_view.observation.observed_at,
            "git_command": list(status_view.observation.git_command),
            "git_exit_code": status_view.observation.git_exit_code,
            "output_sha256": status_view.observation.output_sha256,
            "head_oid": status_view.head_oid,
            "modified_count": len(modified),
            "untracked_count": len(untracked),
            "modified": modified[:50],
            "untracked": untracked[:50],
        })
    except GitAuthorityError as exc:
        git_observation["error"] = exc.to_dict()

    proposal_dir = AGENT_DIR / "actions" / "proposals"
    result_dir = AGENT_DIR / "actions" / "results"

    snapshot = {
        "WorkspaceSnapshot": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "root": str(dashboard_root),
            "authority": "workspace_snapshot_not_validation",
            "scanned": scanned,
            "git_observation": git_observation,
            "action_packets": {
                "authority": "legacy_action_packet_workspace_observation",
                "proposal_count": len(list(proposal_dir.glob("*.yaml"))) if proposal_dir.exists() else 0,
                "result_count": len(list(result_dir.glob("*.yaml"))) if result_dir.exists() else 0,
            },
        }
    }

    state_dir.mkdir(parents=True, exist_ok=True)

    lines = ["WorkspaceSnapshot:"]
    data = snapshot["WorkspaceSnapshot"]
    lines.append(f"  timestamp_utc: {data['timestamp_utc']}")
    lines.append(f"  root: {data['root']}")
    lines.append(f"  authority: {data['authority']}")
    lines.append("  scanned:")
    for name, info in scanned.items():
        lines.append(f"    {name}:")
        lines.append(f"      path: {info['path']}")
        lines.append(f"      exists: {str(info['exists']).lower()}")
        lines.append(f"      file_count: {info['file_count']}")
        lines.append("      files:")
        for file_path in info.get("files", [])[:25]:
            lines.append(f"        - {file_path!r}")
    lines.append("  git_observation:")
    lines.append("    authority: historical_git_observation_not_current_truth")
    lines.append(f"    observation_id: {git_observation.get('observation_id')!r}")
    lines.append(f"    observed_at: {git_observation.get('observed_at')!r}")
    lines.append(f"    git_command: {git_observation.get('git_command', [])!r}")
    lines.append(f"    git_exit_code: {git_observation.get('git_exit_code')!r}")
    lines.append(f"    output_sha256: {git_observation.get('output_sha256')!r}")
    lines.append(f"    head_oid: {git_observation.get('head_oid')!r}")
    lines.append(f"    modified_count: {git_observation['modified_count']}")
    lines.append(f"    untracked_count: {git_observation['untracked_count']}")
    lines.append("    modified:")
    for item in git_observation["modified"][:50]:
        lines.append(f"      - {item!r}")
    lines.append("    untracked:")
    for item in git_observation["untracked"][:50]:
        lines.append(f"      - {item!r}")
    lines.append("  action_packets:")
    lines.append(
        "    authority: "
        f"{snapshot['WorkspaceSnapshot']['action_packets']['authority']}"
    )
    lines.append(f"    proposal_count: {snapshot['WorkspaceSnapshot']['action_packets']['proposal_count']}")
    lines.append(f"    result_count: {snapshot['WorkspaceSnapshot']['action_packets']['result_count']}")
    snapshot_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        build_agent_index(AGENT_NAME)

    if raw:
        print(json.dumps(snapshot, indent=2))
        return 0

    print(f"{AGENT_NAME} refresh complete")
    print(f"  snapshot: {snapshot_path.relative_to(dashboard_root)}")
    for name, info in scanned.items():
        print(f"  {name}: {info['file_count']} files")
    print(f"  git modified: {len(modified)}")
    print(f"  git untracked: {len(untracked)}")
    print("  memory: rebuilt")
    print("  authority: workspace_snapshot_not_validation")
    return 0

def _run_printing_command(func, *args, raw: bool = False, **kwargs) -> int:
    if raw:
        return func(*args, **kwargs)

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = func(*args, **kwargs)

    text = buffer.getvalue().strip()
    if text:
        print(text)
    return code


def _propose(task: str, raw: bool) -> int:
    if "engineering" not in AGENT_CAPABILITIES:
        print("Engineering capability is not enabled for this agent.")
        return 2

    from Agency.Core.agents.tooling.agent_actions import propose_action

    return _run_printing_command(propose_action, AGENT_NAME, task, raw=raw)


def _print_action_packet_compatibility_notice(command: str) -> None:
    print("LEGACY_ACTION_PACKET_COMMAND")
    print(f"command: {command}")
    print("packet_model: ActionPacket")
    print("preferred_model: WorkPacket")
    print("help: python run.py work-packet --help")
    print()


def _run_latest_action_packet_review(raw: bool) -> int:
    from Agency.Core.agents.tooling.agent_actions import review_action_packet

    return _run_printing_command(
        review_action_packet,
        AGENT_NAME,
        latest=True,
        raw=raw,
    )


def _review_latest(raw: bool) -> int:
    _print_action_packet_compatibility_notice("/review latest")
    return _run_latest_action_packet_review(raw)


def _greenlight_latest(
    raw: bool,
    *,
    command: str = "/greenlight latest",
) -> int:
    if "engineering" not in AGENT_CAPABILITIES:
        print("Engineering capability is not enabled for this agent.")
        return 2

    _print_action_packet_compatibility_notice(command)

    from Agency.Core.agents.tooling.agent_actions import apply_action_packet

    review_code = _run_latest_action_packet_review(raw)
    if review_code != 0:
        print("Greenlight blocked until review succeeds.")
        return review_code

    return _run_printing_command(
        apply_action_packet,
        AGENT_NAME,
        latest=True,
        approved=True,
        raw=raw,
    )


def _apply_latest(raw: bool) -> int:
    return _greenlight_latest(
        raw,
        command="/apply latest",
    )

def _analyze_refs(query: str, raw: bool) -> int:
    dashboard_root = DASHBOARD_ROOT
    search_roots = ["Agency", "UI", "Engineering", "run.py"]

    matches = []
    for root_name in search_roots:
        root = dashboard_root / root_name
        if root.is_file():
            files = [root]
        elif root.exists():
            ignore_parts = {".git", "__pycache__", "Chroma", "actions", "memory"}
            files = [
                p for p in root.rglob("*")
                if p.is_file()
                and not any(part in ignore_parts for part in p.parts)
            ]
        else:
            continue

        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for idx, line in enumerate(text.splitlines(), start=1):
                if query in line:
                    matches.append({
                        "path": str(path.relative_to(dashboard_root)),
                        "line": idx,
                        "text": line.strip(),
                    })

    if raw:
        print(json.dumps({
            "query": query,
            "matches": matches,
            "count": len(matches),
            "authority": "filesystem_scan_not_validation",
        }, indent=2))
        return 0

    print(f"References for: {query}")
    print(f"count: {len(matches)}")
    for match in matches[:80]:
        print(f"- {match['path']}:{match['line']} {match['text']}")
    if len(matches) > 80:
        print(f"... truncated {len(matches) - 80} more")
    print("authority: filesystem_scan_not_validation")
    return 0

def _analyze_tree(path_text: str, raw: bool) -> int:
    dashboard_root = DASHBOARD_ROOT
    target = (dashboard_root / path_text).resolve()

    try:
        target.relative_to(dashboard_root)
    except ValueError:
        print("ERR: path outside dashboard workspace")
        return 2

    if not target.exists() or not target.is_dir():
        print(f"ERR: directory not found: {path_text}")
        return 2

    buckets = {}
    file_count = 0
    stale_refs = []

    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or "Chroma" in path.parts:
            continue

        file_count += 1
        rel = path.relative_to(target)
        bucket = rel.parts[0] if len(rel.parts) > 1 else "."
        buckets[bucket] = buckets.get(bucket, 0) + 1

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if "res://screen" in text:
                stale_refs.append(str(path.relative_to(dashboard_root)))
        except Exception:
            pass

    payload = {
        "path": str(target.relative_to(dashboard_root)),
        "file_count": file_count,
        "buckets": buckets,
        "stale_res_screen_refs": stale_refs,
        "authority": "filesystem_scan_not_validation",
    }

    if raw:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Tree analysis: {payload['path']}")
    print(f"files: {file_count}")
    print("buckets:")
    for name, count in sorted(buckets.items()):
        print(f"  - {name}: {count}")
    print(f"stale res://screen refs: {len(stale_refs)}")
    for ref in stale_refs[:40]:
        print(f"  - {ref}")
    print("authority: filesystem_scan_not_validation")
    return 0


def _mission_row_status(row: dict) -> str:
    progress = row.get("unit_progress", {})
    if row.get("phase") == "implementing" or (
        progress.get("total", 0)
        and progress.get("complete", 0) < progress.get("total", 0)
    ):
        return f"{progress.get('complete', 0)}/{progress.get('total', 0)} units"
    if row.get("phase") == "complete":
        return "verified"
    return str(row.get("status") or "")


def _mission_table(rows: list[dict]) -> str:
    header = ("MISSION", "PHASE", "STATUS")
    widths = [
        max(len(header[0]), *(len(str(row.get("mission_id", ""))) for row in rows)) if rows else len(header[0]),
        max(len(header[1]), *(len(str(row.get("phase", ""))) for row in rows)) if rows else len(header[1]),
        max(len(header[2]), *(len(_mission_row_status(row)) for row in rows)) if rows else len(header[2]),
    ]
    lines = [
        f"{header[0]:<{widths[0]}}  {header[1]:<{widths[1]}}  {header[2]:<{widths[2]}}",
        f"{'-' * widths[0]}  {'-' * widths[1]}  {'-' * widths[2]}",
    ]
    for row in rows:
        lines.append(
            f"{str(row.get('mission_id', '')):<{widths[0]}}  "
            f"{str(row.get('phase', '')):<{widths[1]}}  "
            f"{_mission_row_status(row):<{widths[2]}}"
        )
    return "\n".join(lines)


def _render_mission_show(reconstruction: dict) -> str:
    progress = reconstruction.get("unit_progress", {})
    lines = [
        f"# Mission {reconstruction.get('mission_id')}",
        "",
        "## Intent",
        "",
        str(reconstruction.get("intent") or ""),
        "",
        "## Phase",
        "",
        f"{reconstruction.get('phase')} / {reconstruction.get('status')}",
        "",
        "## Next Action",
        "",
        str(reconstruction.get("next_action", {}).get("command")),
        "",
        str(reconstruction.get("next_action", {}).get("reason") or ""),
        "",
        "## Unit Progress",
        "",
        f"{progress.get('complete', 0)}/{progress.get('total', 0)} complete",
    ]
    for unit in progress.get("units", []):
        lines.append(f"- {unit.get('id')}: {unit.get('status')} attempt={unit.get('attempt')}")
    if not progress.get("units"):
        lines.append("- none")
    return "\n".join(lines)



def _render_mission_resume(reconstruction: dict) -> str:
    checkpoints = reconstruction.get("checkpoints", {})
    progress = reconstruction.get("unit_progress", {})
    implementing_detail = (
        f"{progress.get('complete', 0)}/{progress.get('total', 0)} units complete"
        if progress.get("total", 0)
        else "0 units"
    )

    def line(label: str, complete: bool, detail: str | None = None) -> str:
        mark = "[x]" if complete else "[ ]"
        suffix = f" ({detail})" if detail else ""
        return f"{mark} {label}{suffix}"

    lines = [
        f"Mission: {reconstruction.get('mission_id')}",
        f"Phase: {reconstruction.get('phase')}",
        f"Status: {reconstruction.get('status')}",
        "",
        "Mission Phase",
        line("Created", bool(checkpoints.get("created"))),
        line("Inspected", bool(checkpoints.get("inspected")), f"{reconstruction.get('inspection', {}).get('passes', 0)} passes"),
        line("Planned", bool(checkpoints.get("planned"))),
        line("Proposed", bool(checkpoints.get("proposed"))),
        line("Approved", bool(checkpoints.get("approved"))),
        line("Implementing", bool(checkpoints.get("implemented")), implementing_detail),
        line("Verification", bool(checkpoints.get("verified")), reconstruction.get("verification", {}).get("result") or "pending"),
        "",
        "Next command:",
        str(reconstruction.get("next_action", {}).get("command")),
        "",
        str(reconstruction.get("next_action", {}).get("reason") or ""),
    ]
    return "\n".join(lines)

_MISSION_HELP_DESCRIPTION = """Mission tier operational manual

Mission coordinates bounded Core work through persisted artifacts, not loose chat state.
The contract is: intent -> bounded scope -> read-only inspect -> read-only plan -> scope-add when needed -> proposal -> operator review -> implement -> verify.

Architecture alignment:
  - Agency/architecture.yaml defines Core/work as the Task, WorkPacket, Mission, and Adventure workflow home.
  - Core roots are authoritative; active Mission code lives under Agency/Core/work and help surfaces live under Agency/Core/runtime.
  - Retired active namespaces are excluded from current Mission imports and commands.
"""

_MISSION_HELP_EPILOG = """Operational invariants:
  - create records operator intent and explicit engineering scope; it does not inspect or mutate source.
  - inspect reads only bounded scope files and writes inspect/pass_###.json plus inspect/pass_###.md.
  - plan may synthesize only from persisted inspection artifacts; it must not inspect the repository or edit files.
  - scope-add appends concrete validated paths to the same mission and routes back to inspect.
  - propose, review, implement, and verify advance only after the previous persisted state is present.
  - generated next_action commands use --mission; positional MISSION is accepted for direct operator use.

Typical lifecycle:
  %(prog)s create --intent "Fix bounded behavior" --scope Agency/Core/work/missions/mission_runtime.py
  %(prog)s inspect --mission mission-3
  %(prog)s plan --mission mission-3
  %(prog)s propose --mission mission-3
  %(prog)s review --mission mission-3 --approve
  %(prog)s implement --mission mission-3
  %(prog)s verify --mission mission-3
"""

_MISSION_ID_HELP = "Mission identifier such as mission-3 or 3."
_MISSION_FLAG_HELP = "Mission identifier. This form is used by generated next_action payloads."
_RAW_HELP = "Emit the JSON payload without shell rendering changes."


def _mission_formatter() -> type[argparse.RawDescriptionHelpFormatter]:
    return argparse.RawDescriptionHelpFormatter


def _add_raw_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--raw", action="store_true", help=_RAW_HELP)


def _add_mission_reference(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("mission", nargs="?", metavar="MISSION", help=_MISSION_ID_HELP)
    parser.add_argument("--mission", dest="mission_flag", metavar="MISSION", help=_MISSION_FLAG_HELP)


def _normalize_mission_reference(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not hasattr(args, "mission_flag"):
        return
    positional = str(getattr(args, "mission", "") or "").strip()
    flagged = str(getattr(args, "mission_flag", "") or "").strip()
    if positional and flagged and positional != flagged:
        parser.error("mission identifier was supplied twice with different values")
    mission = flagged or positional
    if not mission:
        parser.error(f"mission {args.mission_command} requires MISSION or --mission MISSION")
    args.mission = mission


def _build_mission_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"{AGENT_NAME} mission",
        description=_MISSION_HELP_DESCRIPTION,
        epilog=_MISSION_HELP_EPILOG,
        formatter_class=_mission_formatter(),
    )
    sub = parser.add_subparsers(
        dest="mission_command",
        required=True,
        metavar="<command>",
        title="mission commands",
    )

    create = sub.add_parser(
        "create",
        help="record intent and bounded engineering scope",
        description="Create a Mission from explicit operator intent and one or more concrete scope paths.",
        epilog=(
            "Prerequisites:\n"
            "  --intent must state the operational outcome.\n"
            "  --scope must name active repository paths allowed by Core scope policy; repeat for multiple paths.\n\n"
            "Next lifecycle step: mission inspect --mission <mission-id>."
        ),
        formatter_class=_mission_formatter(),
    )
    create.add_argument("--intent", required=True, metavar="TEXT", help="Operator intent to persist as the mission contract.")
    create.add_argument("--scope", action="append", required=True, metavar="PATH", help="Concrete bounded path to include in scope. Repeat for multiple paths.")
    _add_raw_argument(create)

    status = sub.add_parser(
        "status",
        help="show current mission state and next action",
        description="Report the persisted mission phase, status, unresolved blockers, and next lifecycle command.",
        epilog="Prerequisite: mission artifact directory exists. This command is read-only.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(status)
    _add_raw_argument(status)

    list_cmd = sub.add_parser(
        "list",
        help="list known mission artifacts",
        description="List persisted Mission directories newest first without changing mission state.",
        epilog="Prerequisite: none. This command is read-only.",
        formatter_class=_mission_formatter(),
    )
    _add_raw_argument(list_cmd)

    show = sub.add_parser(
        "show",
        help="render mission reconstruction",
        description="Reconstruct the mission from intent, state, events, inspection, plan, proposal, review, implementation, and verification artifacts.",
        epilog="Prerequisite: mission artifact directory exists. This command is read-only.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(show)
    _add_raw_argument(show)

    inspect = sub.add_parser(
        "inspect",
        help="read bounded scope and persist inspection pass artifacts",
        description="Run one read-only inspection pass over queued files from the mission scope.",
        epilog=(
            "Prerequisites:\n"
            "  mission create has persisted intent and scope.\n"
            "  scoped files are concrete active Core/UI engineering or evidence paths.\n\n"
            "Writes: inspect/pass_###.json, inspect/pass_###.md, manifest.json, coverage.json, state.json.\n"
            "Next lifecycle step: repeat inspect while files remain, then mission plan --mission <mission-id>."
        ),
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(inspect)
    _add_raw_argument(inspect)

    plan = sub.add_parser(
        "plan",
        help="synthesize architecture plan from inspection evidence",
        description="Generate the bounded architecture plan from persisted inspection artifacts only.",
        epilog=(
            "Prerequisites:\n"
            "  at least one primary engineering source must have a usable file_inspected observation.\n"
            "  incomplete inspection is allowed with low or medium confidence warnings.\n\n"
            "Authority: read_only_planning. Source files are not modified.\n"
            "Next lifecycle step: mission propose --mission <mission-id>, or execute the supplied scope-add next_action."
        ),
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(plan)
    _add_raw_argument(plan)

    scope_add = sub.add_parser(
        "scope-add",
        help="append validated dependent files to mission scope",
        description="Add concrete dependency files to an existing Mission and route the lifecycle back to inspection.",
        epilog=(
            "Prerequisites:\n"
            "  mission exists.\n"
            "  each --scope path is a concrete active Core/UI path accepted by Mission scope policy.\n\n"
            "Next lifecycle step: mission inspect --mission <mission-id>."
        ),
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(scope_add)
    scope_add.add_argument("--scope", action="append", required=True, metavar="PATH", help="Concrete dependency path to add. Repeat for multiple paths.")
    _add_raw_argument(scope_add)

    replan = sub.add_parser(
        "replan",
        help="regenerate plan from current inspection evidence",
        description="Rebuild the architecture plan after additional inspection or resourcefulness reconstruction.",
        epilog="Prerequisite: planning readiness must pass from persisted inspection artifacts.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(replan)
    _add_raw_argument(replan)

    resourcefulness = sub.add_parser(
        "resourcefulness",
        help="reconstruct planning context from existing artifacts",
        description="Use persisted mission artifacts to recover useful planning context when proposal readiness is blocked.",
        epilog="Prerequisite: a plan exists or planning evidence can be reconstructed from inspection observations.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(resourcefulness)
    _add_raw_argument(resourcefulness)

    propose = sub.add_parser(
        "propose",
        help="draft bounded implementation proposal",
        description="Create the implementation proposal from the accepted mission plan without applying source changes.",
        epilog="Prerequisite: planning_complete is true. Next lifecycle step: mission review --mission <mission-id>.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(propose)
    _add_raw_argument(propose)

    verify = sub.add_parser(
        "verify",
        help="run verification for implemented mission work",
        description="Execute the mission verification contract after implementation has been attempted.",
        epilog="Prerequisite: implementation artifacts exist. This records verification state.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(verify)
    _add_raw_argument(verify)

    resume = sub.add_parser(
        "resume",
        help="reconstruct mission continuity",
        description="Read persisted artifacts and report how to resume the next valid lifecycle step.",
        epilog="Prerequisite: mission artifact directory exists. This command is read-only.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(resume)
    _add_raw_argument(resume)

    review = sub.add_parser(
        "review",
        help="record operator proposal decision",
        description="Record the operator decision for the generated implementation proposal.",
        epilog=(
            "Prerequisite: proposal artifact exists. Exactly one decision flag may be supplied.\n"
            "Next lifecycle step after approval: mission implement --mission <mission-id>."
        ),
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(review)
    decision = review.add_mutually_exclusive_group()
    decision.add_argument("--approve", action="store_true", help="Approve the proposal for implementation.")
    decision.add_argument("--reject", action="store_true", help="Reject the proposal and keep implementation blocked.")
    decision.add_argument("--request-changes", action="store_true", help="Request proposal changes before implementation.")
    review.add_argument("--note", default="", metavar="TEXT", help="Operator note to persist with the review decision.")
    _add_raw_argument(review)

    implement = sub.add_parser(
        "implement",
        help="apply approved bounded implementation",
        description="Apply the approved proposal within mission boundaries and record implementation artifacts.",
        epilog="Prerequisite: proposal review is approved. Use --dry-run to inspect the implementation order without applying changes.",
        formatter_class=_mission_formatter(),
    )
    _add_mission_reference(implement)
    implement.add_argument("--dry-run", action="store_true", help="Report implementation order without modifying source files.")
    _add_raw_argument(implement)
    return parser


def _run_mission_command(argv: list[str], raw: bool) -> int:
    from Agency.Core.work.missions import mission_runtime

    parser = _build_mission_parser()
    try:
        args = parser.parse_args(argv)
        _normalize_mission_reference(parser, args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    raw_output = bool(raw or getattr(args, "raw", False))
    try:
        if args.mission_command == "create":
            payload = mission_runtime.create_mission(args.intent, list(args.scope or []))
            print(json.dumps(payload, indent=2))
            return 0
        if args.mission_command == "status":
            print(json.dumps(mission_runtime.mission_status(args.mission), indent=2))
            return 0
        if args.mission_command == "inspect":
            print(json.dumps(mission_runtime.inspect_mission(args.mission), indent=2))
            return 0
        if args.mission_command == "plan":
            print(json.dumps(mission_runtime.plan_mission(args.mission), indent=2))
            return 0
        if args.mission_command == "scope-add":
            print(json.dumps(mission_runtime.add_mission_scope(args.mission, list(args.scope or [])), indent=2))
            return 0
        if args.mission_command == "replan":
            print(json.dumps(mission_runtime.replan_mission(args.mission), indent=2))
            return 0
        if args.mission_command == "resourcefulness":
            print(json.dumps(mission_runtime.resourcefulness_mission(args.mission), indent=2))
            return 0
        if args.mission_command == "propose":
            print(json.dumps(mission_runtime.propose_mission(args.mission), indent=2))
            return 0
        if args.mission_command == "review":
            print(json.dumps(mission_runtime.review_mission(
                args.mission,
                approve=bool(getattr(args, "approve", False)),
                reject=bool(getattr(args, "reject", False)),
                request_changes=bool(getattr(args, "request_changes", False)),
                note=str(getattr(args, "note", "") or ""),
            ), indent=2))
            return 0
        if args.mission_command == "implement":
            print(json.dumps(mission_runtime.implement_mission(args.mission, dry_run=bool(getattr(args, "dry_run", False))), indent=2))
            return 0
        if args.mission_command == "verify":
            print(json.dumps(mission_runtime.verify_mission(args.mission), indent=2))
            return 0
        if args.mission_command == "resume":
            reconstruction = mission_runtime.resume_mission(args.mission)
            if raw_output:
                print(json.dumps(reconstruction, indent=2))
            else:
                print(_render_mission_resume(reconstruction))
            return 0
        if args.mission_command == "list":
            rows = mission_runtime.list_missions()
            if raw_output:
                print(json.dumps({"ok": True, "missions": rows}, indent=2))
            else:
                print(_mission_table(rows))
            return 0
        if args.mission_command == "show":
            reconstruction = mission_runtime.show_mission(args.mission)
            if raw_output:
                print(json.dumps(reconstruction, indent=2))
            else:
                print(_render_mission_show(reconstruction))
            return 0
    except mission_runtime.MissionOperationError as exc:
        print(json.dumps(exc.payload, indent=2))
        return exc.return_code

    print(f"ERR: unknown mission command: {args.mission_command}")
    return 2



def _run_repository_inspect_command(rest: str, raw: bool) -> int:
    from Agency.Core.repository.context import (
        RepositoryContextRequest,
        build_repository_context,
        evidence_summary,
        load_evidence_bundle,
    )

    try:
        parts = shlex.split(rest)
    except ValueError as exc:
        print(f"ERR: invalid inspect command: {exc}")
        return 2

    if not parts:
        print("usage: /inspect <path|symbol|text|status|submit> ...")
        return 2

    mode = parts[0].lower()
    if mode == "status" and len(parts) == 2:
        try:
            bundle = load_evidence_bundle(parts[1])
        except Exception as exc:
            print(f"ERR: inspection status unavailable: {type(exc).__name__}: {exc}")
            return 1
        if raw:
            print(json.dumps(bundle.to_dict()["EvidenceBundle"], indent=2))
        else:
            print(evidence_summary(bundle))
        return 0

    if mode == "submit" and len(parts) == 2:
        request_path = Path(parts[1])
        if not request_path.is_absolute():
            request_path = DASHBOARD_ROOT / request_path
        try:
            text = request_path.read_text(encoding="utf-8")
            from Agency.Core.repository.context import parse_repository_context_request
            request = parse_repository_context_request(text)
            if request is None:
                raise ValueError("not_a_repository_context_request")
        except Exception as exc:
            print(f"ERR: request load failed: {type(exc).__name__}: {exc}")
            return 1
        bundle = build_repository_context(request, persist=True)
    else:
        scope: list[str] = []
        symbols: list[str] = []
        text_queries: list[str] = []
        paths: list[str] = []
        operations: list[str] = ["path_discovery"]
        i = 1
        if mode == "path" and i < len(parts):
            paths.append(parts[i])
            scope.append(parts[i])
            operations.append("text_search")
            i += 1
        elif mode == "symbol" and i < len(parts):
            symbols.append(parts[i])
            text_queries.append(parts[i])
            operations.extend(["symbol_definition", "references", "imports"])
            i += 1
        elif mode == "text" and i < len(parts):
            text_queries.append(parts[i])
            operations.append("text_search")
            i += 1
        else:
            print("usage: /inspect path <path> | symbol <name> --scope <path> | text <text> --scope <path>")
            return 2

        while i < len(parts):
            value = parts[i]
            if value == "--scope" and i + 1 < len(parts):
                i += 1
                while i < len(parts) and not parts[i].startswith("--"):
                    scope.append(parts[i])
                    i += 1
                continue
            if value == "--operation" and i + 1 < len(parts):
                operations.append(parts[i + 1])
                i += 2
                continue
            print(f"ERR: unexpected inspect argument: {value}")
            return 2

        if not scope:
            print("ERR: explicit --scope is required for this inspection.")
            return 2
        request = RepositoryContextRequest(
            request_id="shell-" + hashlib.sha256(rest.encode("utf-8", errors="replace")).hexdigest()[:12],
            objective=f"Shell repository inspection: {rest}",
            include=scope,
            operations=list(dict.fromkeys(operations)),
            symbols=symbols,
            text=text_queries,
            paths=paths or scope,
        )
        bundle = build_repository_context(request, persist=True)

    if raw:
        print(json.dumps(bundle.to_dict()["EvidenceBundle"], indent=2))
    else:
        print(evidence_summary(bundle))
    return 0 if bundle.status not in {"rejected", "failed"} else 1


def _handle_command(line: str, raw: bool) -> tuple[bool, bool, int]:
    command, _, rest = line.partition(" ")
    command = command.lower()
    rest = rest.strip()

    if command == "/exit":
        return raw, False, 0

    if command in {"/help", "/?"}:
        _print_help()
        return raw, True, 0

    if command == "/status":
        _print_status(raw)
        return raw, True, 0

    if command == "/memory":
        _print_memory(raw)
        return raw, True, 0

    if command == "/inspect":
        return raw, True, _run_repository_inspect_command(rest, raw)

    if command == "/refresh":
        return raw, True, _refresh(raw)

    if command == "/propose":
        if not rest:
            print("usage: /propose <task>")
            return raw, True, 2
        return raw, True, _propose(rest, raw)

    if command == "/review":
        if rest.lower() != "latest":
            print("usage: /review latest")
            return raw, True, 2
        return raw, True, _review_latest(raw)

    if command == "/greenlight":
        if rest.lower() != "latest":
            print("usage: /greenlight latest")
            return raw, True, 2
        return raw, True, _greenlight_latest(raw)

    if command == "/apply":
        if rest.lower() != "latest":
            print("usage: /apply latest")
            return raw, True, 2
        return raw, True, _apply_latest(raw)

    if command == "/raw":
        value = rest.lower()
        if value == "on":
            print("raw: on")
            return True, True, 0
        if value == "off":
            print("raw: off")
            return False, True, 0
        print("usage: /raw on|off")
        return raw, True, 2

    if command == "/analyze":
        sub, _, value = rest.partition(" ")
        sub = sub.lower()
        value = value.strip()

        if sub == "refs" and value:
            return raw, True, _analyze_refs(value, raw)

        if sub == "tree" and value:
            return raw, True, _analyze_tree(value, raw)

        print("usage: /analyze refs <text> OR /analyze tree <path>")
        return raw, True, 2

    if command == "/mission":
        if not rest:
            print("usage: /mission <create|status|list|show|resume|inspect|plan|scope-add|replan|resourcefulness|propose|review|implement|verify> ...")
            return raw, True, 2
        try:
            args = shlex.split(rest)
        except Exception as e:
            print(f"ERR: failed to parse arguments: {e}")
            return raw, True, 2
        return raw, True, _run_mission_command(args, raw)

    if command == "/tools":
        from Agency.Core.interfaces.cli.dashboard_cli import available_command_names
        print("Available tools:")
        for name in available_command_names():
            print(f"  - {name}")
        return raw, True, 0

    if command == "/tool":
        if not rest:
            print("usage: /tool <command> [args...]")
            return raw, True, 2

        try:
            args = shlex.split(rest)
        except Exception as e:
            print(f"ERR: failed to parse arguments: {e}")
            return raw, True, 2

        if not args:
            print("usage: /tool <command> [args...]")
            return raw, True, 2

        if args[0] == "help":
            if len(args) > 1:
                args = [args[1], "-h"]
            else:
                args = ["-h"]

        from Agency.Core.interfaces.cli import run_command
        try:
            result = run_command(args)
            if result is not None:
                print(result)
            return raw, True, 0
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            return raw, True, exit_code
        except Exception as e:
            print(f"ERR: {e}")
            return raw, True, 1

    if command == "/observe":
        return raw, False, _print_observe(raw)

    print(f"Unknown command: {command}")
    print("Type /help for commands.")
    return raw, True, 2



# BEGIN editor_shell_state_colors
# Terminal-state colors are presentation signals only. They do not determine
# runtime routing, mission state, repository authority, or memory behavior.
SHELL_STATE_COLORS = {
    "idle": "\033[38;2;169;112;255m",       # purple
    "thinking": "\033[38;2;46;107;63m",     # forest green
    "operating": "\033[38;2;0;184;169m",    # teal
    "done": "\033[38;2;77;141;255m",        # blue
    "approval": "\033[38;2;214;168;75m",    # gold
    "blocked": "\033[38;2;217;83;79m",      # red
}
SHELL_COLOR_RESET = "\033[0m"


def _shell_color_enabled() -> bool:
    """Return whether ANSI shell-state colors should be emitted."""
    import os
    import sys

    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _render_shell_status(
    state: str,
    detail: str = "",
    *,
    color: bool | None = None,
) -> str:
    """Render one explicit shell lifecycle state."""
    normalized = state.strip().lower()
    if normalized not in SHELL_STATE_COLORS:
        raise ValueError(f"unknown shell state: {state}")

    label = f"{AGENT_NAME} [{normalized.upper()}]"
    suffix = f"  {detail}" if detail else ""

    use_color = _shell_color_enabled() if color is None else color
    if not use_color:
        return f"{label}{suffix}"

    return (
        f"{SHELL_STATE_COLORS[normalized]}"
        f"{label}"
        f"{SHELL_COLOR_RESET}"
        f"{suffix}"
    )


def _print_shell_status(state: str, detail: str = "") -> None:
    """Print and immediately flush a shell lifecycle transition."""
    print(_render_shell_status(state, detail), flush=True)


def _render_idle_prompt(*, color: bool | None = None) -> str:
    """Render the interactive prompt as the visible idle state."""
    return f"{_render_shell_status('idle', color=color)}> "


# END editor_shell_state_colors


def repl() -> int:
    raw = False
    last_code = 0

    print(f"{AGENT_NAME} terminal. Type /help for commands, /exit to leave.")

    while True:
        try:
            line = input(_render_idle_prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return last_code

        if not line:
            continue

        if line.startswith("/"):
            raw, keep_running, last_code = _handle_command(line, raw)
            if not keep_running:
                return last_code
            continue

        # At this point the shell has accepted free-form input but has not yet
        # established whether the request is conversational or operational.
        # Forest green therefore means routing/inference is active.
        _print_shell_status("thinking", "Routing request...")

        try:
            last_code = _print_agent_answer(line, raw)
        except Exception as exc:
            _print_shell_status(
                "blocked",
                f"{type(exc).__name__}: {exc}",
            )
            last_code = 1
            continue

        if last_code == 0:
            _print_shell_status("done")
        else:
            _print_shell_status("blocked")


def main(agent_name: str, argv: list[str] | None = None) -> int:
    configure(agent_name)
    argv = argv or []

    if not argv:
        return repl()

    command = argv[0].lower()

    if command == "mission":
        return _run_mission_command(argv[1:], raw=False)

    if command in {"status", "--status"}:
        _print_status(raw=False)
        return 0

    if command in {"help", "--help", "-h"}:
        _print_help()
        return 0

    if command.startswith("/"):
        raw, keep_running, code = _handle_command(" ".join(argv), raw=False)
        return code

    return _print_agent_answer(" ".join(argv), raw=False)


if __name__ == "__main__":
    raise SystemExit(main("Agent"))
