from Engineering.py.Physics.constants import GRAVITY_EARTH_M_S2
from Engineering.py.Physics.equations import EquationResult


def weight_force_n(
    mass_kg: float,
    gravity_m_s2: float = GRAVITY_EARTH_M_S2,
) -> EquationResult:

    value = mass_kg * gravity_m_s2

    return EquationResult(
        equation_id="MC.weight_force",
        description="weight_force_n = mass_kg * gravity_m_s2",
        inputs={
            "mass_kg": mass_kg,
            "gravity_m_s2": gravity_m_s2,
        },
        output_name="weight_force_n",
        output_value=value,
        output_unit="N",
        domain="MC",
        blocked_interpretations=[
            "mass_equals_weight",
            "weight_force_equals_mass_without_gravity_context",
        ],
    )
