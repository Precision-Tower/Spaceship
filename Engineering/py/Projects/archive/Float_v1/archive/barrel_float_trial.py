import json
import math
from datetime import datetime, timezone
from pathlib import Path

from Dashboard.Engineering.Physics.Domains.fluids import FRESH_WATER_ENVIRONMENT, SEA_WATER_ENVIRONMENT

OUT = Path("Engineering/Projects/Float/barrel_float_result_packet.json")

barrel = {
    "object_id": "barrel_001",
    "object_type": "barrel",
    "mass_kg": 18.0,
    "outer_radius_m": 0.285,
    "height_m": 0.82,
}

fluid_environment = SEA_WATER_ENVIRONMENT
environment = fluid_environment.to_dict()

external_volume_m3 = math.pi * barrel["outer_radius_m"] ** 2 * barrel["height_m"]
cross_section_area_m2 = math.pi * barrel["outer_radius_m"] ** 2

required_displaced_volume_m3 = barrel["mass_kg"] / environment["fluid"]["density_kg_m3"]

buoyant_force_at_equilibrium_n = (
    environment["fluid"]["density_kg_m3"]
    * required_displaced_volume_m3
    * environment["gravity_m_s2"]
)

submerged_height_m = required_displaced_volume_m3 / cross_section_area_m2
submerged_fraction = submerged_height_m / barrel["height_m"]

weight_force_n = barrel["mass_kg"] * environment["gravity_m_s2"]

barrel_center_z_m = environment["surface_z_m"] + (barrel["height_m"] / 2.0) - submerged_height_m

packet = {
    "packet_type": "barrel_float_static_packet",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "evidence_state": "calculated_candidate",
    "environment": environment,
    "barrel": {
        **barrel,
        "geometry": {
            "shape": "solid_cylinder_candidate",
            "render": {
                "outer": {
                    "primitive": "cylinder",
                    "radius_m": barrel["outer_radius_m"],
                    "height_m": barrel["height_m"],
                }
            },
        },
        "volumes": {
            "external_volume_m3": external_volume_m3,
            "required_displaced_volume_m3": required_displaced_volume_m3,
        },
        "float_state": {
            "state": "floating_candidate",
            "submerged_height_m": submerged_height_m,
            "submerged_fraction": submerged_fraction,
            "barrel_center_z_m": barrel_center_z_m,
            "water_surface_z_m": environment["surface_z_m"],
        },
        "forces": {
            "weight_force_n": weight_force_n,
            "buoyant_force_at_equilibrium_n": buoyant_force_at_equilibrium_n,
            "net_force_at_equilibrium_n": buoyant_force_at_equilibrium_n - weight_force_n,
        },
        "unresolved_variables": [
            "barrel_orientation",
            "sealed_state_validation",
            "dynamic_water_response",
            "drag",
            "waves",
            "current",
            "real_measured_mass",
        ],
        "blocked_interpretations": [
            "calculated_float_state_equals_validated_float_behavior",
            "static_equilibrium_equals_dynamic_stability",
            "rendered_waterline_equals_physical_measurement",
        ],
    },
    "prohibited_interpretations": [
        "simulation_equals_truth",
        "floating_candidate_equals_validated_stability",
        "calculated_submerged_depth_equals_measured_submerged_depth",
    ],
}

OUT.write_text(json.dumps(packet, indent=2), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Submerged height: {submerged_height_m:.4f} m")
print(f"Submerged fraction: {submerged_fraction:.4f}")
print(f"Barrel center Z: {barrel_center_z_m:.4f} m")