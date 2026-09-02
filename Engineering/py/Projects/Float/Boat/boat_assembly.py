from copy import deepcopy
import json
from datetime import datetime, timezone
from pathlib import Path

import sys
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[4]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Engineering.py.Physics.Interactions.collision import find_overlaps

BASE_DIR = Path(__file__).parent
HULL_PACKET_PATH = BASE_DIR / "Hull" / "hull_inventory_packet.json"
HULL_FRAME_PACKET_PATH = BASE_DIR / "Hull" / "hull_frame_packet.json"
BATTERY_PACKET_PATH = BASE_DIR / "Motor" / "battery_packet.json"
MOTOR_PACKET_PATH = BASE_DIR / "Motor" / "motor_packet.json"
LAYOUT_OVERRIDE_PATH = BASE_DIR / "boat_layout_override.json"
OUTPUT_PATH = BASE_DIR / "boat_assembly_packet.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def boat_hierarchy() -> dict:
    return {
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
            "hull_frame": {
                "parent_group": "hull",
                "status": "active",
                "role": "structural_mounting_frame_candidate",
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
                "status": "active",
                "role": "propulsion_subassembly_candidate",
            },
            "power_system": {
            "parent_group": "motor_assembly",
            "status": "active",
            "role": "electrical_power_storage",
        },
        },
    }


def aggregate_summary(hull_packet: dict, objects: list[dict], environment: dict) -> dict:
    hull_summary = hull_packet.get("assembly", {}).get("summary", {})
    g = environment.get("gravity_m_s2", 9.80665)

    total_mass_kg = sum(
        obj["mass_kg"]
        for obj in objects
        if obj.get("contributes_weight", True)
    )

    total_displacement_volume_m3 = sum(
        obj["volume_m3"]
        for obj in objects
        if obj.get("contributes_buoyancy", False)
    )

    total_weight_force_n = total_mass_kg * g
    total_buoyant_force_n = hull_summary.get("total_buoyant_force_n")
    float_margin_n = (
        total_buoyant_force_n - total_weight_force_n
        if total_buoyant_force_n is not None
        else None
    )

    overlap_warnings = find_overlaps(
        objects,
        clearance_m=0.0,
        ignored_object_types=set(),
    )

    return {
        "total_mass_kg": total_mass_kg,
        "total_displacement_volume_m3": total_displacement_volume_m3,
        "total_weight_force_n": total_weight_force_n,
        "total_buoyant_force_n": total_buoyant_force_n,
        "float_margin_n": float_margin_n,
        "center_of_mass_candidate_m": center_of_mass(objects),
        "center_of_buoyancy_candidate_m": hull_summary.get("center_of_buoyancy_candidate_m"),
        "mass_breakdown_kg": mass_breakdown(objects),
        "object_count_breakdown": object_count_breakdown(objects),
        "assembly_group_breakdown": assembly_group_breakdown(objects),
        "physical_overlap_validation": (
            "warning"
            if overlap_warnings
            else "passed"
        ),
        "physical_overlap_warning_count": len(overlap_warnings),
        "physical_overlap_warnings": overlap_warnings[:25],
        "equation_results": hull_summary.get("equation_results", []),
        "source_assembly_ids": [
            hull_packet.get("assembly", {}).get("assembly_id", "hull_inventory_001")
        ],
    }

def center_of_mass(objects: list[dict]) -> dict:
    weighted_objects = [
        obj
        for obj in objects
        if obj.get("contributes_weight", True)
    ]

    total_mass = sum(
        obj["mass_kg"]
        for obj in weighted_objects
    )

    if total_mass == 0:
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    return {
        "x": sum(obj["mass_kg"] * obj["position_m"]["x"] for obj in weighted_objects) / total_mass,
        "y": sum(obj["mass_kg"] * obj["position_m"]["y"] for obj in weighted_objects) / total_mass,
        "z": sum(obj["mass_kg"] * obj["position_m"]["z"] for obj in weighted_objects) / total_mass,
    }

def copied_objects_from(*assemblies: dict) -> list[dict]:
    objects: list[dict] = []

    for assembly in assemblies:
        objects.extend(deepcopy(assembly.get("objects", [])))

    return objects


def apply_layout_override(objects: list[dict]) -> dict:
    if not LAYOUT_OVERRIDE_PATH.exists():
        return {
            "applied": False,
            "object_count": 0,
        }

    override_packet = load_json(LAYOUT_OVERRIDE_PATH)
    overrides = override_packet.get("objects", {})
    if not isinstance(overrides, dict) or not overrides:
        return {
            "applied": False,
            "object_count": 0,
        }

    applied_count = 0

    for obj in objects:
        object_id = obj.get("object_id")
        if object_id not in overrides:
            continue

        object_override = overrides.get(object_id, {})
        if not isinstance(object_override, dict):
            continue

        applied = False

        if "position_m" in object_override:
            applied = apply_position_override(obj, object_override["position_m"])

        if applied:
            applied_count += 1

    return {
        "applied": applied_count > 0,
        "object_count": applied_count,
    }


def apply_position_override(obj: dict, position_override: dict) -> bool:
    if not isinstance(position_override, dict):
        return False

    old_position = vector_from_dict(obj.get("position_m", {}))
    new_position = vector_from_dict(position_override)
    render = obj.get("render", {})

    if isinstance(render, dict) and isinstance(render.get("display_position_m"), dict):
        old_display_position = vector_from_dict(render["display_position_m"])
        display_offset = {
            "x": old_display_position["x"] - old_position["x"],
            "y": old_display_position["y"] - old_position["y"],
            "z": old_display_position["z"] - old_position["z"],
        }
        render["display_position_m"] = {
            "x": new_position["x"] + display_offset["x"],
            "y": new_position["y"] + display_offset["y"],
            "z": new_position["z"] + display_offset["z"],
        }

    obj["position_m"] = new_position
    return True


def vector_from_dict(value: dict) -> dict:
    return {
        "x": float(value.get("x", 0.0)),
        "y": float(value.get("y", 0.0)),
        "z": float(value.get("z", 0.0)),
    }


def build_packet() -> dict:
    hull_packet = load_json(HULL_PACKET_PATH)
    battery_packet = load_json(BATTERY_PACKET_PATH)
    motor_packet = load_json(MOTOR_PACKET_PATH)
    hull_frame_packet = load_json(HULL_FRAME_PACKET_PATH)

    hull_assembly = hull_packet.get("assembly", {})
    hull_frame_assembly = hull_frame_packet.get("assembly", {})
    battery_assembly = battery_packet.get("assembly", {})
    motor_assembly = motor_packet.get("assembly", {})

    objects = copied_objects_from(
        hull_assembly,
        hull_frame_assembly,
        battery_assembly,
        motor_assembly,
    )
    layout_override = apply_layout_override(objects)
    source_packets = [
        {
            "packet_type": hull_packet.get("packet_type", "hull_inventory_packet"),
            "packet_path": str(HULL_PACKET_PATH.relative_to(BASE_DIR)),
        },
        {
            "packet_type": battery_packet.get("packet_type", "battery_packet"),
            "packet_path": str(BATTERY_PACKET_PATH.relative_to(BASE_DIR)),
        },
        {
            "packet_type": hull_frame_packet.get("packet_type", "hull_frame_packet"),
            "packet_path": str(HULL_FRAME_PACKET_PATH.relative_to(BASE_DIR)),
        },
        {
            "packet_type": motor_packet.get("packet_type", "motor_packet"),
            "packet_path": str(MOTOR_PACKET_PATH.relative_to(BASE_DIR)),
        },
    ]

    if layout_override["applied"]:
        source_packets.append({
            "packet_type": "boat_layout_override",
            "packet_path": str(LAYOUT_OVERRIDE_PATH.relative_to(BASE_DIR)),
        })

    summary = aggregate_summary(
        hull_packet,
        objects,
        hull_packet.get("environment", {}),
    )
    summary["layout_override_applied"] = layout_override["applied"]
    summary["layout_override_path"] = (
        str(LAYOUT_OVERRIDE_PATH.relative_to(BASE_DIR))
        if layout_override["applied"]
        else None
    )
    summary["layout_override_object_count"] = layout_override["object_count"]

    return {
        "packet_type": "boat_assembly_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": hull_packet.get("evidence_state", "calculated_candidate"),
        "environment": hull_packet.get("environment", {}),
        "source_packets": source_packets,
        "assembly": {
            "assembly_id": "boat_assembly_001",
            "assembly_type": "boat_assembly",
            "hierarchy": boat_hierarchy(),
            "objects": objects,
            "summary": summary,
            "unresolved_variables": (
                hull_assembly.get("unresolved_variables", [])
                + battery_assembly.get("unresolved_variables", [])
                + hull_frame_assembly.get("unresolved_variables", [])
                + motor_assembly.get("unresolved_variables", [])
            ),
            "blocked_interpretations": (
                hull_assembly.get("blocked_interpretations", [])
                + battery_assembly.get("blocked_interpretations", [])
                + hull_frame_assembly.get("blocked_interpretations", [])
                + motor_assembly.get("blocked_interpretations", [])
            ),
        },
        "prohibited_interpretations": (
            hull_packet.get("prohibited_interpretations", [])
            + battery_packet.get("prohibited_interpretations", [])
            + hull_frame_packet.get("prohibited_interpretations", [])
            + motor_packet.get("prohibited_interpretations", [])
        ),
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


def main() -> None:
    packet = build_packet()
    OUTPUT_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(json.dumps(packet, indent=2))
    print(f"\nWrote packet: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
