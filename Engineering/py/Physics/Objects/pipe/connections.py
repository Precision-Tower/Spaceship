from typing import Any

import math

from Engineering.py.Physics.Objects.pipe.pipe import pvc_pipe

def _vec(port: dict[str, Any], key: str) -> dict[str, float]:
    value = port.get(key, {})
    return {
        "x": float(value.get("x", 0.0)),
        "y": float(value.get("y", 0.0)),
        "z": float(value.get("z", 0.0)),
    }


def _opposite_direction(direction: dict[str, float]) -> dict[str, float]:
    return {
        "x": -direction["x"],
        "y": -direction["y"],
        "z": -direction["z"],
    }

def pipe_attached_to_port(
    *,
    object_id: str,
    target_port: dict[str, Any],
    length_m: float,
    nominal_size_in: float,
    schedule: str = "SCH40",
    material: str = "pvc_candidate",
    object_type: str = "connector_pipe",
    role: str = "pipe_attached_to_port_candidate",
    assembly_group: str,
    subsystem: str,
    parent_group: str,
) -> dict[str, Any]:
    direction = target_port["direction"]
    port_position = target_port["position_m"]

    dx = float(direction.get("x", 0.0))
    dy = float(direction.get("y", 0.0))
    dz = float(direction.get("z", 0.0))

    center = {
        "x": float(port_position["x"]) + dx * (length_m / 2.0),
        "y": float(port_position["y"]) + dy * (length_m / 2.0),
        "z": float(port_position.get("z", 0.0)) + dz * (length_m / 2.0),
    }

    # Godot cylinder default length axis is Y.
    # This handles XY-plane pipe routing for now.
    angle_rad = math.atan2(dx, dy)
    angle_deg = math.degrees(angle_rad)

    return pvc_pipe(
        object_id=object_id,
        object_type=object_type,
        role=role,
        material=material,
        nominal_size_in=nominal_size_in,
        schedule=schedule,
        length_m=length_m,
        position_m=center,
        display_position_m=center,
        rotation_degrees={"x": 0.0, "y": 0.0, "z": angle_deg},
        contributes_weight=True,
        contributes_buoyancy=False,
        assembly_group=assembly_group,
        subsystem=subsystem,
        parent_group=parent_group,
    )

def fitting_attached_to_pipe_port(
    *,
    fitting: dict[str, Any],
    fitting_port_id: str,
    target_pipe_id: str,
    target_port: dict[str, Any],
    roll_degrees: float = 0.0,
) -> dict[str, Any]:
    """
    Attach a fitting socket to a pipe port.

    The fitting position and socket axis are locked to the pipe port.
    The only intended operator freedom is roll_degrees around that pipe axis.
    """
    placed = dict(fitting)

    target_position = _vec(target_port, "position_m")
    target_direction = _vec(target_port, "direction")

    placed["position_m"] = target_position
    placed["display_position_m"] = target_position

    placed["placement"] = {
        "mode": "pipe_port_locked_roll",
        "attached_to": {
            "object_id": target_pipe_id,
            "port_id": target_port.get("port_id", "missing"),
        },
        "fitting_port_id": fitting_port_id,
        "locked_axis": {
            "source": f"{target_pipe_id}.{target_port.get('port_id', 'missing')}.direction",
            "world_direction": target_direction,
        },
        "required_fitting_port_direction": _opposite_direction(target_direction),
        "roll_degrees": roll_degrees,
        "editable_degrees_of_freedom": [
            "roll_degrees_about_locked_axis"
        ],
        "blocked_degrees_of_freedom": [
            "free_position",
            "free_rotation_x",
            "free_rotation_y",
            "free_rotation_z",
        ],
    }

    placed["roll_degrees"] = roll_degrees

    placed.setdefault("blocked_interpretations", [])
    placed["blocked_interpretations"].extend([
        "roll_alignment_equals_pressure_safe_connection",
        "socket_alignment_equals_leak_free_joint",
        "visual_pipe_connection_equals_validated_pressure_boundary",
    ])

    return placed

def get_open_ports(obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        port for port in obj.get("ports", [])
        if port.get("state") == "open"
    ]


def can_connect(port_a: dict[str, Any], port_b: dict[str, Any]) -> bool:
    if port_a.get("state") != "open" or port_b.get("state") != "open":
        return False

    if port_a.get("connection_type") != port_b.get("connection_type"):
        return False

    if port_a.get("nominal_radius_m") != port_b.get("nominal_radius_m"):
        return False

    return True


def build_connection_record(
    *,
    connection_id: str,
    from_object_id: str,
    from_port_id: str,
    to_object_id: str,
    to_port_id: str,
    connection_role: str = "pipe_connection_candidate",
    evidence_state: str = "calculated_candidate",
) -> dict[str, Any]:
    return {
        "connection_id": connection_id,
        "from_object_id": from_object_id,
        "from_port_id": from_port_id,
        "to_object_id": to_object_id,
        "to_port_id": to_port_id,
        "connection_role": connection_role,
        "evidence_state": evidence_state,
        "prohibited_interpretations": [
            "connection_record_equals_leak_free",
            "connection_record_equals_pressure_safe",
            "visual_alignment_equals_physical_connection",
            "pipe_topology_equals_build_ready",
        ],
    }
