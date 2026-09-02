from dataclasses import dataclass
import math

from Dashboard.Engineering.Physics.Science.materials import get_material

@dataclass
class BarrelCandidate:
    object_id: str
    material_id: str
    outer_radius_m: float
    height_m: float
    wall_thickness_m: float
    flooded_volume_m3: float = 0.0
    sealed_state: bool = True
    declared_mass_kg: float | None = None

    def mass_difference_kg(self) -> float | None:
        if self.declared_mass_kg is None:
            return None
        return self.declared_mass_kg - self.estimated_shell_mass_kg()

    def material_density_kg_m3(self) -> float:
        return get_material(self.material_id).density_kg_m3


    def estimated_shell_mass_kg(self) -> float:
        return (
            self.shell_volume_m3()
            * self.material_density_kg_m3()
        )

    def external_volume_m3(self) -> float:
        return math.pi * self.outer_radius_m ** 2 * self.height_m

    def inner_radius_m(self) -> float:
        return max(0.0, self.outer_radius_m - self.wall_thickness_m)

    def internal_volume_m3(self) -> float:
        return math.pi * self.inner_radius_m() ** 2 * self.height_m

    def shell_volume_m3(self) -> float:
        return max(0.0, self.external_volume_m3() - self.internal_volume_m3())

    def unresolved_variables(self) -> list[str]:
        unresolveds = [
            "actual_wall_thickness",
            "actual_internal_volume",
            "material_grade",
            "cap_or_lid_geometry",
            "ribbed_surface_geometry",
            "measured_mass_kg",
        ]

        diff = self.mass_difference_kg()
        if diff is not None and abs(diff) > 0.5:
            unresolveds.append("declared_mass_disagrees_with_geometry_material_estimate")

        return unresolveds
    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "object_type": "barrel_candidate",
            "material_id": self.material_id,
            "unresolved_variables": self.unresolved_variables(),
            "material": {
                "material_id": self.material_id,
                "density_kg_m3": self.material_density_kg_m3(),
            },
            "mass": {
                "declared_mass_kg": self.declared_mass_kg,
                "estimated_shell_mass_kg": self.estimated_shell_mass_kg(),
                "mass_difference_kg": self.mass_difference_kg(),
                "mass_source": "declared_candidate_vs_geometry_material_estimate",
            },
            "geometry": {
                "shape": "hollow_cylinder_candidate",
                "outer_radius_m": self.outer_radius_m,
                "height_m": self.height_m,
                "wall_thickness_m": self.wall_thickness_m,
                "inner_radius_m": self.inner_radius_m(),
                "render": {
                    "outer": {
                        "primitive": "cylinder",
                        "radius_m": self.outer_radius_m,
                        "height_m": self.height_m,
                    },
                    "inner": {
                        "primitive": "cylinder",
                        "radius_m": self.inner_radius_m(),
                        "height_m": self.height_m,
                    },
                    "wall_thickness_m": self.wall_thickness_m,
                },
            },
            "volumes": {
                "external_volume_m3": self.external_volume_m3(),
                "internal_volume_m3": self.internal_volume_m3(),
                "shell_volume_m3": self.shell_volume_m3(),
                "flooded_volume_m3": self.flooded_volume_m3,
            },
            "state": {
                "sealed_state": self.sealed_state,
            },
            "blocked_interpretations": [
                "candidate_geometry_equals_measured_barrel",
                "calculated_volume_equals_validated_volume",
                "sealed_state_equals_validated_no_leak",
            ],
        }
