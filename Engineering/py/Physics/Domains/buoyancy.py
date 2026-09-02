from Engineering.py.Physics.constants import GRAVITY_EARTH_M_S2
from Engineering.py.Physics.equations import EquationResult


def buoyant_force_n(
    fluid_density_kg_m3: float,
    displaced_volume_m3: float,
    gravity_m_s2: float = GRAVITY_EARTH_M_S2,
) -> EquationResult:

    value = (
        fluid_density_kg_m3
        * displaced_volume_m3
        * gravity_m_s2
    )

    return EquationResult(
        equation_id="MC.buoyant_force",
        description=(
            "buoyant_force_n = "
            "fluid_density_kg_m3 * "
            "displaced_volume_m3 * "
            "gravity_m_s2"
        ),
        inputs={
            "fluid_density_kg_m3": fluid_density_kg_m3,
            "displaced_volume_m3": displaced_volume_m3,
            "gravity_m_s2": gravity_m_s2,
        },
        output_name="buoyant_force_n",
        output_value=value,
        output_unit="N",
        domain="MC",
        blocked_interpretations=[
            "buoyant_force_equals_stability",
            "positive_buoyancy_equals_safe_payload",
            "calculation_equals_validation",
        ],
    )


def float_margin_n(
    buoyant_force_n_value: float,
    weight_force_n_value: float,
) -> EquationResult:

    value = (
        buoyant_force_n_value
        - weight_force_n_value
    )

    return EquationResult(
        equation_id="MC.float_margin",
        description=(
            "float_margin_n = "
            "buoyant_force_n - "
            "weight_force_n"
        ),
        inputs={
            "buoyant_force_n": buoyant_force_n_value,
            "weight_force_n": weight_force_n_value,
        },
        output_name="float_margin_n",
        output_value=value,
        output_unit="N",
        domain="MC",
        blocked_interpretations=[
            "positive_margin_equals_stable",
            "positive_margin_equals_seaworthy",
            "positive_margin_equals_validated",
        ],
    )
