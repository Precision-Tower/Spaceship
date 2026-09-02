import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[5]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

OUTPUT_PATH = Path(__file__).resolve().parent / "battery_packet.json"


def make_battery(
    *,
    index: int,
    x: float,
    y: float,
    z: float,
) -> dict:
    return {
        "object_id": f"battery_12v_{index:03d}",
        "object_type": "battery",
        "role": "power_storage",
        "mass_kg": 18.0,
        "volume_m3": 0.0,
        "position_m": {
            "x": x,
            "y": y,
            "z": z,
        },
        "dimensions_m": {
            "x": 0.33,
            "y": 0.24,
            "z": 0.22,
        },
        "electrical": {
            "nominal_voltage_v": 12.0,
            "connection_role": "series_member",
            "series_index": index,
        },
        "render": {
            "primitive": "box",
            "size_m": {
                "x": 0.33,
                "y": 0.24,
                "z": 0.22,
            },
            "display_position_m": {
                "x": x,
                "y": y,
                "z": z,
            },
            "material": {
                "material_id": "battery_case_candidate",
            },
        },
        "material": "lead_acid_battery_candidate",
        "contributes_weight": True,
        "contributes_buoyancy": False,
        "assembly_group": "power_system",
        "subsystem": "motor",
        "parent_group": "motor_assembly",
        "unresolved_variables": [
            "actual_battery_type",
            "actual_battery_mass",
            "actual_battery_dimensions",
            "battery_mounting_hardware",
            "battery_box_mass",
            "cable_mass",
            "waterproofing",
            "electrical_protection",
        ],
        "blocked_interpretations": [
            "battery_candidate_equals_selected_battery",
            "nominal_voltage_equals_runtime_voltage_under_load",
            "battery_presence_equals_power_system_validated",
        ],
    }


def build_packet() -> dict:
    batteries = [
        make_battery(
            index=1,
            x=-0.35,
            y=0.55,
            z=0.0,
        ),
        make_battery(
            index=2,
            x=0.35,
            y=0.55,
            z=0.0,
        ),
    ]

    total_mass_kg = sum(
        battery["mass_kg"]
        for battery in batteries
        if battery.get("contributes_weight", True)
    )

    pack_voltage_v = sum(
        battery["electrical"]["nominal_voltage_v"]
        for battery in batteries
    )

    return {
        "packet_type": "battery_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "assembly": {
            "assembly_id": "battery_pack_001",
            "assembly_type": "battery_pack",
            "hierarchy": {
                "root_group": "power_system",
                "groups": {
                    "power_system": {
                        "parent_group": "motor_assembly",
                        "status": "active",
                        "role": "electrical_power_storage",
                    },
                    "battery_pack": {
                        "parent_group": "power_system",
                        "status": "active",
                        "role": "series_battery_pack_candidate",
                    },
                },
            },
            "objects": batteries,
            "summary": {
                "battery_count": len(batteries),
                "connection": "series_candidate",
                "nominal_battery_voltage_v": 12.0,
                "pack_voltage_v": pack_voltage_v,
                "total_battery_mass_kg": total_mass_kg,
                "contributes_weight": True,
                "contributes_buoyancy": False,
            },
            "unresolved_variables": [
                "actual_battery_type",
                "actual_battery_mass",
                "actual_battery_dimensions",
                "battery_mounting_location",
                "battery_box_mass",
                "cable_mass",
                "fuse_breaker_selection",
                "waterproofing",
                "runtime_current_draw",
                "usable_capacity_ah",
            ],
            "blocked_interpretations": [
                "two_12v_batteries_equals_validated_power_system",
                "series_voltage_equals_motor_compatibility",
                "battery_packet_equals_safe_electrical_design",
                "battery_mass_candidate_equals_measured_mass",
            ],
        },
        "prohibited_interpretations": [
            "calculation_equals_validation",
            "battery_candidate_equals_safe_installation",
            "packet_equals_electrical_safety_review",
            "nominal_voltage_equals_operational_readiness",
        ],
    }


def main() -> None:
    packet = build_packet()

    OUTPUT_PATH.write_text(
        json.dumps(packet, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(packet, indent=2))
    print(f"\nWrote packet: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
