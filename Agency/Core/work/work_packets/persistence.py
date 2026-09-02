from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Agency.Core.repository.git_authority.persistence_guard import guard_ceos_persistence
from Agency.Core.foundation.paths import WORK_PACKETS_ROOT, stable_path
from Agency.Core.work.work_packets.contracts import WorkPacket, WorkPacketStep, now_utc, packet_from_mapping




def work_packets_root() -> Path:
    return WORK_PACKETS_ROOT


def packet_dir(packet_id: str) -> Path:
    return work_packets_root() / packet_id


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    guard_ceos_persistence(payload, record_name=stable_path(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_event(directory: Path, event: str, **fields: Any) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    record = {"ts": now_utc(), "event": event, **fields}
    with (directory / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def save_packet(packet: WorkPacket) -> Path:
    directory = packet_dir(packet.packet_id)
    atomic_json(directory / "packet.json", packet.to_dict())
    steps_dir = directory / "steps"
    for step in packet.steps:
        atomic_json(steps_dir / f"{step.step_id}.json", step.to_dict())
    return directory


def load_packet(packet_id: str) -> WorkPacket:
    return packet_from_mapping(json.loads((packet_dir(packet_id) / "packet.json").read_text(encoding="utf-8")))


def save_task_reference(packet_id: str, editor_task_id: str, payload: dict[str, Any]) -> Path:
    path = packet_dir(packet_id) / "tasks" / f"{editor_task_id}.json"
    atomic_json(path, payload)
    return path


def save_result_reference(packet_id: str, editor_task_id: str, payload: dict[str, Any]) -> Path:
    path = packet_dir(packet_id) / "results" / f"{editor_task_id}.json"
    atomic_json(path, payload)
    return path


def save_authorization(packet_id: str, authorization_id: str, payload: dict[str, Any]) -> Path:
    path = packet_dir(packet_id) / "authorizations" / f"{authorization_id}.json"
    atomic_json(path, payload)
    return path


def load_authorization(packet_id: str, authorization_id: str) -> dict[str, Any]:
    return json.loads((packet_dir(packet_id) / "authorizations" / f"{authorization_id}.json").read_text(encoding="utf-8"))


def save_throw(packet_id: str, throw_id: str, payload: dict[str, Any]) -> Path:
    path = packet_dir(packet_id) / "throws" / f"{throw_id}.json"
    atomic_json(path, payload)
    return path


def stable_packet_path(packet_id: str) -> str:
    return stable_path(packet_dir(packet_id))
