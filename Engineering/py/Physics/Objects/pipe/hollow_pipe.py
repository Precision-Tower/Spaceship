import math
from Engineering.py.Physics.materials import PhysicalMaterial

def pipe_inner_radius(
    *,
    outer_radius_m: float,
    wall_thickness_m: float | None,
    inner_radius_m: float | None,
) -> float:
    if outer_radius_m <= 0.0:
        raise ValueError("outer_radius_m must be greater than 0")

    if inner_radius_m is not None:
        if inner_radius_m < 0.0 or inner_radius_m > outer_radius_m:
            raise ValueError("inner_radius_m must be between 0 and outer_radius_m")
        return inner_radius_m

    if wall_thickness_m is None:
        return 0.0

    if wall_thickness_m < 0.0 or wall_thickness_m > outer_radius_m:
        raise ValueError("wall_thickness_m must be between 0 and outer_radius_m")

    return outer_radius_m - wall_thickness_m

def mass_from_volume(volume_m3: float, material: PhysicalMaterial) -> float:
    return volume_m3 * material.density_kg_m3


def cylinder_volume_m3(radius_m: float, height_m: float) -> float:
    if radius_m < 0.0:
        raise ValueError("radius_m must be non-negative")
    if height_m < 0.0:
        raise ValueError("height_m must be non-negative")
    return math.pi * radius_m**2 * height_m


def hollow_cylinder_volume_m3(
    outer_radius_m: float,
    inner_radius_m: float,
    height_m: float,
) -> float:
    return math.pi * max(0.0, outer_radius_m**2 - inner_radius_m**2) * height_m
