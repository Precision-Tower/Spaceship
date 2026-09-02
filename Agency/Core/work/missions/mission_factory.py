from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from Agency.Core.foundation.paths import MISSIONS_ROOT, stable_path
from Agency.Core.work.missions.mission_spec import (
    ALLOWED_MISSION_STATES,
    MissionSpec,
    MissionSpecValidationError,
    build_mission_spec,
    require_valid_mission_spec,
)



class MissionFactoryError(RuntimeError):
    def __init__(self, message: str, *, phase: str, files_written: list[str] | None = None) -> None:
        super().__init__(message)
        self.phase = phase
        self.files_written = files_written or []


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mission_number_from_name(name: str) -> int | None:
    if not name.startswith("mission-"):
        return None
    tail = name.removeprefix("mission-")
    if not tail.isdigit():
        return None
    value = int(tail)
    return value if value > 0 else None


def allocate_mission_id(*, root: Path | None = None) -> str:
    missions_root = root or MISSIONS_ROOT
    highest = 0
    if missions_root.exists():
        for path in missions_root.iterdir():
            if not path.is_dir():
                continue
            number = mission_number_from_name(path.name)
            if number is not None:
                highest = max(highest, number)
    return f"mission-{highest + 1}"


def mission_dir(mission_id: str, *, root: Path | None = None) -> Path:
    return (root or MISSIONS_ROOT) / mission_id


def write_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def append_history_event(mission_id: str, event: dict[str, Any], *, root: Path | None = None) -> None:
    path = mission_dir(mission_id, root=root) / "history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=False) + "\n")


def create_mission(title: str, *, owner: str, objective: str | None = None, root: Path | None = None) -> dict[str, Any]:
    spec = build_mission_spec(
        mission_id=allocate_mission_id(root=root),
        title=title,
        owner=owner,
        objective=objective or title,
    )
    return create_mission_from_spec(spec, root=root)


def create_mission_from_spec(spec: MissionSpec, *, root: Path | None = None) -> dict[str, Any]:
    root = root or MISSIONS_ROOT
    spec = require_valid_mission_spec(spec)
    mission_path = mission_dir(spec.mission_id, root=root)
    preflight_errors = _preflight_create(spec, mission_path, root=root)
    if preflight_errors:
        raise MissionSpecValidationError(preflight_errors)

    files = render_mission_files(spec)
    created: list[str] = []
    preserved: list[str] = []
    try:
        for relative_path, text in files.items():
            path = mission_path / relative_path
            if write_if_missing(path, text):
                created.append(stable_path(path))
            else:
                preserved.append(stable_path(path))
    except Exception as exc:
        raise MissionFactoryError(str(exc), phase="filesystem", files_written=created) from exc

    if spec.parent_mission_id:
        try:
            _attach_child_to_parent(spec.parent_mission_id, spec.mission_id, root=root)
        except Exception as exc:
            raise MissionFactoryError(str(exc), phase="parent_relationship", files_written=created) from exc

    return {
        "status": "created",
        "mission_id": spec.mission_id,
        "mission_dir": stable_path(mission_path),
        "state": spec.initial_state,
        "owner": spec.owner,
        "objective": spec.objective,
        "created": created,
        "preserved_existing": preserved,
        "next_commands": [
            f"python run.py mission inspect --mission {spec.mission_id}",
            f"python run.py mission transition --mission {spec.mission_id} --state running --reason \"started\"",
        ],
        "authority": "mission_creation_only_not_execution_authority",
        "mission_spec": spec.to_dict(),
    }


def _preflight_create(spec: MissionSpec, mission_path: Path, *, root: Path) -> list[str]:
    errors: list[str] = []
    if mission_path.exists():
        errors.append(f"mission already exists: {spec.mission_id}")
    if spec.parent_mission_id:
        parent_path = mission_dir(spec.parent_mission_id, root=root)
        if not (parent_path / "mission.json").exists():
            errors.append(f"parent mission not found: {spec.parent_mission_id}")
    return errors


def render_mission_files(spec: MissionSpec) -> dict[str, str]:
    created_event = history_event(
        spec.mission_id,
        event_type="created",
        actor="mission_factory",
        reason="mission created from MissionSpec",
        after_state=spec.initial_state,
        evidence=["mission.json", "state.json"],
        timestamp=spec.created_at,
    )
    return {
        "mission.json": json.dumps({"MissionSpec": spec.to_dict()}, indent=2, sort_keys=False) + "\n",
        "state.json": json.dumps(initial_state_payload(spec), indent=2, sort_keys=False) + "\n",
        "history.jsonl": json.dumps(created_event, sort_keys=False) + "\n",
        "outputs/.keep": "",
    }


def initial_state_payload(spec: MissionSpec) -> dict[str, Any]:
    tasks = [
        {"task_id": task.task_id, "title": task.title, "status": task.status}
        for task in spec.tasks
    ]
    return {
        "MissionState": {
            "mission_id": spec.mission_id,
            "title": spec.title,
            "initial_owner": spec.owner,
            "owner": spec.owner,
            "objective": spec.objective,
            "state": spec.initial_state,
            "progress": progress_from_tasks(tasks),
            "tasks": tasks,
            "inputs": list(spec.inputs),
            "context": dict(spec.context),
            "constraints": list(spec.constraints),
            "resources": list(spec.resources),
            "relationships": {
                "parent_mission_id": spec.parent_mission_id,
                "child_mission_ids": [],
            },
            "outputs": [],
            "completion": None,
            "failure": None,
            "updated_at": spec.created_at,
            "authority": "mission_state_record_not_execution_authority",
        }
    }


def progress_from_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    by_state: dict[str, list[str]] = {
        "pending_tasks": [],
        "active_tasks": [],
        "completed_tasks": [],
        "skipped_tasks": [],
        "blocked_tasks": [],
        "failed_tasks": [],
    }
    mapping = {
        "pending": "pending_tasks",
        "active": "active_tasks",
        "completed": "completed_tasks",
        "skipped": "skipped_tasks",
        "blocked": "blocked_tasks",
        "failed": "failed_tasks",
    }
    for task in tasks:
        key = mapping.get(str(task.get("status")))
        if key:
            by_state[key].append(str(task.get("task_id")))
    return by_state


def history_event(
    mission_id: str,
    *,
    event_type: str,
    actor: str,
    reason: str,
    before_state: str | None = None,
    after_state: str | None = None,
    evidence: list[str] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    return {
        "mission_id": mission_id,
        "event_type": event_type,
        "actor": actor,
        "reason": reason,
        "timestamp": timestamp or utc_now(),
        "before_state": before_state,
        "after_state": after_state,
        "evidence": evidence or [],
        "authority": "mission_history_record_not_execution_authority",
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load_mission_records(mission_id: str, *, root: Path | None = None) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    path = mission_dir(mission_id, root=root)
    mission_json = path / "mission.json"
    state_json = path / "state.json"
    if not mission_json.exists():
        raise FileNotFoundError(f"mission_not_found: {mission_id}")
    if not state_json.exists():
        raise FileNotFoundError(f"mission_state_not_found: {mission_id}")
    return path, read_json(mission_json), read_json(state_json)


def inspect_mission(mission_id: str, *, root: Path | None = None) -> dict[str, Any]:
    path, mission, state = load_mission_records(mission_id, root=root)
    current = state.get("MissionState") or {}
    spec = mission.get("MissionSpec") or {}
    identity = spec.get("identity") or {}
    history_path = path / "history.jsonl"
    history_count = 0
    if history_path.exists():
        history_count = len([line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()])
    return {
        "status": "found",
        "mission_id": mission_id,
        "mission_dir": stable_path(path),
        "title": identity.get("title"),
        "created_at": identity.get("created_at"),
        "initial_owner": identity.get("owner"),
        "owner": current.get("owner"),
        "objective": current.get("objective") or spec.get("objective"),
        "state": current.get("state"),
        "progress": current.get("progress") or {},
        "completed_tasks": (current.get("progress") or {}).get("completed_tasks") or [],
        "pending_tasks": (current.get("progress") or {}).get("pending_tasks") or [],
        "outputs": current.get("outputs") or [],
        "completion": current.get("completion"),
        "failure": current.get("failure"),
        "relationships": current.get("relationships") or {},
        "history_events": history_count,
        "authority": "mission_inspection_not_execution_authority",
    }


def transition_mission_state(
    mission_id: str,
    new_state: str,
    *,
    reason: str,
    summary: str | None = None,
    produced_artifacts: list[str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    new_state = str(new_state).strip()
    reason = str(reason).strip()
    if new_state not in ALLOWED_MISSION_STATES:
        raise MissionSpecValidationError([f"invalid lifecycle state: {new_state}"])
    if not reason:
        raise MissionSpecValidationError(["transition reason is required"])
    if new_state == "completed" and not (summary or "").strip():
        raise MissionSpecValidationError(["completion summary is required"])

    path, _mission, state = load_mission_records(mission_id, root=root)
    current = state.get("MissionState") or {}
    before_state = str(current.get("state") or "")
    now = utc_now()
    current["state"] = new_state
    current["updated_at"] = now

    if new_state == "completed":
        current["completion"] = {
            "state": "completed",
            "completed_at": now,
            "summary": summary,
            "produced_artifacts": produced_artifacts or [],
        }
        current["failure"] = None
    elif new_state == "failed":
        current["failure"] = {
            "state": "failed",
            "failed_at": now,
            "reason": reason,
            "produced_artifacts": current.get("outputs") or [],
            "remaining_work": (current.get("progress") or {}).get("pending_tasks") or [],
        }

    write_json(path / "state.json", state)
    append_history_event(
        mission_id,
        history_event(
            mission_id,
            event_type="state_transition",
            actor="mission_factory",
            reason=reason,
            before_state=before_state,
            after_state=new_state,
            evidence=["state.json"],
        ),
        root=root,
    )
    return {
        "status": "transitioned",
        "mission_id": mission_id,
        "from_state": before_state,
        "to_state": new_state,
        "state": new_state,
        "authority": "mission_state_transition_record_not_execution_authority",
    }


def handoff_mission(mission_id: str, new_owner: str, *, reason: str, root: Path | None = None) -> dict[str, Any]:
    new_owner = str(new_owner).strip()
    reason = str(reason).strip()
    if not new_owner:
        raise MissionSpecValidationError(["new owner is required"])
    if not reason:
        raise MissionSpecValidationError(["handoff reason is required"])
    path, _mission, state = load_mission_records(mission_id, root=root)
    current = state.get("MissionState") or {}
    old_owner = current.get("owner")
    current["owner"] = new_owner
    current["updated_at"] = utc_now()
    write_json(path / "state.json", state)
    append_history_event(
        mission_id,
        history_event(
            mission_id,
            event_type="ownership_handoff",
            actor="mission_factory",
            reason=reason,
            evidence=["state.json"],
        ),
        root=root,
    )
    return {
        "status": "owner_changed",
        "mission_id": mission_id,
        "from_owner": old_owner,
        "to_owner": new_owner,
        "authority": "mission_ownership_record_not_execution_authority",
    }


def _attach_child_to_parent(parent_id: str, child_id: str, *, root: Path) -> None:
    parent_path, _mission, state = load_mission_records(parent_id, root=root)
    current = state.get("MissionState") or {}
    relationships = current.setdefault("relationships", {})
    children = relationships.setdefault("child_mission_ids", [])
    if child_id not in children:
        children.append(child_id)
    current["updated_at"] = utc_now()
    write_json(parent_path / "state.json", state)
    append_history_event(
        parent_id,
        history_event(
            parent_id,
            event_type="child_mission_created",
            actor="mission_factory",
            reason=f"child mission created: {child_id}",
            evidence=[f"../{child_id}/mission.json", "state.json"],
        ),
        root=root,
    )


def parse_context(values: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise MissionSpecValidationError([f"context entry must use key=value: {item}"], phase="input")
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _ask_required(prompt: str, *, input_func: Callable[[str], str]) -> str:
    return input_func(prompt).strip()


def _ask_optional(prompt: str, default: str | None, *, input_func: Callable[[str], str]) -> str | None:
    suffix = f" [{default}]" if default is not None else ""
    value = input_func(f"{prompt}{suffix}: ").strip()
    return value or default


def _ask_list(prompt: str, *, input_func: Callable[[str], str]) -> list[str]:
    value = input_func(f"{prompt} [comma-separated, blank for none]: ").strip()
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _ask_context(*, input_func: Callable[[str], str]) -> dict[str, str]:
    value = input_func("context [key=value comma-separated, blank for none]: ").strip()
    if not value:
        return {}
    return parse_context([part.strip() for part in value.split(",") if part.strip()])


def _ask_bool(prompt: str, default: bool, *, input_func: Callable[[str], str]) -> bool:
    marker = "Y/n" if default else "y/N"
    while True:
        value = input_func(f"{prompt} [{marker}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer y or n.")


def collect_interactive_mission_spec(
    *,
    mission_id: str | None = None,
    created_at: str | None = None,
    input_func: Callable[[str], str] = input,
    root: Path | None = None,
) -> MissionSpec | None:
    title = _ask_required("mission title: ", input_func=input_func)
    owner = _ask_required("owner agent: ", input_func=input_func)
    objective = _ask_optional("objective", title, input_func=input_func) or title
    inputs = _ask_list("inputs", input_func=input_func)
    context = _ask_context(input_func=input_func)
    constraints = _ask_list("constraints", input_func=input_func)
    resources = _ask_list("resources", input_func=input_func)
    tasks = _ask_list("tasks", input_func=input_func)
    parent = _ask_optional("parent mission", None, input_func=input_func)
    spec = build_mission_spec(
        mission_id=mission_id or allocate_mission_id(root=root),
        title=title,
        owner=owner,
        objective=objective,
        created_at=created_at,
        inputs=inputs,
        context=context,
        constraints=constraints,
        resources=resources,
        tasks=tasks,
        parent_mission_id=parent,
    )
    require_valid_mission_spec(spec)
    print("Normalized MissionSpec:")
    print(json.dumps(spec.to_dict(), indent=2))
    confirmed = _ask_bool("create this mission", False, input_func=input_func)
    return spec if confirmed else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python run.py mission",
        description="Create, inspect, and record Dashboard Missions.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("title_arg", nargs="?", help="compatibility title; objective defaults to this title")
    create.add_argument("--title", default=None)
    create.add_argument("--owner", default=None)
    create.add_argument("--objective", default=None)
    create.add_argument("--input", action="append", dest="inputs", default=None)
    create.add_argument("--context", action="append", default=None, help="key=value")
    create.add_argument("--constraint", action="append", dest="constraints", default=None)
    create.add_argument("--resource", action="append", dest="resources", default=None)
    create.add_argument("--task", action="append", dest="tasks", default=None, help="task-id:title[:status] or title")
    create.add_argument("--parent", default=None)
    create.add_argument("--non-interactive", action="store_true")
    create.add_argument("--raw", "--json", dest="raw", action="store_true")

    inspect = sub.add_parser("inspect")
    inspect.add_argument("--mission", required=True)
    inspect.add_argument("--raw", "--json", dest="raw", action="store_true")

    transition = sub.add_parser("transition")
    transition.add_argument("--mission", required=True)
    transition.add_argument("--state", required=True, choices=tuple(sorted(ALLOWED_MISSION_STATES)))
    transition.add_argument("--reason", required=True)
    transition.add_argument("--summary", default=None)
    transition.add_argument("--artifact", action="append", dest="artifacts", default=None)
    transition.add_argument("--raw", "--json", dest="raw", action="store_true")

    handoff = sub.add_parser("handoff")
    handoff.add_argument("--mission", required=True)
    handoff.add_argument("--owner", required=True)
    handoff.add_argument("--reason", required=True)
    handoff.add_argument("--raw", "--json", dest="raw", action="store_true")
    return parser


def _has_declarative_create_values(args: argparse.Namespace) -> bool:
    for name in ("title", "owner", "objective", "inputs", "context", "constraints", "resources", "tasks", "parent"):
        if getattr(args, name, None) is not None:
            return True
    return False


def spec_from_create_args(
    args: argparse.Namespace,
    *,
    mission_id: str | None = None,
    created_at: str | None = None,
    input_func: Callable[[str], str] = input,
    root: Path | None = None,
) -> MissionSpec | None:
    declarative = _has_declarative_create_values(args)
    positional_compat = bool(args.title_arg) and args.title is None
    if not args.title_arg and not declarative:
        if args.non_interactive:
            raise MissionSpecValidationError(["identity.title is required", "identity.owner is required", "objective is required"], phase="input")
        return collect_interactive_mission_spec(mission_id=mission_id, created_at=created_at, input_func=input_func, root=root)

    title = args.title or args.title_arg
    if not title:
        raise MissionSpecValidationError(["identity.title is required"], phase="input")
    owner = args.owner
    if not owner:
        if args.non_interactive:
            raise MissionSpecValidationError(["identity.owner is required"], phase="input")
        owner = _ask_required("owner agent: ", input_func=input_func)
    objective = args.objective
    if not objective:
        if positional_compat:
            objective = title
        elif args.non_interactive:
            raise MissionSpecValidationError(["objective is required"], phase="input")
        else:
            objective = _ask_optional("objective", title, input_func=input_func) or title
    spec = build_mission_spec(
        mission_id=mission_id or allocate_mission_id(root=root),
        title=title,
        owner=owner,
        objective=objective,
        created_at=created_at,
        inputs=args.inputs,
        context=parse_context(args.context),
        constraints=args.constraints,
        resources=args.resources,
        tasks=args.tasks,
        parent_mission_id=args.parent,
    )
    require_valid_mission_spec(spec)
    return spec


def format_result(result: dict[str, Any]) -> str:
    lines = [
        "MISSION_CREATED",
        f"status: {result.get('status', 'created')}",
        f"mission_id: {result['mission_id']}",
        f"mission_dir: {result['mission_dir']}",
        f"state: {result['state']}",
        f"owner: {result['owner']}",
        f"objective: {result['objective']}",
        f"authority: {result['authority']}",
        "",
        "created:",
    ]
    created = result.get("created") or []
    if created:
        lines.extend(f"  - {item}" for item in created)
    else:
        lines.append("  - none")
    lines.append("")
    lines.append("preserved_existing:")
    preserved = result.get("preserved_existing") or []
    if preserved:
        lines.extend(f"  - {item}" for item in preserved)
    else:
        lines.append("  - none")
    lines.append("")
    lines.append("next_commands:")
    lines.extend(f"  - {item}" for item in result.get("next_commands", []))
    return "\n".join(lines)


def format_inspection(result: dict[str, Any]) -> str:
    lines = [
        "MISSION_INSPECTION",
        f"status: {result['status']}",
        f"mission_id: {result['mission_id']}",
        f"state: {result['state']}",
        f"owner: {result['owner']}",
        f"objective: {result['objective']}",
        f"history_events: {result['history_events']}",
        f"authority: {result['authority']}",
        "",
        "completed_tasks:",
    ]
    completed = result.get("completed_tasks") or []
    if completed:
        lines.extend(f"  - {item}" for item in completed)
    else:
        lines.append("  - none")
    lines.append("pending_tasks:")
    pending = result.get("pending_tasks") or []
    if pending:
        lines.extend(f"  - {item}" for item in pending)
    else:
        lines.append("  - none")
    lines.append("outputs:")
    outputs = result.get("outputs") or []
    if outputs:
        lines.extend(f"  - {item}" for item in outputs)
    else:
        lines.append("  - none")
    if result.get("failure"):
        lines.append(f"failure: {json.dumps(result['failure'], sort_keys=True)}")
    if result.get("completion"):
        lines.append(f"completion: {json.dumps(result['completion'], sort_keys=True)}")
    return "\n".join(lines)


def format_failure(*, phase: str, errors: list[str], files_written: list[str] | None = None) -> str:
    lines = ["MISSION_FAILED", "status: failed", f"phase: {phase}", "files_written:"]
    written = files_written or []
    if written:
        lines.extend(f"  - {item}" for item in written)
    else:
        lines.append("  - none")
    lines.append("errors:")
    lines.extend(f"  - {error}" for error in errors)
    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
    *,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            spec = spec_from_create_args(args, input_func=input_func)
            if spec is None:
                output_func("MISSION_CREATE_CANCELLED")
                output_func("status: cancelled")
                return 2
            result = create_mission_from_spec(spec)
            output_func(json.dumps(result, indent=2) if args.raw else format_result(result))
            return 0
        if args.command == "inspect":
            result = inspect_mission(args.mission)
            output_func(json.dumps(result, indent=2) if args.raw else format_inspection(result))
            return 0
        if args.command == "transition":
            result = transition_mission_state(
                args.mission,
                args.state,
                reason=args.reason,
                summary=args.summary,
                produced_artifacts=args.artifacts,
            )
            output_func(json.dumps(result, indent=2))
            return 0
        if args.command == "handoff":
            result = handoff_mission(args.mission, args.owner, reason=args.reason)
            output_func(json.dumps(result, indent=2))
            return 0
    except MissionSpecValidationError as exc:
        output_func(format_failure(phase=exc.phase, errors=exc.errors))
        return 1
    except MissionFactoryError as exc:
        output_func(format_failure(phase=exc.phase, errors=[str(exc)], files_written=exc.files_written))
        return 1
    except Exception as exc:
        output_func(format_failure(phase="unknown", errors=[str(exc)]))
        return 1

    output_func(format_failure(phase="input", errors=[f"unknown command: {args.command}"]))
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
