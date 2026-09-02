import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[5]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Engineering.py.Physics.Objects.pipe.pipe import pipe
from Engineering.py.Physics.Objects.pipe.fittings import elbow_90
from Engineering.py.Physics.Objects.pipe.routing import pipe_between_ports
from Engineering.py.Physics.Objects.pipe.pipe import pvc_pipe
from Engineering.py.Physics.Objects.pipe.connections import (
    pipe_attached_to_port,
    fitting_attached_to_pipe_port,
    build_connection_record,
)
OUTPUT_PATH = Path(__file__).resolve().parent / "hull_frame_packet.json"

CONNECTOR_PIPE_OUTER_RADIUS_M = 0.0254
CONNECTOR_PIPE_WALL_THICKNESS_M = 0.006341448467343372

BARREL_RADIUS_M = 0.285
BARREL_LENGTH_M = 0.82
PONTOON_CENTER_SPREAD_M = 1.2192

PIPE_CLEARANCE_M = 0.025

pipe_offset = (
    BARREL_RADIUS_M
    + CONNECTOR_PIPE_OUTER_RADIUS_M
    + PIPE_CLEARANCE_M
)

def make_connector(
    *,
    object_id: str,
    x: float,
    y: float,
    z: float,
    length_m: float,
    rotation_degrees: dict | None = None,
    assembly_group: str = "connector_frame",
    role: str = "pvc_cradle_structure",
) -> dict:
    if rotation_degrees is None:
        rotation_degrees = {"x": 0.0, "y": 0.0, "z": 0.0}

    position_m = {"x": x, "y": y, "z": z}

    return pipe(
        object_id=object_id,
        object_type="connector_pipe",
        role=role,
        material="pvc_candidate",
        outer_radius_m=CONNECTOR_PIPE_OUTER_RADIUS_M,
        wall_thickness_m=CONNECTOR_PIPE_WALL_THICKNESS_M,
        length_m=length_m,
        position_m=position_m,
        display_position_m=position_m,
        rotation_degrees=rotation_degrees,
        contributes_weight=True,
        contributes_buoyancy=False,
        assembly_group=assembly_group,
        subsystem="hull",
        parent_group="hull",
    )

def build_frame_objects(
    *,
    barrel_x_values: list[float],
    pontoon_length_m: float,
) -> list[dict]:
    objects: list[dict] = []

    rail_y = BARREL_RADIUS_M * 0.55

    front_x = min(barrel_x_values) - BARREL_LENGTH_M / 2.0
    rear_x = max(barrel_x_values) + BARREL_LENGTH_M / 2.0
    center_x = (front_x + rear_x) / 2.0

    pipe_lab_x = center_x
    pipe_lab_y = rail_y + 0.75
    pipe_lab_z = 0.0

    frame_pipe_nominal_size_in = 1.0
    frame_pipe_schedule = "SCH40"

    starter_pipe = pvc_pipe(
        object_id="test_pipe_001",
        object_type="connector_pipe",
        material="pvc_candidate",
        role="pipe_lab_straight_pipe_candidate",
        nominal_size_in=frame_pipe_nominal_size_in,
        schedule=frame_pipe_schedule,
        length_m=0.30,
        position_m={
            "x": pipe_lab_x,
            "y": pipe_lab_y,
            "z": 0.0,
        },
        display_position_m={
            "x": pipe_lab_x,
            "y": pipe_lab_y,
            "z": 0.0,
        },
        rotation_degrees={"x": 0.0, "y": 0.0, "z": -90.0},
        contributes_weight=True,
        contributes_buoyancy=False,
        assembly_group="pipe_lab",
        subsystem="hull",
        parent_group="hull",
    )
    objects.append(starter_pipe)

    target_port = starter_pipe["ports"][1]

    elbow_raw = elbow_90(
        object_id="test_elbow_001",
        nominal_size_in=frame_pipe_nominal_size_in,
        schedule=frame_pipe_schedule,
        position_m=target_port["position_m"],
        display_position_m=target_port["position_m"],
        assembly_group="pipe_lab",
        subsystem="hull",
        parent_group="hull",
        role="pipe_lab_elbow_90_candidate",
    )

    elbow = fitting_attached_to_pipe_port(
        fitting=elbow_raw,
        fitting_port_id="A",
        target_pipe_id=starter_pipe["object_id"],
        target_port=target_port,
        roll_degrees=0.0,
    )    
    objects.append(elbow)

    connection = build_connection_record(
        connection_id="connection_test_pipe_001_to_test_elbow_001",
        from_object_id=starter_pipe["object_id"],
        from_port_id="B",
        to_object_id=elbow["object_id"],
        to_port_id="A",
        connection_role="pipe_to_elbow_candidate",
    )

    starter_pipe["connections"] = [connection]
    elbow["connections"] = [connection]

    return objects

def build_packet() -> dict:
    # Standalone test dimensions matching current hull inventory defaults.
    barrel_spacing_m = BARREL_LENGTH_M + 0.0762
    barrels_per_pontoon = 5
    start_x = -barrel_spacing_m * ((barrels_per_pontoon - 1) / 2.0)

    barrel_x_values = [
        start_x + col * barrel_spacing_m
        for col in range(barrels_per_pontoon)
    ]

    pontoon_length_m = (
        barrels_per_pontoon * BARREL_LENGTH_M
        + (barrels_per_pontoon - 1) * 0.0762
    )

    objects = build_frame_objects(
        barrel_x_values=barrel_x_values,
        pontoon_length_m=pontoon_length_m,
    )

    total_mass_kg = sum(
        obj["mass_kg"]
        for obj in objects
        if obj.get("contributes_weight", True)
    )

    return {
        "packet_type": "hull_frame_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "assembly": {
            "assembly_id": "hull_frame_001",
            "assembly_type": "hull_frame",
            "hierarchy": {
                "root_group": "hull_frame",
                "groups": {
                    "hull_frame": {
                        "parent_group": "hull",
                        "status": "active",
                        "role": "pipe_frame_candidate",
                    },
                    "connector_frame": {
                        "parent_group": "hull_frame",
                        "status": "active",
                        "role": "pvc_connector_frame_candidate",
                    },
                },
            },
            "objects": objects,
            "summary": {
                "frame_member_count": len(objects),
                "total_frame_mass_kg": total_mass_kg,
                "contributes_weight": True,
                "contributes_buoyancy": False,
            },
            "unresolved_variables": [
                "actual_pipe_material",
                "actual_pipe_schedule",
                "actual_joint_method",
                "fitting_geometry",
                "port_alignment",
                "joint_strength",
                "barrel_retention_method",
                "frame_load_path",
            ],
            "blocked_interpretations": [
                "pipe_frame_packet_equals_structural_validation",
                "visible_pipe_frame_equals_load_path_validated",
                "candidate_pipe_mass_equals_measured_mass",
                "pipe_presence_equals_safe_mounting",
            ],
        },
        "prohibited_interpretations": [
            "calculation_equals_validation",
            "pipe_frame_candidate_equals_structural_safety",
            "packet_equals_load_test",
            "visual_frame_equals_validated_structure",
        ],
    }


def main() -> None:
    packet = build_packet()
    OUTPUT_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(json.dumps(packet, indent=2))
    print(f"\nWrote packet: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()





