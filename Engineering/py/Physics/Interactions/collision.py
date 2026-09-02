from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AABB:
    object_id: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float


def object_aabb(obj: dict[str, Any]) -> AABB | None:
    object_id = str(obj.get("object_id", "unknown"))
    primitive = str(obj.get("physical_primitive", obj.get("primitive", "")))

    position = obj.get("position_m", {})
    render = obj.get("render", {})
    display_position = render.get("display_position_m", position)

    cx = float(display_position.get("x", position.get("x", 0.0)))
    cy = float(display_position.get("y", position.get("y", 0.0)))
    cz = float(display_position.get("z", position.get("z", 0.0)))

    if primitive == "barrel":
        barrel = obj.get("barrel", {})
        radius = float(barrel.get("radius_m", obj.get("dimensions_m", {}).get("radius", 0.0)))
        length = float(barrel.get("height_m", obj.get("dimensions_m", {}).get("height", 0.0)))
        rotation = render.get("rotation_degrees", {})

        # Godot cylinder height defaults along Y.
        # z=90 means long axis visually along X.
        # x=90 means long axis visually along Z.
        rx = float(rotation.get("x", 0.0))
        rz = float(rotation.get("z", 0.0))

        if abs(rz) > 45.0:
            half_x = length / 2.0
            half_y = radius
            half_z = radius
        elif abs(rx) > 45.0:
            half_x = radius
            half_y = radius
            half_z = length / 2.0
        else:
            half_x = radius
            half_y = length / 2.0
            half_z = radius

        return AABB(
            object_id=object_id,
            min_x=cx - half_x,
            max_x=cx + half_x,
            min_y=cy - half_y,
            max_y=cy + half_y,
            min_z=cz - half_z,
            max_z=cz + half_z,
        )

    if primitive == "pipe" or obj.get("object_type") == "connector_pipe":
        dimensions = obj.get("dimensions_m", {})
        radius = float(
            dimensions.get(
                "outer_radius",
                dimensions.get("radius", 0.0),
            )
        )
        length = float(dimensions.get("length", 0.0))
        rotation = render.get("rotation_degrees", {})

        rx = float(rotation.get("x", 0.0))
        rz = float(rotation.get("z", 0.0))

        if abs(rz) > 45.0:
            half_x = length / 2.0
            half_y = radius
            half_z = radius
        elif abs(rx) > 45.0:
            half_x = radius
            half_y = radius
            half_z = length / 2.0
        else:
            half_x = radius
            half_y = length / 2.0
            half_z = radius

        return AABB(
            object_id=object_id,
            min_x=cx - half_x,
            max_x=cx + half_x,
            min_y=cy - half_y,
            max_y=cy + half_y,
            min_z=cz - half_z,
            max_z=cz + half_z,
        )

    if primitive == "block" or obj.get("object_type") == "frame_beam":
        dimensions = obj.get("dimensions_m", {})
        sx = float(dimensions.get("x", 0.0))
        sy = float(dimensions.get("y", 0.0))
        sz = float(dimensions.get("z", 0.0))

        return AABB(
            object_id=object_id,
            min_x=cx - sx / 2.0,
            max_x=cx + sx / 2.0,
            min_y=cy - sy / 2.0,
            max_y=cy + sy / 2.0,
            min_z=cz - sz / 2.0,
            max_z=cz + sz / 2.0,
        )

    return None


def aabb_overlap(a: AABB, b: AABB, clearance_m: float = 0.0) -> bool:
    return (
        a.min_x - clearance_m <= b.max_x
        and a.max_x + clearance_m >= b.min_x
        and a.min_y - clearance_m <= b.max_y
        and a.max_y + clearance_m >= b.min_y
        and a.min_z - clearance_m <= b.max_z
        and a.max_z + clearance_m >= b.min_z
    )


def find_overlaps(
    objects: list[dict[str, Any]],
    clearance_m: float = 0.0,
    ignore_same_group: bool = False,
    ignored_object_types: set[str] | None = None,
) -> list[dict[str, Any]]:
    if ignored_object_types is None:
        ignored_object_types = set()

    boxes: list[tuple[dict[str, Any], AABB]] = []

    for obj in objects:
        if str(obj.get("object_type", "")) in ignored_object_types:
            continue

        box = object_aabb(obj)
        if box is not None:
            boxes.append((obj, box))

    overlaps: list[dict[str, Any]] = []

    for i in range(len(boxes)):
        obj_a, box_a = boxes[i]

        for j in range(i + 1, len(boxes)):
            obj_b, box_b = boxes[j]

            if ignore_same_group and obj_a.get("assembly_group") == obj_b.get("assembly_group"):
                continue

            if aabb_overlap(box_a, box_b, clearance_m=clearance_m):
                overlaps.append(
                    {
                        "object_a": box_a.object_id,
                        "object_b": box_b.object_id,
                        "assembly_group_a": obj_a.get("assembly_group", "unknown"),
                        "assembly_group_b": obj_b.get("assembly_group", "unknown"),
                        "object_type_a": obj_a.get("object_type", "unknown"),
                        "object_type_b": obj_b.get("object_type", "unknown"),
                        "clearance_m": clearance_m,
                    }
                )

    return overlaps


def validate_no_overlaps(
    objects: list[dict[str, Any]],
    clearance_m: float = 0.0,
    ignored_object_types: set[str] | None = None,
) -> None:
    overlaps = find_overlaps(
        objects,
        clearance_m=clearance_m,
        ignored_object_types=ignored_object_types,
    )

    if not overlaps:
        return

    preview = "\n".join(
        f"- {entry['object_a']} overlaps {entry['object_b']}"
        for entry in overlaps[:20]
    )

    raise ValueError(
        "Physical overlap validation failed:\n"
        + preview
        + (
            f"\n... and {len(overlaps) - 20} more overlaps"
            if len(overlaps) > 20
            else ""
        )
    )
