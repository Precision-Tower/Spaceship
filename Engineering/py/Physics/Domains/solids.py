from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SolidObject:
    object_id: str
    object_type: str
    mass_kg: float
    volume_m3: float
    geometry: Any
    position_m: dict[str, float]
    material_id: str
    contributes_weight: bool = True
    contributes_buoyancy: bool = False

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "mass_kg": self.mass_kg,
            "volume_m3": self.volume_m3,
            "geometry": _to_packet_value(self.geometry),
            "position_m": dict(self.position_m),
            "material_id": self.material_id,
            "contributes_weight": self.contributes_weight,
            "contributes_buoyancy": self.contributes_buoyancy,
        }


def _to_packet_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()

    if isinstance(value, dict):
        return dict(value)

    return value
