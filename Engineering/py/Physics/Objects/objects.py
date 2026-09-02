from dataclasses import dataclass, field

from Engineering.py.Physics.variables import Variable
from Engineering.py.Physics.Domains.fluids import Fluid, FRESH_WATER


@dataclass
class PhysicalObject:
    object_id: str
    object_type: str
    variables: dict[str, Variable] = field(default_factory=dict)

    def get_value(self, name: str, default=None):
        variable = self.variables.get(name)
        if variable is None:
            return default
        return variable.value

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "variables": {
                name: variable.to_dict()
                for name, variable in self.variables.items()
            },
        }


@dataclass
class FloatBody:
    object_id: str
    object_type: str
    mass_kg: float
    volume_m3: float
    flooded_volume_m3: float = 0.0

    fluid: Fluid = field(
        default_factory=lambda: FRESH_WATER
    )

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "object_type": self.object_type,
            "mass_kg": self.mass_kg,
            "volume_m3": self.volume_m3,
            "flooded_volume_m3": self.flooded_volume_m3,
            "fluid": self.fluid.to_dict(),
        }
