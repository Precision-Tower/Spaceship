import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[5]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Engineering.py.Physics.Domains.motion import weight_force_n
from Engineering.py.Physics.Domains.buoyancy import buoyant_force_n, float_margin_n
from Engineering.py.Physics.Domains.fluids import SEA_WATER_ENVIRONMENT
from Engineering.py.Physics.Domains.solids import SolidObject
from Engineering.py.Physics.geometry import CylinderGeometry

from Engineering.py.Projects.Float.dynamics import (
    required_displaced_volume_m3,
    displacement_utilization_ratio,
)


OUTPUT_PATH = Path(__file__).parent / "hull_inventory_packet.json"

BARREL_RADIUS_M = 0.285
BARREL_LENGTH_M = 0.82
BARREL_VOLUME_M3 = 0.208
BARREL_MASS_KG = 18.0

BARRELS_PER_PONTOON = 5
BARREL_GAP_M = 0.0762  # 3 inches
PONTOON_CENTER_SPREAD_M = 1.2192  # 4 ft

env = SEA_WATER_ENVIRONMENT.to_dict()
rho = env["fluid"]["density_kg_m3"]
g = env["gravity_m_s2"]


def solid_packet_base(solid: SolidObject) -> dict:
    return {
        "object_id": solid.object_id,
        "object_type": solid.object_type,
        "mass_kg": solid.mass_kg,
        "volume_m3": solid.volume_m3,
        "position_m": dict(solid.position_m),
        "material": solid.material_id,
        "contributes_weight": solid.contributes_weight,
        "contributes_buoyancy": solid.contributes_buoyancy,
    }


def make_barrel(index: int, x: float, z: float, assembly_group: str) -> dict:
    position_m = {"x": x, "y": 0.0, "z": z}

    geometry = CylinderGeometry(
        radius_m=BARREL_RADIUS_M,
        height_m=BARREL_LENGTH_M,
    )

    solid = SolidObject(
        object_id=f"barrel_{index:03d}",
        object_type="barrel",
        mass_kg=BARREL_MASS_KG,
        volume_m3=BARREL_VOLUME_M3,
        geometry=geometry,
        position_m=position_m,
        material_id="hdpe_candidate",
        contributes_weight=True,
        contributes_buoyancy=True,
    )

    base = solid_packet_base(solid)

    return {
        "object_id": base["object_id"],
        "object_type": base["object_type"],
        "physical_primitive": "barrel",
        "role": "flotation_element",
        "mass_kg": base["mass_kg"],
        "volume_m3": base["volume_m3"],
        "position_m": base["position_m"],
        "dimensions_m": {
            "radius": BARREL_RADIUS_M,
            "height": BARREL_LENGTH_M,
        },
        "barrel": {
            "radius_m": BARREL_RADIUS_M,
            "height_m": BARREL_LENGTH_M,
            "sealed": True,
            "fill_state": "air",
            "external_volume_m3": base["volume_m3"],
        },
        "render": {
            "primitive": "cylinder",
            "radius_m": BARREL_RADIUS_M,
            "height_m": BARREL_LENGTH_M,
            "display_position_m": {
                "x": x,
                "y": BARREL_RADIUS_M * 0.85,
                "z": z,
            },
            "rotation_degrees": {
                "x": 0.0,
                "y": 0.0,
                "z": 90.0,
            },
        },
        "material": base["material"],
        "contributes_weight": base["contributes_weight"],
        "contributes_buoyancy": base["contributes_buoyancy"],
        "assembly_group": assembly_group,
        "subsystem": "hull",
        "parent_group": "hull",
    }

def build_hull_objects() -> list[dict]:
    objects: list[dict] = []

    barrel_spacing_m = BARREL_LENGTH_M + BARREL_GAP_M
    start_x = -barrel_spacing_m * ((BARRELS_PER_PONTOON - 1) / 2.0)

    pontoon_z_values = [
        -PONTOON_CENTER_SPREAD_M / 2.0,
        PONTOON_CENTER_SPREAD_M / 2.0,
    ]

    index = 1

    for pontoon_z in pontoon_z_values:
        assembly_group = (
            "port_pontoon"
            if pontoon_z < 0
            else "starboard_pontoon"
        )

        for col in range(BARRELS_PER_PONTOON):
            x = start_x + col * barrel_spacing_m

            objects.append(
                make_barrel(
                    index=index,
                    x=x,
                    z=pontoon_z,
                    assembly_group=assembly_group,
                )
            )

            index += 1

    pontoon_length_m = (
        BARRELS_PER_PONTOON * BARREL_LENGTH_M
        + (BARRELS_PER_PONTOON - 1) * BARREL_GAP_M
    )

    return objects

def build_packet() -> dict:
    objects = build_hull_objects()

    for obj in objects:
        if obj.get("physical_primitive") == "pipe":
            print(
                "[PIPE PORT CHECK]",
                obj["object_id"],
                "ports=",
                len(obj.get("ports", [])),
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

    weight = weight_force_n(total_mass_kg, g)

    buoyancy = buoyant_force_n(
        fluid_density_kg_m3=rho,
        displaced_volume_m3=total_volume_m3,
        gravity_m_s2=g,
    )

    margin = float_margin_n(
        buoyant_force_n_value=buoyancy.output_value,
        weight_force_n_value=weight.output_value,
    )

    required_volume = required_displaced_volume_m3(
        mass_kg=total_mass_kg,
        fluid_density_kg_m3=rho,
    )

    available_volume = total_volume_m3
    unused_volume = available_volume - required_volume

    utilization = displacement_utilization_ratio(
        required_volume_m3=required_volume,
        available_volume_m3=available_volume,
    )

    com = center_of_mass(objects)
    cob = center_of_buoyancy(objects)
    mass_by_type = mass_breakdown(objects)
    count_by_type = object_count_breakdown(objects)
    groups = assembly_group_breakdown(objects)

    barrel_spacing_m = BARREL_LENGTH_M + BARREL_GAP_M
    pontoon_length_m = (
        BARRELS_PER_PONTOON * BARREL_LENGTH_M
        + (BARRELS_PER_PONTOON - 1) * BARREL_GAP_M
    )

    return {
        "packet_type": "hull_inventory_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "environment": env,
        "assembly": {
            "assembly_id": "hull_inventory_001",
            "assembly_type": "hull_inventory",
            "hierarchy": {
                "root_group": "hull",
                "groups": {
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
                        "role": "pvc_cradle_structure",
                    },
                },
            },
            "objects": objects,
            "summary": {
                "barrels_per_pontoon": BARRELS_PER_PONTOON,
                "barrel_gap_m": BARREL_GAP_M,
                "barrel_spacing_m": barrel_spacing_m,
                "pontoon_center_spread_m": PONTOON_CENTER_SPREAD_M,
                "pontoon_length_m": pontoon_length_m,
                "total_mass_kg": total_mass_kg,
                "total_displacement_volume_m3": total_volume_m3,
                "total_weight_force_n": weight.output_value,
                "total_buoyant_force_n": buoyancy.output_value,
                "float_margin_n": margin.output_value,
                "center_of_mass_candidate_m": com,
                "center_of_buoyancy_candidate_m": cob,
                "mass_breakdown_kg": mass_by_type,
                "object_count_breakdown": count_by_type,
                "assembly_group_breakdown": groups,
                "equation_results": [
                    weight.to_dict(),
                    buoyancy.to_dict(),
                    margin.to_dict(),
                ],
                "required_displacement_volume_m3": required_volume,
                "available_displacement_volume_m3": available_volume,
                "unused_displacement_volume_m3": unused_volume,
                "displacement_utilization_ratio": utilization,
            },
            "unresolved_variables": [
                "actual_barrel_dimensions",
                "actual_barrel_spacing",
                "pvc_joint_method",
                "pvc_cradle_fastening",
                "barrel_retention_straps",
                "center_of_mass",
                "center_of_buoyancy",
                "tilt_or_list_behavior",
            ],
            "blocked_interpretations": [
                "positive_float_margin_equals_stability",
                "inventory_packet_equals_physical_validation",
                "calculated_candidate_equals_safe_payload",
                "pvc_cradle_geometry_equals_structural_validation",
            ],
        },
        "prohibited_interpretations": [
            "simulation_equals_truth",
            "calculation_equals_validation",
            "float_margin_equals_seaworthiness",
            "visual_cradle_equals_structural_safety",
        ],
    }


def center_of_mass(objects: list[dict]) -> dict:
    weighted_objects = [
        obj
        for obj in objects
        if obj.get("contributes_weight", True)
    ]

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
                "displacement_volume_m3": 0.0,
            }

        groups[group]["object_count"] += 1

        if obj.get("contributes_weight", True):
            groups[group]["mass_kg"] += obj["mass_kg"]

        if obj.get("contributes_buoyancy", False):
            groups[group]["displacement_volume_m3"] += obj["volume_m3"]

    return groups


def center_of_buoyancy(objects: list[dict]) -> dict:
    buoyant_objects = [
        obj
        for obj in objects
        if obj.get("contributes_buoyancy", False)
    ]

    total_volume = sum(obj["volume_m3"] for obj in buoyant_objects)

    if total_volume == 0:
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    return {
        "x": sum(obj["volume_m3"] * obj["position_m"]["x"] for obj in buoyant_objects) / total_volume,
        "y": sum(obj["volume_m3"] * obj["position_m"]["y"] for obj in buoyant_objects) / total_volume,
        "z": sum(obj["volume_m3"] * obj["position_m"]["z"] for obj in buoyant_objects) / total_volume,
    }


def main() -> None:
    packet = build_packet()
    OUTPUT_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(json.dumps(packet, indent=2))
    print(f"\nWrote packet: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
