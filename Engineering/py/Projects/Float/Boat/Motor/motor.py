import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[5]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

OUTPUT_PATH = Path(__file__).resolve().parent / "motor_packet.json"


def make_motor() -> dict:
    return {
        "object_id": "electric_motor_001",
        "object_type": "electric_motor",
        "role": "propulsion_drive",
        "mass_kg": 12.0,
        "volume_m3": 0.0,
        "position_m": {
            "x": 0.0,
            "y": 0.45,
            "z": 0.95,
        },
        "dimensions_m": {
            "x": 0.35,
            "y": 0.28,
            "z": 0.28,
        },
        "electrical": {
            "nominal_voltage_v": 24.0,
            "power_w_candidate": 1000.0,
            "current_a_candidate": 41.67,
        },
        "propulsion": {
            "thrust_force_n_candidate": None,
            "propeller_diameter_m_candidate": None,
            "shaft_power_w_candidate": None,
            "efficiency_candidate": None,
        },
        "render": {
            "primitive": "box",
            "size_m": {
                "x": 0.35,
                "y": 0.28,
                "z": 0.28,
            },
            "display_position_m": {
                "x": 0.0,
                "y": 0.45,
                "z": 0.95,
            },
            "material": {
                "material_id": "motor_case_candidate",
            },
        },
        "material": "electric_motor_candidate",
        "contributes_weight": True,
        "contributes_buoyancy": False,
        "assembly_group": "motor_assembly",
        "subsystem": "motor",
        "parent_group": "boat_assembly",
        "unresolved_variables": [
            "actual_motor_mass",
            "actual_motor_dimensions",
            "motor_mount_mass",
            "shaft_mass",
            "propeller_mass",
            "controller_mass",
            "actual_power_rating",
            "actual_current_draw",
            "actual_thrust_curve",
            "cooling_requirement",
            "waterproofing",
        ],
        "blocked_interpretations": [
            "motor_candidate_equals_selected_motor",
            "nominal_voltage_equals_motor_compatibility",
            "power_candidate_equals_measured_output",
            "motor_packet_equals_propulsion_validation",
        ],
    }


def build_packet() -> dict:
    motor = make_motor()

    return {
        "packet_type": "motor_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "assembly": {
            "assembly_id": "motor_assembly_001",
            "assembly_type": "motor_assembly",
            "hierarchy": {
                "root_group": "motor_assembly",
                "groups": {
                    "motor_assembly": {
                        "parent_group": "boat_assembly",
                        "status": "active",
                        "role": "propulsion_system_candidate",
                    }
                },
            },
            "objects": [motor],
            "summary": {
                "motor_count": 1,
                "total_motor_mass_kg": motor["mass_kg"],
                "nominal_voltage_v": motor["electrical"]["nominal_voltage_v"],
                "power_w_candidate": motor["electrical"]["power_w_candidate"],
                "current_a_candidate": motor["electrical"]["current_a_candidate"],
                "thrust_force_n_candidate": motor["propulsion"]["thrust_force_n_candidate"],
                "contributes_weight": True,
                "contributes_buoyancy": False,
            },
            "unresolved_variables": [
                "actual_motor_selection",
                "motor_mounting_location",
                "motor_mount_mass",
                "controller_mass",
                "shaft_or_outdrive_geometry",
                "propeller_selection",
                "thrust_curve",
                "drag_model",
                "battery_runtime_under_load",
                "waterproofing",
            ],
            "blocked_interpretations": [
                "motor_packet_equals_validated_propulsion",
                "voltage_match_equals_system_compatibility",
                "candidate_power_equals_available_thrust",
                "motor_presence_equals_drivable_vessel",
            ],
        },
        "prohibited_interpretations": [
            "calculation_equals_validation",
            "motor_candidate_equals_safe_installation",
            "packet_equals_propulsion_test",
            "nominal_voltage_equals_operational_readiness",
            "power_rating_equals_measured_thrust",
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
