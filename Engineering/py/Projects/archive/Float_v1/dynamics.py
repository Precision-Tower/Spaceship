import math
from dataclasses import dataclass

from Engineering.py.Physics.Domains.fluids import SEA_WATER_ENVIRONMENT
from Engineering.py.Physics.Domains.resistance import linear_damping_force_n


@dataclass(frozen=True)
class FloatBody:
    object_id: str
    object_type: str
    mass_kg: float
    radius_m: float
    height_m: float


def cylinder_cross_section_area_m2(radius_m: float) -> float:
    return math.pi * radius_m**2


def cylinder_external_volume_m3(radius_m: float, height_m: float) -> float:
    return cylinder_cross_section_area_m2(radius_m) * height_m


def cylinder_submerged_height_m(
    *,
    center_z_m: float,
    height_m: float,
    surface_z_m: float,
) -> float:
    bottom_z = center_z_m - height_m / 2.0
    return max(0.0, min(height_m, surface_z_m - bottom_z))


def cylinder_displaced_volume_m3(
    *,
    radius_m: float,
    height_m: float,
    center_z_m: float,
    surface_z_m: float,
) -> tuple[float, float]:
    submerged_height = cylinder_submerged_height_m(
        center_z_m=center_z_m,
        height_m=height_m,
        surface_z_m=surface_z_m,
    )
    area = cylinder_cross_section_area_m2(radius_m)
    displaced_volume = area * submerged_height
    return submerged_height, displaced_volume


def required_displaced_volume_m3(
    *,
    mass_kg: float,
    fluid_density_kg_m3: float,
) -> float:
    return mass_kg / fluid_density_kg_m3


def equilibrium_submerged_height_m(
    *,
    mass_kg: float,
    fluid_density_kg_m3: float,
    radius_m: float,
) -> float:
    area = cylinder_cross_section_area_m2(radius_m)
    return required_displaced_volume_m3(
        mass_kg=mass_kg,
        fluid_density_kg_m3=fluid_density_kg_m3,
    ) / area


def equilibrium_center_z_m(
    *,
    surface_z_m: float,
    height_m: float,
    equilibrium_submerged_height_m_value: float,
) -> float:
    return surface_z_m + height_m / 2.0 - equilibrium_submerged_height_m_value


def simulate_vertical_cylinder_float(
    *,
    body: FloatBody,
    environment: dict | None = None,
    initial_center_z_m: float = 1.25,
    initial_velocity_z_m: float = 0.0,
    dt_s: float = 0.04,
    steps: int = 240,
    damping_coefficient: float = 42.0,
) -> dict:
    if environment is None:
        environment = SEA_WATER_ENVIRONMENT.to_dict()

    rho = environment["fluid"]["density_kg_m3"]
    g = environment["gravity_m_s2"]
    surface_z = environment["surface_z_m"]

    center_z = initial_center_z_m
    velocity_z = initial_velocity_z_m

    external_volume = cylinder_external_volume_m3(
        body.radius_m,
        body.height_m,
    )

    eq_required_volume = required_displaced_volume_m3(
        mass_kg=body.mass_kg,
        fluid_density_kg_m3=rho,
    )

    eq_submerged_height = equilibrium_submerged_height_m(
        mass_kg=body.mass_kg,
        fluid_density_kg_m3=rho,
        radius_m=body.radius_m,
    )

    eq_center_z = equilibrium_center_z_m(
        surface_z_m=surface_z,
        height_m=body.height_m,
        equilibrium_submerged_height_m_value=eq_submerged_height,
    )

    frames = []

    for i in range(steps):
        submerged_height, displaced_volume = cylinder_displaced_volume_m3(
            radius_m=body.radius_m,
            height_m=body.height_m,
            center_z_m=center_z,
            surface_z_m=surface_z,
        )

        weight_n = body.mass_kg * g
        buoyancy_n = rho * displaced_volume * g

        damping_n = (
            linear_damping_force_n(damping_coefficient, velocity_z).output_value
            if submerged_height > 0.0
            else 0.0
        )

        net_force_n = buoyancy_n - weight_n + damping_n
        acceleration_z = net_force_n / body.mass_kg

        velocity_z += acceleration_z * dt_s
        center_z += velocity_z * dt_s

        water_contact = submerged_height > 0.0
        target_rotation_x_deg = 90.0 if water_contact else 0.0
        rotation_x_deg = min(90.0, target_rotation_x_deg * min(1.0, i / 90.0))

        vertical_center_y = center_z
        horizontal_center_y = surface_z + body.radius_m - eq_submerged_height
        orientation_blend = rotation_x_deg / 90.0

        barrel_center_y = (
            vertical_center_y * (1.0 - orientation_blend)
            + horizontal_center_y * orientation_blend
        )

        frames.append(
            {
                "frame": i,
                "time_s": round(i * dt_s, 4),
                "center_z_m": center_z,
                "velocity_z_m_s": velocity_z,
                "acceleration_z_m_s2": acceleration_z,
                "rotation_x_deg": rotation_x_deg,
                "submerged_height_m": submerged_height,
                "displaced_volume_m3": displaced_volume,
                "weight_force_n": weight_n,
                "buoyant_force_n": buoyancy_n,
                "damping_force_n": damping_n,
                "net_force_n": net_force_n,
                "render_center_y_m": barrel_center_y,
                "water_contact": water_contact,
            }
        )

    return {
        "object_id": body.object_id,
        "object_type": body.object_type,
        "evidence_state": "calculated_candidate",
        "environment": environment,
        "geometry": {
            "shape": "vertical_cylinder_candidate",
            "radius_m": body.radius_m,
            "height_m": body.height_m,
            "cross_section_area_m2": cylinder_cross_section_area_m2(body.radius_m),
            "external_volume_m3": external_volume,
        },
        "mass": {
            "mass_kg": body.mass_kg,
        },
        "float_state": {
            "required_displaced_volume_m3": eq_required_volume,
            "equilibrium_submerged_height_m": eq_submerged_height,
            "equilibrium_center_z_m": eq_center_z,
            "final_center_z_m": frames[-1]["center_z_m"] if frames else center_z,
            "water_surface_z_m": surface_z,
        },
        "simulation": {
            "dt_s": dt_s,
            "steps": steps,
            "initial_center_z_m": initial_center_z_m,
            "initial_velocity_z_m_s": initial_velocity_z_m,
            "damping_coefficient": damping_coefficient,
            "frames": frames,
        },
        "unresolved_variables": [
            "drag_coefficient",
            "rotational_behavior",
            "barrel_orientation",
            "waves",
            "current",
            "real_measured_mass",
            "real_fluid_density",
            "surface_disturbance",
        ],
        "blocked_interpretations": [
            "dynamic_candidate_equals_validated_float_behavior",
            "settling_animation_equals_measured_motion",
            "damping_value_equals_real_drag",
            "vertical_cylinder_model_equals_real_barrel_behavior",
        ],
    }

def displacement_utilization_ratio(
    *,
    required_volume_m3: float,
    available_volume_m3: float,
) -> float:
    if available_volume_m3 <= 0.0:
        return 0.0

    return required_volume_m3 / available_volume_m3
