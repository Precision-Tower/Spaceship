from dataclasses import dataclass

from Engineering.py.Physics.constants import GRAVITY_EARTH_M_S2
from Engineering.py.Physics.materials import (
    FRESH_WATER_CANDIDATE,
    SEA_WATER_CANDIDATE,
)


@dataclass(frozen=True)
class Fluid:
    fluid_id: str
    density_kg_m3: float
    material_id: str
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "fluid_id": self.fluid_id,
            "density_kg_m3": self.density_kg_m3,
            "material_id": self.material_id,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FluidEnvironment:
    environment_id: str
    fluid: Fluid
    gravity_m_s2: float = GRAVITY_EARTH_M_S2
    surface_z_m: float = 0.0
    size_x_m: float = 6.0
    size_z_m: float = 6.0
    depth_m: float = 0.5
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "environment_id": self.environment_id,
            "fluid": self.fluid.to_dict(),
            "gravity_m_s2": self.gravity_m_s2,
            "surface_z_m": self.surface_z_m,
            "render": {
                "primitive": "fluid_volume",
                "size_m": {
                    "x": self.size_x_m,
                    "y": self.depth_m,
                    "z": self.size_z_m,
                },
                "surface_z_m": self.surface_z_m,
                "depth_m": self.depth_m,
                "material": {
                    "fluid_id": self.fluid.fluid_id,
                    "alpha": 0.25,
                },
            },
            "notes": self.notes,
        }


FRESH_WATER = Fluid(
    fluid_id="fresh_water",
    density_kg_m3=FRESH_WATER_CANDIDATE.density_kg_m3,
    material_id=FRESH_WATER_CANDIDATE.material_id,
    notes="fresh_water_default_candidate",
)


SEA_WATER = Fluid(
    fluid_id="sea_water",
    density_kg_m3=SEA_WATER_CANDIDATE.density_kg_m3,
    material_id=SEA_WATER_CANDIDATE.material_id,
    notes="sea_water_default_candidate",
)


FRESH_WATER_ENVIRONMENT = FluidEnvironment(
    environment_id="fresh_water_test",
    fluid=FRESH_WATER,
    size_x_m=3.0,
    size_z_m=3.0,
)

SEA_WATER_ENVIRONMENT = FluidEnvironment(
    environment_id="water_environment_001",
    fluid=SEA_WATER,
)
