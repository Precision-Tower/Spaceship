from dataclasses import dataclass, field

from Dashboard.Engineering.Physics.Objects.objects import FloatBody
from Dashboard.Engineering.Physics.Domains.motion import weight_force_n
from Dashboard.Engineering.Physics.Domains.buoyancy import buoyant_force_n, float_margin_n


@dataclass
class Boat:
    boat_id: str
    hull: FloatBody
    payloads: list[FloatBody] = field(default_factory=list)

    def total_mass_kg(self) -> float:
        return self.hull.mass_kg + sum(payload.mass_kg for payload in self.payloads)

    def max_supported_mass_kg(self) -> float:
        return self.hull.fluid.density_kg_m3 * self.hull.volume_m3

    def weight_result(self):
        return weight_force_n(self.total_mass_kg())

    def buoyancy_result(self):
        return buoyant_force_n(
            fluid_density_kg_m3=self.hull.fluid.density_kg_m3,
            displaced_volume_m3=self.hull.volume_m3,
        )

    def margin_result(self):
        return float_margin_n(
            buoyant_force_n_value=self.buoyancy_result().output_value,
            weight_force_n_value=self.weight_result().output_value,
        )

    def remaining_payload_capacity_kg(self) -> float:
        return self.max_supported_mass_kg() - self.total_mass_kg()

    def declared_state(self) -> str:
        margin = self.margin_result().output_value

        if margin > 0:
            return "float_candidate"
        if abs(margin) < 1e-6:
            return "neutral_candidate"
        return "sink_candidate"

    def to_dict(self) -> dict:
        weight = self.weight_result()
        buoyancy = self.buoyancy_result()
        margin = self.margin_result()

        return {
            "boat_id": self.boat_id,
            "declared_state": self.declared_state(),
            "fluid": self.hull.fluid.to_dict(),
            "hull": self.hull.to_dict(),
            "payloads": [payload.to_dict() for payload in self.payloads],
            "total_mass_kg": self.total_mass_kg(),
            "max_supported_mass_kg": self.max_supported_mass_kg(),
            "remaining_payload_capacity_kg": self.remaining_payload_capacity_kg(),
            "equation_results": [
                weight.to_dict(),
                buoyancy.to_dict(),
                margin.to_dict(),
            ],
            "weight_force_n": weight.output_value,
            "max_buoyant_force_n": buoyancy.output_value,
            "float_margin_n": margin.output_value,
            "blocked_interpretations": [
                "float_candidate_equals_stable_boat",
                "positive_margin_equals_safe_payload",
                "calculation_equals_validation",
                "static_buoyancy_equals_seaworthiness",
                "simulation_equals_truth",
            ],
            "unresolved_variables": [
                "hull_shape_displacement_curve",
                "center_of_mass",
                "center_of_buoyancy",
                "free_surface_effect",
                "tilt_or_list_behavior",
                "water_ingress_rate",
                "dynamic_wave_response",
                "material_flex_or_failure",
                "real_payload_distribution",
            ],
        }