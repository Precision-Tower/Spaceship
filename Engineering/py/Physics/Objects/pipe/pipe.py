import math
from typing import Any

from Engineering.py.Physics.materials import PhysicalMaterial, get_material
from Engineering.py.Physics.Objects.pipe.hollow_pipe import pipe_inner_radius, cylinder_volume_m3, mass_from_volume, hollow_cylinder_volume_m3
from Engineering.py.Physics.Objects.pipe.catalog import pvc_pipe_dimensions

def pipe(
    *,
    object_id: str,
    object_type: str = "pipe",
    role: str,
    material: PhysicalMaterial | str,
    outer_radius_m: float,
    length_m: float,
    position_m: dict[str, float],
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    wall_thickness_m: float | None = None,
    inner_radius_m: float | None = None,
    fill_state: str = "empty",
    fill_material: PhysicalMaterial | str = "fresh_water_candidate",
    contributes_weight: bool = True,
    contributes_buoyancy: bool = False,
    rotation_degrees: dict[str, float] | None = None,
    display_position_m: dict[str, float] | None = None,
    ports: list[dict[str, Any]] | None = None,
) -> dict:
    material_data = _coerce_material(material)

    resolved_inner_radius_m = pipe_inner_radius(
        outer_radius_m=outer_radius_m,
        wall_thickness_m=wall_thickness_m,
        inner_radius_m=inner_radius_m,
    )

    external_volume_m3 = cylinder_volume_m3(outer_radius_m, length_m)
    contained_volume_m3 = cylinder_volume_m3(resolved_inner_radius_m, length_m)
    material_volume_m3 = hollow_cylinder_volume_m3(
        outer_radius_m,
        resolved_inner_radius_m,
        length_m,
    )

    mass_kg = mass_from_volume(material_volume_m3, material_data)

    if fill_state == "water_filled":
        mass_kg += mass_from_volume(
            contained_volume_m3,
            _coerce_material(fill_material),
        )
    elif fill_state != "empty":
        raise ValueError(f"Unsupported pipe fill_state: {fill_state}")

    rotation_degrees = rotation_degrees or {"x": 0.0, "y": 0.0, "z": 0.0}
    display_position_m = display_position_m or dict(position_m)

    if ports is None:
        ports = _default_pipe_ports(
            outer_radius_m=outer_radius_m,
            inner_radius_m=resolved_inner_radius_m,
            length_m=length_m,
            position_m=position_m,
            rotation_degrees=rotation_degrees,
        )

    return {
        "object_id": object_id,
        "object_type": object_type,
        "physical_primitive": "pipe",
        "role": role,
        "mass_kg": mass_kg,
        "volume_m3": external_volume_m3 if contributes_buoyancy else 0.0,
        "position_m": dict(position_m),
        "dimensions_m": {
            "radius": outer_radius_m,
            "length": length_m,
            "outer_radius": outer_radius_m,
            "inner_radius": resolved_inner_radius_m,
            "wall_thickness": outer_radius_m - resolved_inner_radius_m,
        },
        "render": {
            "primitive": "cylinder",
            "radius_m": outer_radius_m,
            "height_m": length_m,
            "display_position_m": display_position_m,
            "rotation_degrees": rotation_degrees,
        },
        "material": material_data.material_id,
        "material_density_kg_m3": material_data.density_kg_m3,
        "material_volume_m3": material_volume_m3,
        "contributes_weight": contributes_weight,
        "contributes_buoyancy": contributes_buoyancy,
        "assembly_group": assembly_group,
        "subsystem": subsystem,
        "parent_group": parent_group,
        "fill_state": fill_state,
        "contained_volume_m3": contained_volume_m3,
        "ports": ports,
    }

def pvc_pipe(
    *,
    nominal_size_in: float,
    schedule: str = "SCH40",
    **kwargs: Any,
) -> dict:
    dims = pvc_pipe_dimensions(
        nominal_size_in=nominal_size_in,
        schedule=schedule,
    )

    packet = pipe(
        outer_radius_m=dims["outer_radius_m"],
        inner_radius_m=dims["inner_radius_m"],
        wall_thickness_m=dims["wall_thickness_m"],
        **kwargs,
    )

    packet["pipe_spec"] = dims
    packet["dimensions_m"]["nominal_size_in"] = nominal_size_in
    packet["dimensions_m"]["schedule"] = schedule
    packet["dimensions_m"]["outer_diameter_m"] = dims["outer_diameter_m"]
    packet["dimensions_m"]["inner_diameter_m"] = dims["inner_diameter_m"]

    return packet

def pipe_segment(**kwargs: Any) -> dict:
    return pipe(**kwargs)


def _coerce_material(material: PhysicalMaterial | str) -> PhysicalMaterial:
    if isinstance(material, PhysicalMaterial):
        return material
    return get_material(material)

def _default_pipe_ports(
    *,
    outer_radius_m: float,
    inner_radius_m: float,
    length_m: float,
    position_m: dict[str, float],
    rotation_degrees: dict[str, float],
) -> list[dict[str, Any]]:
    return [
        {
            "port_id": "A",
            "connection_type": "pipe_end",
            "nominal_radius_m": outer_radius_m,
            "inner_radius_m": inner_radius_m,
            "position_m": {
                "x": position_m["x"] - (length_m / 2.0),
                "y": position_m["y"],
                "z": position_m["z"],
            },
            "direction": {"x": -1.0, "y": 0.0, "z": 0.0},
            "state": "open",
        },
        {
            "port_id": "B",
            "connection_type": "pipe_end",
            "nominal_radius_m": outer_radius_m,
            "inner_radius_m": inner_radius_m,
            "position_m": {
                "x": position_m["x"] + (length_m / 2.0),
                "y": position_m["y"],
                "z": position_m["z"],
            },
            "direction": {"x": 1.0, "y": 0.0, "z": 0.0},
            "state": "open",
        },
    ]

def port_transform(
    *,
    center_m: dict[str, float],
    local_position_m: dict[str, float],
    local_direction: dict[str, float],
    rotation_degrees: dict[str, float],
) -> dict:
    # Minimal rotation support around Z for now.
    import math

    z_rad = math.radians(rotation_degrees.get("z", 0.0))
    cos_z = math.cos(z_rad)
    sin_z = math.sin(z_rad)

    lx = local_position_m["x"]
    ly = local_position_m["y"]
    lz = local_position_m["z"]

    dx = local_direction["x"]
    dy = local_direction["y"]
    dz = local_direction["z"]

    world_pos = {
        "x": center_m["x"] + (lx * cos_z - ly * sin_z),
        "y": center_m["y"] + (lx * sin_z + ly * cos_z),
        "z": center_m["z"] + lz,
    }

    world_dir = {
        "x": dx * cos_z - dy * sin_z,
        "y": dx * sin_z + dy * cos_z,
        "z": dz,
    }

    return {
        "position_m": world_pos,
        "direction": world_dir,
    }