from Engineering.py.Physics.equations import EquationResult


def quadratic_drag_force_n(
    fluid_density_kg_m3: float,
    drag_coefficient: float,
    projected_area_m2: float,
    relative_velocity_m_s: float,
) -> EquationResult:

    value = (
        -0.5
        * fluid_density_kg_m3
        * drag_coefficient
        * projected_area_m2
        * relative_velocity_m_s
        * abs(relative_velocity_m_s)
    )

    return EquationResult(
        equation_id="MC.quadratic_drag_force",
        description=(
            "drag_force_n = "
            "-0.5 * "
            "fluid_density_kg_m3 * "
            "drag_coefficient * "
            "projected_area_m2 * "
            "relative_velocity_m_s * "
            "abs(relative_velocity_m_s)"
        ),
        inputs={
            "fluid_density_kg_m3": fluid_density_kg_m3,
            "drag_coefficient": drag_coefficient,
            "projected_area_m2": projected_area_m2,
            "relative_velocity_m_s": relative_velocity_m_s,
        },
        output_name="drag_force_n",
        output_value=value,
        output_unit="N",
        domain="MC",
        blocked_interpretations=[
            "drag_force_equals_validated_fluid_model",
            "drag_coefficient_equals_measured_value",
            "projected_area_equals_full_contact_model",
            "scalar_resistance_equals_full_3d_fluid_simulation",
        ],
    )


def linear_damping_force_n(
    damping_coefficient: float,
    velocity_m_s: float,
) -> EquationResult:

    value = -damping_coefficient * velocity_m_s

    return EquationResult(
        equation_id="MC.linear_damping_force",
        description=(
            "damping_force_n = "
            "-damping_coefficient * "
            "velocity_m_s"
        ),
        inputs={
            "damping_coefficient": damping_coefficient,
            "velocity_m_s": velocity_m_s,
        },
        output_name="damping_force_n",
        output_value=value,
        output_unit="N",
        domain="MC",
        blocked_interpretations=[
            "linear_damping_equals_real_drag",
            "damping_coefficient_equals_measured_value",
            "scalar_damping_equals_full_fluid_resistance",
        ],
    )
