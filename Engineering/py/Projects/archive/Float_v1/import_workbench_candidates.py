import json
from pathlib import Path
from typing import Any

from Engineering.py.Physics.Objects.pipe.pipe import pvc_pipe
from Engineering.py.Physics.Objects.pipe.fittings import elbow_90
from Engineering.py.Physics.Objects.pipe.connections import (
    fitting_attached_to_pipe_port,
    build_connection_record,
)

SOURCE_PATH = Path(__file__).resolve().parent / "workbench_candidate_commands.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "workbench_candidate_packet.json"
EVIDENCE_STATE = "ui_imported_candidate"
SUPPORTED_PRIMITIVES = {
    "sphere",
    "box",
    "cylinder",
    "plane",
    "cone",
    "torus",
}
PROHIBITED_INTERPRETATIONS = [
    "candidate_packet_equals_engineering_validation",
    "ui_imported_candidate_equals_project_assembly_member",
    "ghost_position_equals_validated_geometry",
    "candidate_object_equals_physical_truth",
]


def main() -> None:
    packet = import_workbench_candidates()
    OUTPUT_PATH.write_text(
        json.dumps(packet, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {OUTPUT_PATH} "
        f"objects={len(packet['objects'])} "
        f"unresolved_commands={len(packet['unresolved_commands'])}"
    )


def import_workbench_candidates() -> dict[str, Any]:
    source_packet = _load_source_packet()
    objects: list[dict[str, Any]] = []
    unresolved_commands: list[dict[str, Any]] = []

    for command in source_packet.get("commands", []):
        if not isinstance(command, dict):
            unresolved_commands.append(
                {
                    "unresolved_reason": "command_not_object",
                    "source_command": command,
                }
            )
            continue

        candidate_object = _candidate_object_from_command(command)
        if candidate_object is None:
            unresolved_commands.append(
                {
                    "unresolved_reason": _unresolved_reason(command),
                    "source_command": command,
                }
            )
            continue

        objects.append(candidate_object)

    return {
        "packet_type": "workbench_candidate_packet",
        "evidence_state": EVIDENCE_STATE,
        "source_packet": SOURCE_PATH.name,
        "objects": objects,
        "unresolved_commands": unresolved_commands,
        "prohibited_interpretations": PROHIBITED_INTERPRETATIONS,
    }

def _candidate_object_from_command(command: dict[str, Any]) -> dict[str, Any] | None:
    command_type = str(command.get("command_type", ""))

    if command_type == "create_primitive":
        return _primitive_candidate_from_command(command)

    if command_type == "create_pipe_candidate":
        return _pipe_candidate_from_command(command)
    
    if command_type == "attach_elbow_90_candidate":
        return _elbow_candidate_from_command(command)

    return None

def _candidate_object_from_command(command: dict[str, Any]) -> dict[str, Any] | None:
    command_type = str(command.get("command_type", ""))

    if command_type == "create_primitive":
        return _primitive_candidate_from_command(command)

    if command_type == "create_pipe_candidate":
        return _pipe_candidate_from_command(command)

    if command_type == "attach_elbow_90_candidate":
        return _elbow_candidate_from_command(command)

    return None

def _elbow_candidate_from_command(command: dict[str, Any]) -> dict[str, Any] | None:
    target_object_id = str(command.get("target_object_id", ""))
    target_port_id = str(command.get("target_port_id", ""))
    fitting_port_id = str(command.get("fitting_port_id", "A"))
    roll_degrees = float(command.get("roll_degrees", 0.0))

    source_packet = _load_existing_candidate_packet()
    target_object = _find_object(source_packet.get("objects", []), target_object_id)
    if target_object is None:
        command["unresolved_reason"] = "target_object_not_found"
        return None

    target_port = _find_port(target_object, target_port_id)
    if target_port is None:
        command["unresolved_reason"] = "target_port_not_found"
        return None

    target_position = target_port.get("position_m", target_object.get("position_m", {}))

    elbow_raw = elbow_90(
        object_id=f"elbow_90_for_{target_object_id}_{target_port_id}",
        nominal_size_in=1.0,
        schedule="SCH40",
        position_m=target_position,
        display_position_m=target_position,
        assembly_group="workbench_candidates",
        subsystem="pipe",
        parent_group="workbench_candidates",
        role="workbench_elbow_90_candidate",
    )

    elbow = fitting_attached_to_pipe_port(
        fitting=elbow_raw,
        fitting_port_id=fitting_port_id,
        target_pipe_id=target_object_id,
        target_port=target_port,
        roll_degrees=roll_degrees,
    )

    connection = build_connection_record(
        connection_id=f"connection_{target_object_id}_{target_port_id}_to_{elbow['object_id']}_{fitting_port_id}",
        from_object_id=target_object_id,
        from_port_id=target_port_id,
        to_object_id=elbow["object_id"],
        to_port_id=fitting_port_id,
        connection_role="pipe_to_elbow_90_candidate",
    )

    elbow["connections"] = [connection]
    elbow["evidence_state"] = EVIDENCE_STATE
    elbow["source_command"] = command
    elbow["candidate_state"] = "ui_imported_candidate"

    return elbow

def _load_existing_candidate_packet() -> dict[str, Any]:
    if not OUTPUT_PATH.exists():
        return {"objects": []}

    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def _find_object(objects: list[dict[str, Any]], object_id: str) -> dict[str, Any] | None:
    for obj in objects:
        if str(obj.get("object_id", "")) == object_id:
            return obj
    return None


def _find_port(obj: dict[str, Any], port_id: str) -> dict[str, Any] | None:
    for port in obj.get("ports", []):
        if isinstance(port, dict) and str(port.get("port_id", "")) == port_id:
            return port
    return None

def _load_source_packet() -> dict[str, Any]:
    return json.loads(SOURCE_PATH.read_text(encoding="utf-8"))


def _primitive_candidate_from_command(command: dict[str, Any]) -> dict[str, Any] | None:

    primitive = str(command.get("primitive", command.get("item", "")))
    if primitive not in SUPPORTED_PRIMITIVES:
        return None

    position_m = _vector_dict(command.get("position_m", command.get("world_position", {})))
    rotation_degrees = _vector_dict(command.get("rotation_degrees", {}))
    scale_m = _vector_dict(command.get("scale_m", {"x": 1.0, "y": 1.0, "z": 1.0}), 1.0)

    return {
        "object_id": str(command.get("object_id", f"candidate_{primitive}")),
        "object_type": "primitive_candidate",
        "primitive": primitive,
        "position_m": position_m,
        "rotation_degrees": rotation_degrees,
        "scale_m": scale_m,
        "evidence_state": EVIDENCE_STATE,
        "source_command": command,
        "render": {
            "primitive": primitive,
            "display_position_m": position_m,
            "rotation_degrees": rotation_degrees,
        },
    }

def _pipe_candidate_from_command(command: dict[str, Any]) -> dict[str, Any]:
    position_m = _vector_dict(command.get("position_m", command.get("world_position", {})))
    rotation_degrees = {"x": 0.0, "y": 0.0, "z": -90.0}

    pipe = pvc_pipe(
        object_id=str(command.get("object_id", "workbench_pipe_candidate_001")),
        object_type="connector_pipe",
        role="workbench_pipe_candidate",
        material="pvc_candidate",
        nominal_size_in=1.0,
        schedule="SCH40",
        length_m=1.0,
        position_m=position_m,
        display_position_m=position_m,
        rotation_degrees=rotation_degrees,
        contributes_weight=True,
        contributes_buoyancy=False,
        assembly_group="workbench_candidates",
        subsystem="pipe",
        parent_group="workbench_candidates",
    )

    pipe["evidence_state"] = EVIDENCE_STATE
    pipe["source_command"] = command
    pipe["candidate_state"] = "ui_imported_candidate"

    pipe.setdefault("blocked_interpretations", [])
    pipe["blocked_interpretations"].extend([
        "ui_pipe_candidate_equals_routed_pipe_system",
        "ghost_pipe_equals_pressure_safe_pipe",
        "candidate_pipe_position_equals_validated_installation",
    ])

    return pipe

def _elbow_candidate_from_command(command: dict[str, Any]) -> dict[str, Any] | None:
    target_object_id = str(command.get("target_object_id", ""))
    target_port_id = str(command.get("target_port_id", ""))
    fitting_port_id = str(command.get("fitting_port_id", "A"))
    roll_degrees = float(command.get("roll_degrees", 0.0))

    source_packet = _load_existing_candidate_packet()
    target_object = _find_object(source_packet.get("objects", []), target_object_id)
    if target_object is None:
        command["unresolved_reason"] = "target_object_not_found"
        return None

    target_port = _find_port(target_object, target_port_id)
    if target_port is None:
        command["unresolved_reason"] = "target_port_not_found"
        return None

    target_position = target_port.get("position_m", target_object.get("position_m", {}))

    elbow_raw = elbow_90(
        object_id=f"elbow_90_for_{target_object_id}_{target_port_id}",
        nominal_size_in=1.0,
        schedule="SCH40",
        position_m=target_position,
        display_position_m=target_position,
        assembly_group="workbench_candidates",
        subsystem="pipe",
        parent_group="workbench_candidates",
        role="workbench_elbow_90_candidate",
    )

    elbow = fitting_attached_to_pipe_port(
        fitting=elbow_raw,
        fitting_port_id=fitting_port_id,
        target_pipe_id=target_object_id,
        target_port=target_port,
        roll_degrees=roll_degrees,
    )

    connection = build_connection_record(
        connection_id=f"connection_{target_object_id}_{target_port_id}_to_{elbow['object_id']}_{fitting_port_id}",
        from_object_id=target_object_id,
        from_port_id=target_port_id,
        to_object_id=elbow["object_id"],
        to_port_id=fitting_port_id,
        connection_role="pipe_to_elbow_90_candidate",
    )

    elbow["connections"] = [connection]
    elbow["evidence_state"] = EVIDENCE_STATE
    elbow["source_command"] = command
    elbow["candidate_state"] = "ui_imported_candidate"

    return elbow

def _unresolved_reason(command: dict[str, Any]) -> str:
    command_type = str(command.get("command_type", ""))

    if command_type == "create_primitive":
        primitive = str(command.get("primitive", command.get("item", "")))
        if primitive not in SUPPORTED_PRIMITIVES:
            return "unsupported_primitive"
        return "unresolved_primitive_command"

    if command_type == "create_barrel_candidate":
        return "unsupported_barrel_candidate"

    if command_type == "create_pipe_candidate":
        return "pipe_candidate_failed_to_import"

    return "unsupported_command_type"

def _load_existing_candidate_packet() -> dict[str, Any]:
    if not OUTPUT_PATH.exists():
        return {"objects": []}
    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def _find_object(objects: list[dict[str, Any]], object_id: str) -> dict[str, Any] | None:
    for obj in objects:
        if str(obj.get("object_id", "")) == object_id:
            return obj
    return None


def _find_port(obj: dict[str, Any], port_id: str) -> dict[str, Any] | None:
    for port in obj.get("ports", []):
        if isinstance(port, dict) and str(port.get("port_id", "")) == port_id:
            return port
    return None

def _vector_dict(value: Any, default: float = 0.0) -> dict[str, float]:
    if not isinstance(value, dict):
        value = {}

    return {
        "x": float(value.get("x", default)),
        "y": float(value.get("y", default)),
        "z": float(value.get("z", default)),
    }


if __name__ == "__main__":
    main()

