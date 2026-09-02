import math
from typing import Any

from Engineering.py.Physics.materials import (
    PhysicalMaterial,
    get_material,
)


def barrel(
    *,
    object_id: str,
    object_type: str = "barrel",
    role: str,
    material: PhysicalMaterial | str = "hdpe_candidate",
    radius_m: float,
    height_m: float,
    position_m: dict[str, float],
    wall_thickness_m: float,
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    contributes_weight: bool = True,
    contributes_buoyancy: bool = True,
    rotation_degrees: dict[str, float] | None = None,
    display_position_m: dict[str, float] | None = None,
) -> dict:
    material_data = _coerce_material(material)
    inner_radius_m = max(0.0, radius_m - wall_thickness_m)
    inner_height_m = max(0.0, height_m - (2.0 * wall_thickness_m))
    external_volume_m3 = _cylinder_volume_m3(radius_m, height_m)
    internal_volume_m3 = _cylinder_volume_m3(inner_radius_m, inner_height_m)
    material_volume_m3 = max(0.0, external_volume_m3 - internal_volume_m3)
    mass_kg = _mass_from_volume(material_volume_m3, material_data)

    if rotation_degrees is None:
        rotation_degrees = {"x": 90.0, "y": 0.0, "z": 0.0}

    if display_position_m is None:
        display_position_m = dict(position_m)

    return _packet_object(
        object_id=object_id,
        object_type=object_type,
        physical_primitive="barrel",
        role=role,
        mass_kg=mass_kg,
        packet_volume_m3=external_volume_m3 if contributes_buoyancy else 0.0,
        material_volume_m3=material_volume_m3,
        position_m=position_m,
        dimensions_m={
            "radius": radius_m,
            "height": height_m,
            "wall_thickness": wall_thickness_m,
            "inner_radius": inner_radius_m,
            "inner_height": inner_height_m,
        },
        render={
            "primitive": "cylinder",
            "radius_m": radius_m,
            "height_m": height_m,
            "display_position_m": display_position_m,
            "rotation_degrees": rotation_degrees,
        },
        material=material_data,
        contributes_weight=contributes_weight,
        contributes_buoyancy=contributes_buoyancy,
        assembly_group=assembly_group,
        subsystem=subsystem,
        parent_group=parent_group,
        extra={
            "external_volume_m3": external_volume_m3,
            "internal_volume_m3": internal_volume_m3,
        },
    )

def plate(
    *,
    object_id: str,
    object_type: str,
    role: str,
    material: PhysicalMaterial | str,
    length_m: float,
    width_m: float,
    thickness_m: float,
    position_m: dict[str, float],
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    contributes_weight: bool = True,
    contributes_buoyancy: bool = False,
    display_position_m: dict[str, float] | None = None,
) -> dict:
    return block(
        object_id=object_id,
        object_type=object_type,
        physical_primitive="plate",
        role=role,
        material=material,
        size_m={
            "x": length_m,
            "y": thickness_m,
            "z": width_m,
        },
        position_m=position_m,
        assembly_group=assembly_group,
        subsystem=subsystem,
        parent_group=parent_group,
        contributes_weight=contributes_weight,
        contributes_buoyancy=contributes_buoyancy,
        display_position_m=display_position_m,
    )


def block(
    *,
    object_id: str,
    object_type: str,
    role: str,
    material: PhysicalMaterial | str,
    size_m: dict[str, float],
    position_m: dict[str, float],
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    contributes_weight: bool = True,
    contributes_buoyancy: bool = False,
    display_position_m: dict[str, float] | None = None,
    render_material_id: str | None = None,
    physical_primitive: str = "block",
) -> dict:
    material_data = _coerce_material(material)
    material_volume_m3 = (
        float(size_m["x"])
        * float(size_m["y"])
        * float(size_m["z"])
    )
    mass_kg = _mass_from_volume(material_volume_m3, material_data)

    if display_position_m is None:
        display_position_m = dict(position_m)

    render: dict[str, Any] = {
        "primitive": "box",
        "size_m": dict(size_m),
        "display_position_m": display_position_m,
    }

    if render_material_id is not None:
        render["material"] = {"material_id": render_material_id}

    return _packet_object(
        object_id=object_id,
        object_type=object_type,
        physical_primitive=physical_primitive,
        role=role,
        mass_kg=mass_kg,
        packet_volume_m3=material_volume_m3 if contributes_buoyancy else 0.0,
        material_volume_m3=material_volume_m3,
        position_m=position_m,
        dimensions_m=dict(size_m),
        render=render,
        material=material_data,
        contributes_weight=contributes_weight,
        contributes_buoyancy=contributes_buoyancy,
        assembly_group=assembly_group,
        subsystem=subsystem,
        parent_group=parent_group,
    )


def _packet_object(
    *,
    object_id: str,
    object_type: str,
    physical_primitive: str,
    role: str,
    mass_kg: float,
    packet_volume_m3: float,
    material_volume_m3: float,
    position_m: dict[str, float],
    dimensions_m: dict[str, Any],
    render: dict[str, Any],
    material: PhysicalMaterial,
    contributes_weight: bool,
    contributes_buoyancy: bool,
    assembly_group: str,
    subsystem: str,
    parent_group: str,
    extra: dict[str, Any] | None = None,
) -> dict:
    packet = {
        "object_id": object_id,
        "object_type": object_type,
        "physical_primitive": physical_primitive,
        "role": role,
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
    }

    if extra:
        packet.update(extra)

    return packet


def _coerce_material(material: PhysicalMaterial | str) -> PhysicalMaterial:
    if isinstance(material, PhysicalMaterial):
        return material

    return get_material(material)


def _pipe_inner_radius(
    *,
    outer_radius_m: float,
    wall_thickness_m: float | None,
    inner_radius_m: float | None,
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
