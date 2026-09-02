import math
from typing import Any

from Engineering.py.Physics.Objects.pipe.pipe import pipe


def pipe_between_ports(
    *,
    object_id: str,
    start_port: dict[str, Any],
    end_port: dict[str, Any],
    material,
    outer_radius_m: float,
    wall_thickness_m: float,
    object_type: str = "pipe",
    role: str = "pipe_segment_between_ports",
    assembly_group: str = "pipe_route",
    subsystem: str = "pipe",
    parent_group: str = "pipe_route",
    contributes_weight: bool = True,
    contributes_buoyancy: bool = False,
) -> dict:
    start = start_port["position_m"]
    end = end_port["position_m"]

    dx = float(end["x"]) - float(start["x"])
    dy = float(end["y"]) - float(start["y"])
    dz = float(end["z"]) - float(start["z"])

    length_m = math.sqrt(dx * dx + dy * dy + dz * dz)

    if length_m <= 0.0:
        raise ValueError("pipe_between_ports requires two different port positions")

    midpoint = {
        "x": (float(start["x"]) + float(end["x"])) / 2.0,
        "y": (float(start["y"]) + float(end["y"])) / 2.0,
        "z": (float(start["z"]) + float(end["z"])) / 2.0,
    }

    rotation_degrees = _rotation_from_x_axis(dx, dy, dz)

    return pipe(
        object_id=object_id,
        object_type=object_type,
        role=role,
        material=material,
        outer_radius_m=outer_radius_m,
        length_m=length_m,
        position_m=midpoint,
        wall_thickness_m=wall_thickness_m,
        contributes_weight=contributes_weight,
        contributes_buoyancy=contributes_buoyancy,
        rotation_degrees=rotation_degrees,
        display_position_m=midpoint,
        assembly_group=assembly_group,
        subsystem=subsystem,
        parent_group=parent_group,
        ports=[
            {
                "port_id": "A",
                "connection_type": "pipe_end",
                "nominal_radius_m": outer_radius_m,
                "position_m": dict(start),
                "direction": dict(start_port.get("direction", {"x": -1.0, "y": 0.0, "z": 0.0})),
                "state": "connected",
                "connected_to": start_port.get("port_id"),
            },
            {
                "port_id": "B",
                "connection_type": "pipe_end",
                "nominal_radius_m": outer_radius_m,
                "position_m": dict(end),
                "direction": dict(end_port.get("direction", {"x": 1.0, "y": 0.0, "z": 0.0})),
                "state": "connected",
                "connected_to": end_port.get("port_id"),
            },
        ],
    )


def _rotation_from_x_axis(dx: float, dy: float, dz: float) -> dict[str, float]:
    yaw_z = math.degrees(math.atan2(dy, dx))
    horizontal = math.sqrt(dx * dx + dy * dy)
    pitch_y = -math.degrees(math.atan2(dz, horizontal))

    return {
        "x": 0.0,
        "y": pitch_y,
        "z": yaw_z,
    }