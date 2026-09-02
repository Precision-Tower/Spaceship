from dataclasses import dataclass
import math


@dataclass(frozen=True)
class CylinderGeometry:
    radius_m: float
    height_m: float
    axis: str = "z"

    def volume_m3(self) -> float:
        return cylinder_volume_m3(self.radius_m, self.height_m)

    def cross_section_area_m2(self) -> float:
        return cylinder_cross_section_area_m2(self.radius_m)

    def to_dict(self) -> dict:
        return {
            "geometry_type": "cylinder",
            "radius_m": self.radius_m,
            "height_m": self.height_m,
            "axis": self.axis,
            "volume_m3": self.volume_m3(),
            "cross_section_area_m2": self.cross_section_area_m2(),
        }


@dataclass(frozen=True)
class BoxGeometry:
    size_x_m: float
    size_y_m: float
    size_z_m: float

    def volume_m3(self) -> float:
        return box_volume_m3(self.size_x_m, self.size_y_m, self.size_z_m)

    def to_dict(self) -> dict:
        return {
            "geometry_type": "box",
            "size_m": {
                "x": self.size_x_m,
                "y": self.size_y_m,
                "z": self.size_z_m,
            },
            "volume_m3": self.volume_m3(),
        }


def cylinder_volume_m3(radius_m: float, height_m: float) -> float:
    return math.pi * radius_m**2 * height_m


def box_volume_m3(size_x_m: float, size_y_m: float, size_z_m: float) -> float:
    return size_x_m * size_y_m * size_z_m


def cylinder_cross_section_area_m2(radius_m: float) -> float:
    return math.pi * radius_m**2
