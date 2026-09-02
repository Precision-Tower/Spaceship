from dataclasses import dataclass, asdict


GRAVITY = 9.80665
WATER_DENSITY = 1000.0


@dataclass
class FloatObject:
    object_id: str
    object_type: str
    mass_kg: float
    volume_m3: float
    flooded_volume_m3: float = 0.0
    water_density_kg_m3: float = WATER_DENSITY
    gravity_m_s2: float = GRAVITY

    @property
    def flooded_mass_kg(self) -> float:
        return self.flooded_volume_m3 * self.water_density_kg_m3

    @property
    def total_mass_kg(self) -> float:
        return self.mass_kg + self.flooded_mass_kg

    @property
    def weight_force_n(self) -> float:
        return self.total_mass_kg * self.gravity_m_s2

    @property
    def max_buoyant_force_n(self) -> float:
        return self.water_density_kg_m3 * self.volume_m3 * self.gravity_m_s2

    @property
    def float_margin_n(self) -> float:
        return self.max_buoyant_force_n - self.weight_force_n

    @property
    def max_supported_mass_kg(self) -> float:
        return self.water_density_kg_m3 * self.volume_m3

    def to_dict(self) -> dict:
        data = asdict(self)
        data.update({
            "flooded_mass_kg": self.flooded_mass_kg,
            "total_mass_kg": self.total_mass_kg,
            "weight_force_n": self.weight_force_n,
            "max_buoyant_force_n": self.max_buoyant_force_n,
            "float_margin_n": self.float_margin_n,
            "max_supported_mass_kg": self.max_supported_mass_kg,
        })
        return data