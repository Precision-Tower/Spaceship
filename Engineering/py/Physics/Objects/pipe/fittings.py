import math
from typing import Any

from Engineering.py.Physics.materials import PhysicalMaterial, get_material
from Engineering.py.Physics.Objects.pipe.pipe import port_transform
from Engineering.py.Physics.Objects.pipe.catalog import pvc_pipe_dimensions

HOLLOW_ACCOUNTING_UNRESOLVED = (
    "inner_radius_m_or_wall_thickness_m_required_for_hollow_accounting"
)

INCH_TO_M = 0.0254

FITTING_STANDARDS = {
    "ASME_B16_9_LR_90": {
        "angle_degrees": 90.0,
        "takeoff_multiplier": 1.5,
        "description": "ASME B16.9 long-radius 90 elbow candidate",
    },
    "ASME_B16_9_SR_90": {
        "angle_degrees": 90.0,
        "takeoff_multiplier": 1.0,
        "description": "ASME B16.9 short-radius 90 elbow candidate",
    },
}


def standard_elbow_takeoff_m(
    *,
    nominal_size_in: float,
    fitting_standard: str,
) -> float:
    if nominal_size_in <= 0.0:
        raise ValueError("nominal_size_in must be greater than 0")

    if fitting_standard not in FITTING_STANDARDS:
        raise ValueError(f"Unsupported fitting_standard: {fitting_standard}")

    multiplier = FITTING_STANDARDS[fitting_standard]["takeoff_multiplier"]
    return nominal_size_in * multiplier * INCH_TO_M

def coupling(
    *,
    object_id: str,
    role: str = "pipe_coupling_candidate",
    material: PhysicalMaterial | str = "pvc_candidate",
    nominal_radius_m: float,
    length_m: float,
    position_m: dict[str, float],
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    object_type: str = "pipe_coupling",
    outer_radius_m: float | None = None,
    inner_radius_m: float | None = None,
    wall_thickness_m: float | None = None,
    rotation_degrees: dict[str, float] | None = None,
    display_position_m: dict[str, float] | None = None,
    contributes_weight: bool = True,
    contributes_buoyancy: bool = False,
    ports: list[dict[str, Any]] | None = None,
) -> dict:
    if rotation_degrees is None:
        rotation_degrees = {"x": 0.0, "y": 0.0, "z": 0.0}

    if display_position_m is None:
        display_position_m = dict(position_m)

    resolved_outer_radius_m = outer_radius_m if outer_radius_m is not None else nominal_radius_m
    resolved_inner_radius_m = _inner_radius(
        outer_radius_m=resolved_outer_radius_m,
        inner_radius_m=inner_radius_m,
        wall_thickness_m=wall_thickness_m,
    )
    resolved_wall_thickness_m = resolved_outer_radius_m - resolved_inner_radius_m
    unresolved_variables = _hollow_accounting_unresolved_variables(
        inner_radius_m=inner_radius_m,
        wall_thickness_m=wall_thickness_m,
    )
    material_data = _coerce_material(material)
    material_volume_m3 = _hollow_cylinder_volume_m3(
        resolved_outer_radius_m,
        resolved_inner_radius_m,
        length_m,
    )

    if ports is None:
        ports = _linear_two_ports(
            position_m=position_m,
            length_m=length_m,
            nominal_radius_m=nominal_radius_m,
            inner_radius_m=resolved_inner_radius_m,
            rotation_degrees=rotation_degrees,
        )

    return _fitting_object(
        object_id=object_id,
        object_type=object_type,
        fitting_type="coupling",
        role=role,
        material=material_data,
        mass_kg=_mass_from_volume(material_volume_m3, material_data),
        material_volume_m3=material_volume_m3,
        packet_volume_m3=_cylinder_volume_m3(resolved_outer_radius_m, length_m)
        if contributes_buoyancy
        else 0.0,
        position_m=position_m,
        dimensions_m={
            "nominal_radius_m": nominal_radius_m,
            "outer_radius_m": resolved_outer_radius_m,
            "inner_radius_m": resolved_inner_radius_m,
            "length_m": length_m,
            "wall_thickness_m": resolved_wall_thickness_m,
        },
        render={
            "primitive": "cylinder",
            "radius_m": resolved_outer_radius_m,
            "height_m": length_m,
            "display_position_m": display_position_m,
            "rotation_degrees": rotation_degrees,
        },
        contributes_weight=contributes_weight,
        contributes_buoyancy=contributes_buoyancy,
        assembly_group=assembly_group,
        subsystem=subsystem,
        parent_group=parent_group,
        ports=ports,
        takeoffs=_takeoff_block(
            takeoff_role="coupling",
            values_m={
                "nominal_radius_m": nominal_radius_m,
                "length_m": length_m,
                "outer_radius_m": resolved_outer_radius_m,
                "inner_radius_m": resolved_inner_radius_m,
                "wall_thickness_m": resolved_wall_thickness_m,
            },
        ),
        unresolved_variables=unresolved_variables,
    )


def elbow_90(
    *,
    object_id: str,
    role: str = "pipe_elbow_candidate",
    material: PhysicalMaterial | str = "pvc_candidate",
    nominal_size_in: float,
    schedule: str = "SCH40",
    nominal_radius_m: float | None = None,
    position_m: dict[str, float],
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    bend_radius_m: float | None = None,
    fitting_standard: str = "ASME_B16_9_LR_90",
    object_type: str = "pipe_fitting",
    outer_radius_m: float | None = None,
    inner_radius_m: float | None = None,
    wall_thickness_m: float | None = None,
    rotation_degrees: dict[str, float] | None = None,
    display_position_m: dict[str, float] | None = None,
    contributes_weight: bool = True,
    contributes_buoyancy: bool = False,
    ports: list[dict[str, Any]] | None = None,
) -> dict:
    if rotation_degrees is None:
        rotation_degrees = {"x": 0.0, "y": 0.0, "z": 0.0}

    if display_position_m is None:
        display_position_m = dict(position_m)

    pipe_dims = pvc_pipe_dimensions(
        nominal_size_in=nominal_size_in,
        schedule=schedule,
    )

    if nominal_radius_m is None:
        nominal_radius_m = pipe_dims["outer_radius_m"]

    if outer_radius_m is None:
        outer_radius_m = pipe_dims["outer_radius_m"]

    if inner_radius_m is None and wall_thickness_m is None:
        inner_radius_m = pipe_dims["inner_radius_m"]
        wall_thickness_m = pipe_dims["wall_thickness_m"]

    if bend_radius_m is None:
        if nominal_size_in is None:
            raise ValueError("bend_radius_m or nominal_size_in is required")

        bend_radius_m = standard_elbow_takeoff_m(
            nominal_size_in=nominal_size_in,
            fitting_standard=fitting_standard,
        )

    if bend_radius_m <= 0.0:
        raise ValueError("bend_radius_m must be greater than 0")

    if fitting_standard not in FITTING_STANDARDS:
        raise ValueError(f"Unsupported fitting_standard: {fitting_standard}")

    standard_data = FITTING_STANDARDS[fitting_standard]
    takeoff_multiplier = float(standard_data["takeoff_multiplier"])
    angle_degrees = float(standard_data.get("angle_degrees", 90.0))

    resolved_outer_radius_m = (
        outer_radius_m if outer_radius_m is not None else nominal_radius_m
    )

    resolved_inner_radius_m = _inner_radius(
        outer_radius_m=resolved_outer_radius_m,
        inner_radius_m=inner_radius_m,
        wall_thickness_m=wall_thickness_m,
    )

    resolved_wall_thickness_m = (
        resolved_outer_radius_m - resolved_inner_radius_m
    )

    unresolved_variables = _hollow_accounting_unresolved_variables(
        inner_radius_m=inner_radius_m,
        wall_thickness_m=wall_thickness_m,
    )

    material_data = _coerce_material(material)

    centerline_length_m = math.pi * bend_radius_m / 2.0

    material_volume_m3 = _hollow_cylinder_volume_m3(
        resolved_outer_radius_m,
        resolved_inner_radius_m,
        centerline_length_m,
    )

    if ports is None:
        ports = _elbow_90_ports(
            position_m=position_m,
            bend_radius_m=bend_radius_m,
            nominal_radius_m=nominal_radius_m,
            inner_radius_m=resolved_inner_radius_m,
            rotation_degrees=rotation_degrees,
        )

    return _fitting_object(
        object_id=object_id,
        object_type=object_type,
        fitting_type="elbow_90",
        role=role,
        material=material_data,
        mass_kg=_mass_from_volume(material_volume_m3, material_data),
        material_volume_m3=material_volume_m3,
        packet_volume_m3=(
            _cylinder_volume_m3(resolved_outer_radius_m, centerline_length_m)
            if contributes_buoyancy
            else 0.0
        ),
        position_m=position_m,
        dimensions_m={
            "nominal_radius_m": nominal_radius_m,
            "nominal_size_in": nominal_size_in,
            "outer_radius_m": resolved_outer_radius_m,
            "inner_radius_m": resolved_inner_radius_m,
            "bend_radius_m": bend_radius_m,
            "takeoff_m": bend_radius_m,
            "takeoff_multiplier": takeoff_multiplier,
            "angle_degrees": angle_degrees,
            "centerline_length_m": centerline_length_m,
            "wall_thickness_m": resolved_wall_thickness_m,
            "fitting_standard": fitting_standard,
            "schedule": schedule,
            "pipe_spec": pipe_dims,
        },
        render={
            "primitive": "pipe_elbow_90",
            "outer_radius_m": resolved_outer_radius_m,
            "inner_radius_m": resolved_inner_radius_m,
            "bend_radius_m": bend_radius_m,
            "takeoff_m": bend_radius_m,
            "angle_degrees": angle_degrees,
            "display_position_m": display_position_m,
            "rotation_degrees": rotation_degrees,
            "nominal_size_in": nominal_size_in,
            "schedule": schedule,
        },
        contributes_weight=contributes_weight,
        contributes_buoyancy=contributes_buoyancy,
        assembly_group=assembly_group,
        subsystem=subsystem,
        parent_group=parent_group,
        ports=ports,
        takeoffs=_takeoff_block(
            takeoff_role="elbow_90",
            values_m={
                "nominal_radius_m": nominal_radius_m,
                "nominal_size_in": nominal_size_in,
                "outer_radius_m": resolved_outer_radius_m,
                "inner_radius_m": resolved_inner_radius_m,
                "wall_thickness_m": resolved_wall_thickness_m,
                "bend_radius_m": bend_radius_m,
                "takeoff_m": bend_radius_m,
                "takeoff_multiplier": takeoff_multiplier,
                "angle_degrees": angle_degrees,
                "centerline_length_m": centerline_length_m,
            },
        ),
        unresolved_variables=unresolved_variables,
    )

def _fitting_object(
    *,
    object_id: str,
    object_type: str,
    fitting_type: str,
    role: str,
    material: PhysicalMaterial,
    mass_kg: float,
    material_volume_m3: float,
    packet_volume_m3: float,
    position_m: dict[str, float],
    dimensions_m: dict[str, Any],
    render: dict[str, Any],
    contributes_weight: bool,
    contributes_buoyancy: bool,
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    ports: list[dict[str, Any]],
    takeoffs: dict[str, Any],
    unresolved_variables: list[str] | None = None,
) -> dict:
    packet = {
        "object_id": object_id,
        "object_type": object_type,
        "physical_primitive": "pipe_fitting",
        "fitting_type": fitting_type,
        "role": role,
        "evidence_state": "calculated_candidate",
        "mass_kg": mass_kg,
        "volume_m3": packet_volume_m3,
        "position_m": dict(position_m),
        "dimensions_m": dict(dimensions_m),
        "render": render,
        "material": material.material_id,
        "material_density_kg_m3": material.density_kg_m3,
        "material_volume_m3": material_volume_m3,
        "contributes_weight": contributes_weight,
        "contributes_buoyancy": contributes_buoyancy,
        "assembly_group": assembly_group,
        "subsystem": subsystem,
        "parent_group": parent_group,
        "ports": ports,
        "takeoffs": takeoffs,
        "blocked_interpretations": [
            "fitting_candidate_equals_pressure_rated_part",
            "fitting_geometry_equals_leak_free_connection",
            "calculated_candidate_equals_build_ready_component",
        ],
    }

    if unresolved_variables:
        packet["unresolved_variables"] = list(unresolved_variables)

    return packet


def _takeoff_block(
    *,
    takeoff_role: str,
    values_m: dict[str, float],
) -> dict[str, Any]:
    return {
        "evidence_state": "calculated_candidate",
        "items": [
            {
                "type": "fitting_takeoff_candidate",
                "takeoff_role": takeoff_role,
                "values_m": dict(values_m),
            }
        ],
    }


def _hollow_accounting_unresolved_variables(
    *,
    inner_radius_m: float | None,
    wall_thickness_m: float | None,
) -> list[str]:
    if inner_radius_m is not None or wall_thickness_m is not None:
        return []

    return [HOLLOW_ACCOUNTING_UNRESOLVED]


def _linear_two_ports(
    *,
    position_m: dict[str, float],
    length_m: float,
    nominal_radius_m: float,
    inner_radius_m: float,
    rotation_degrees: dict[str, float],
) -> list[dict[str, Any]]:
    port_a = port_transform(
        center_m=position_m,
        local_position_m={"x": 0.0, "y": -length_m / 2.0, "z": 0.0},
        local_direction={"x": 0.0, "y": -1.0, "z": 0.0},
        rotation_degrees=rotation_degrees,
    )
    port_b = port_transform(
        center_m=position_m,
        local_position_m={"x": 0.0, "y": length_m / 2.0, "z": 0.0},
        local_direction={"x": 0.0, "y": 1.0, "z": 0.0},
        rotation_degrees=rotation_degrees,
    )

    return [
        _port("A", nominal_radius_m, inner_radius_m, port_a),
        _port("B", nominal_radius_m, inner_radius_m, port_b),
    ]

def _elbow_90_ports(
    *,
    position_m: dict[str, float],
    bend_radius_m: float,
    nominal_radius_m: float,
    inner_radius_m: float,
    rotation_degrees: dict[str, float],
) -> list[dict[str, Any]]:
    # Matches current Godot elbow mesh:
    # Port A = horizontal inlet from the left
    # Port B = vertical outlet upward
    port_a = port_transform(
        center_m=position_m,
        local_position_m={
            "x": bend_radius_m,
            "y": -bend_radius_m,
            "z": 0.0,
        },
        local_direction={
            "x": -1.0,
            "y": 0.0,
            "z": 0.0,
        },
        rotation_degrees=rotation_degrees,
    )

    port_b = port_transform(
        center_m=position_m,
        local_position_m={
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
        local_direction={
            "x": 0.0,
            "y": 1.0,
            "z": 0.0,
        },
        rotation_degrees=rotation_degrees,
    )

    return [
        _port("A", nominal_radius_m, inner_radius_m, port_a),
        _port("B", nominal_radius_m, inner_radius_m, port_b),
    ]

def _port(
    port_id: str,
    nominal_radius_m: float,
    inner_radius_m: float,
    transform: dict[str, dict[str, float]],
) -> dict[str, Any]:
    return {
        "port_id": port_id,
        "connection_type": "pipe_end",
        "nominal_radius_m": nominal_radius_m,
        "inner_radius_m": inner_radius_m,
        "position_m": transform["position_m"],
        "direction": transform["direction"],
        "state": "open",
    }


def _coerce_material(material: PhysicalMaterial | str) -> PhysicalMaterial:
    if isinstance(material, PhysicalMaterial):
        return material

    return get_material(material)


def _inner_radius(
    *,
    outer_radius_m: float,
    inner_radius_m: float | None,
    wall_thickness_m: float | None,
) -> float:
    if inner_radius_m is not None:
        if inner_radius_m < 0.0 or inner_radius_m > outer_radius_m:
            raise ValueError("inner_radius_m must be between 0 and outer_radius_m")
        return inner_radius_m

    if wall_thickness_m is None:
        return 0.0

    if wall_thickness_m < 0.0 or wall_thickness_m > outer_radius_m:
        raise ValueError("wall_thickness_m must be between 0 and outer_radius_m")

    return outer_radius_m - wall_thickness_m


def _mass_from_volume(volume_m3: float, material: PhysicalMaterial) -> float:
    return volume_m3 * material.density_kg_m3


def _cylinder_volume_m3(radius_m: float, height_m: float) -> float:
    return math.pi * radius_m**2 * height_m


def _hollow_cylinder_volume_m3(
    outer_radius_m: float,
    inner_radius_m: float,
    height_m: float,
) -> float:
    return math.pi * max(0.0, outer_radius_m**2 - inner_radius_m**2) * height_m


__all__ = ["coupling", "elbow_90"]
