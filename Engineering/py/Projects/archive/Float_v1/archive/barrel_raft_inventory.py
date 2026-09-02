import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[4]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Dashboard.Engineering.Physics.Domains.motion import weight_force_n
from Dashboard.Engineering.Physics.Domains.buoyancy import buoyant_force_n, float_margin_n
from Dashboard.Engineering.Physics.Domains.fluids import SEA_WATER_ENVIRONMENT

OUTPUT_PATH = Path(__file__).parent / "barrel_raft_inventory_packet.json"

env = SEA_WATER_ENVIRONMENT.to_dict()
rho = env["fluid"]["density_kg_m3"]
g = env["gravity_m_s2"]
surface_z = env["surface_z_m"]

def make_barrel(index: int, x: float, z: float, assembly_group: str) -> dict:
    radius_m = 0.285
    height_m = 0.82

    return {
        "object_id": f"barrel_{index:03d}",
        "object_type": "barrel",
        "role": "flotation_element",
        "mass_kg": 18.0,
        "volume_m3": 0.208,
        "position_m": {"x": x, "y": 0.0, "z": z},
        "dimensions_m": {"radius": radius_m, "height": height_m},
        "render": {
            "primitive": "cylinder",
            "radius_m": radius_m,
            "height_m": height_m,
            "display_position_m": {"x": x, "y": radius_m * 0.85, "z": z},
            "rotation_degrees": {"x": 90.0, "y": 0.0, "z": 0.0},
        },
        "material": "hdpe_candidate",
        "contributes_weight": True,
        "contributes_buoyancy": True,
        "assembly_group": assembly_group,
        "subsystem": "hull",
        "parent_group": "hull",
    }

def make_connector(
    object_id: str,
    mass_kg: float,
    x: float,
    y: float,
    z: float,
    length_m: float,
    rotation_degrees: dict | None = None,
) -> dict:
    radius_m = 0.0254
    if rotation_degrees is None:
        rotation_degrees = {"x": 0.0, "y": 0.0, "z": 0.0}

    return {
        "object_id": object_id,
        "object_type": "connector_pipe",
        "role": "restraint_structure",
        "assembly_group": "connector_frame",
        "subsystem": "hull",
        "parent_group": "hull",
        "mass_kg": mass_kg,
        "volume_m3": 0.0,
        "position_m": {
            "x": x,
            "y": y,
            "z": z
        },
        "dimensions_m": {
            "radius": radius_m,
            "length": length_m
        },
        "render": {
            "primitive": "cylinder",
            "radius_m": radius_m,
            "height_m": length_m,
            "display_position_m": {
                "x": x,
                "y": y,
                "z": z
            },
            "rotation_degrees": rotation_degrees,
        },
        "material": "pvc_candidate",
        "contributes_weight": True,
        "contributes_buoyancy": False
    }

def build_packet() -> dict:
    objects = []

    barrels_per_row = 5
    barrel_spacing_m = 0.72
    row_gap_m = 1.22

    start_x = -barrel_spacing_m * ((barrels_per_row - 1) / 2.0)

    row_z_values = [
        -row_gap_m / 2.0,
        row_gap_m / 2.0,
    ]

    index = 1

    for row_z in row_z_values:
        for col in range(barrels_per_row):
            x = start_x + col * barrel_spacing_m

            assembly_group = (
                "port_pontoon"
                if row_z < 0
                else "starboard_pontoon"
            )

            objects.append(
                make_barrel(
                    index,
                    x,
                    row_z,
                    assembly_group
                )
            )

            index += 1

    objects.append(
        make_connector(
            "connector_long_left_001",
            4.0,
            0.0,
            0.4,
            -0.61,
            3.2,
            {"x": 0.0, "y": 0.0, "z": 90.0}
        )
    )

    objects.append(
        make_connector(
            "connector_long_right_001",
            4.0,
            0.0,
            0.4,
            0.61,
            3.2,
            {"x": 0.0, "y": 0.0, "z": 90.0}
        )
    )

    cross_positions = [
        start_x,
        0.0,
        start_x + (barrels_per_row - 1) * barrel_spacing_m,
    ]

    for i, x in enumerate(cross_positions):
        objects.append(
            make_connector(
                f"connector_cross_{i + 1:03d}",
                x,
                rail_y,
                0.0,
                row_gap_m,
                {"x": 90.0, "y": 0.0, "z": 0.0}
            )
        )

    total_mass_kg = sum(
        obj["mass_kg"]
        for obj in objects
        if obj.get("contributes_weight", True)
    )

    total_volume_m3 = sum(
        obj["volume_m3"]
        for obj in objects
        if obj.get("contributes_buoyancy", False)
    )

    weight = weight_force_n(
        total_mass_kg,
        g
    )

    buoyancy = buoyant_force_n(
        fluid_density_kg_m3=rho,
        displaced_volume_m3=total_volume_m3,
        gravity_m_s2=g,
    )

    margin = float_margin_n(
        buoyant_force_n_value=buoyancy.output_value,
        weight_force_n_value=weight.output_value,
    )

    com = center_of_mass(objects)
    mass_by_type = mass_breakdown(objects)
    count_by_type = object_count_breakdown(objects)
    groups = assembly_group_breakdown(objects)

    return {
        "packet_type": "barrel_raft_inventory_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "environment": env,
        "assembly": {
            "assembly_id": "boat_assembly_001",
            "assembly_type": "boat_assembly",
            "hierarchy": {
                "root_group": "boat_assembly",
                "groups": {
                    "boat_assembly": {
                        "parent_group": None,
                        "status": "active",
                        "role": "root_assembly",
                    },
                    "hull": {
                        "parent_group": "boat_assembly",
                        "status": "active",
                        "role": "primary_float_structure",
                    },
                    "port_pontoon": {
                        "parent_group": "hull",
                        "status": "active",
                        "role": "flotation_subassembly",
                    },
                    "starboard_pontoon": {
                        "parent_group": "hull",
                        "status": "active",
                        "role": "flotation_subassembly",
                    },
                    "connector_frame": {
                        "parent_group": "hull",
                        "status": "active",
                        "role": "restraint_structure",
                    },
                    "subfloor": {
                        "parent_group": "boat_assembly",
                        "status": "planned",
                        "planned": True,
                    },
                    "deck": {
                        "parent_group": "boat_assembly",
                        "status": "planned",
                        "planned": True,
                    },
                    "motor_assembly": {
                        "parent_group": "boat_assembly",
                        "status": "planned",
                        "planned": True,
                    },
                },
            },
            "objects": objects,
            "summary": {
                "total_mass_kg": total_mass_kg,
                "total_displacement_volume_m3": total_volume_m3,
                "total_weight_force_n": weight.output_value,
                "total_buoyant_force_n": buoyancy.output_value,
                "float_margin_n": margin.output_value,
                "center_of_mass_candidate_m": com,
                "mass_breakdown_kg": mass_by_type,
                "object_count_breakdown": count_by_type,
                "assembly_group_breakdown": groups,
                "equation_results": [
                    weight.to_dict(),
                    buoyancy.to_dict(),
                    margin.to_dict(),
                ],
            },
            "unresolved_variables": [
                "object_spacing",
                "connector_mass",
                "center_of_mass",
                "center_of_buoyancy",
                "tilt_or_list_behavior",
            ],
            "blocked_interpretations": [
                "positive_float_margin_equals_stability",
                "inventory_packet_equals_physical_validation",
                "calculated_candidate_equals_safe_payload",
            ],
        },
        "prohibited_interpretations": [
            "simulation_equals_truth",
            "calculation_equals_validation",
            "float_margin_equals_seaworthiness",
        ],
    }

def center_of_mass(objects: list[dict]) -> dict:
    weighted_objects = [obj for obj in objects if obj.get("contributes_weight", True)]
    total_mass = sum(obj["mass_kg"] for obj in weighted_objects)

    if total_mass == 0:
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    return {
        "x": sum(obj["mass_kg"] * obj["position_m"]["x"] for obj in weighted_objects) / total_mass,
        "y": sum(obj["mass_kg"] * obj["position_m"]["y"] for obj in weighted_objects) / total_mass,
        "z": sum(obj["mass_kg"] * obj["position_m"]["z"] for obj in weighted_objects) / total_mass,
    }   

def mass_breakdown(objects: list[dict]) -> dict:
    breakdown: dict[str, float] = {}

    for obj in objects:
        if not obj.get("contributes_weight", True):
            continue

        object_type = obj.get("object_type", "unknown")
        breakdown[object_type] = breakdown.get(object_type, 0.0) + obj["mass_kg"]

    return breakdown


def object_count_breakdown(objects: list[dict]) -> dict:
    counts: dict[str, int] = {}

    for obj in objects:
        object_type = obj.get("object_type", "unknown")
        counts[object_type] = counts.get(object_type, 0) + 1

    return counts

def assembly_group_breakdown(objects: list[dict]) -> dict:
    groups: dict[str, dict] = {}

    for obj in objects:
        group = obj.get("assembly_group", "ungrouped")

        if group not in groups:
            groups[group] = {
                "object_count": 0,
                "mass_kg": 0.0,
                "displacement_volume_m3": 0.0
            }

        groups[group]["object_count"] += 1

        if obj.get("contributes_weight", True):
            groups[group]["mass_kg"] += obj["mass_kg"]

        if obj.get("contributes_buoyancy", False):
            groups[group]["displacement_volume_m3"] += obj["volume_m3"]

    return groups

def main() -> None:
    packet = build_packet()
    OUTPUT_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(json.dumps(packet, indent=2))
    print(f"\nWrote packet: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
