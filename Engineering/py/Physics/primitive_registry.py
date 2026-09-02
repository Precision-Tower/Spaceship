from __future__ import annotations

from typing import Any


PRIMITIVE_COMMANDS: tuple[dict[str, Any], ...] = (
    {
        "id": "sphere",
        "label": "Sphere",
        "primitive": "sphere",
        "preview": {
            "shape": "sphere",
            "default_size_m": {"radius": 0.35},
        },
    },
    {
        "id": "box",
        "label": "Box",
        "primitive": "box",
        "preview": {
            "shape": "box",
            "default_size_m": {"x": 0.7, "y": 0.7, "z": 0.7},
        },
    },
    {
        "id": "cylinder",
        "label": "Cylinder",
        "primitive": "cylinder",
        "preview": {
            "shape": "cylinder",
            "default_size_m": {"radius": 0.3, "height": 0.8},
        },
    },
    {
        "id": "plane",
        "label": "Plane",
        "primitive": "plane",
        "preview": {
            "shape": "plane",
            "default_size_m": {"x": 1.0, "z": 1.0},
        },
    },
    {
        "id": "cone",
        "label": "Cone",
        "primitive": "cone",
        "preview": {
            "shape": "cone",
            "default_size_m": {"radius": 0.35, "height": 0.8},
        },
    },
    {
        "id": "torus",
        "label": "Torus",
        "primitive": "torus",
        "preview": {
            "shape": "torus",
            "default_size_m": {"inner_radius": 0.18, "outer_radius": 0.35},
        },
    },
)

OBJECT_COMMANDS: tuple[dict[str, Any], ...] = (
    {
        "id": "barrel",
        "label": "Barrel",
        "object_type": "barrel",
        "preview": {
            "shape": "cylinder",
            "default_size_m": {"radius": 0.3, "height": 0.8},
        },
    },
    {
        "id": "pipe",
        "label": "Pipe",
        "object_type": "pipe",
        "preview": {
            "shape": "cylinder",
            "default_size_m": {"radius": 0.08, "height": 1.0},
        },
    },
)


def workbench_primitive_registry() -> dict[str, list[dict[str, Any]]]:
    return {
        "Primitives": [dict(item) for item in PRIMITIVE_COMMANDS],
        "Objects": [dict(item) for item in OBJECT_COMMANDS],
    }
