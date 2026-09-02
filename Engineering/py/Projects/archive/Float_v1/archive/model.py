from dataclasses import dataclass


WATER_DENSITY = 1000.0
GRAVITY = 9.80665


@dataclass
class FloatState:
    z: float = 0.0
    velocity: float = 0.0
    flooded_volume: float = 0.0
    time: float = 0.0


@dataclass
class FloatParams:
    dry_mass: float = 10.0
    object_volume: float = 0.02
    cross_section_area: float = 0.1
    damping: float = 8.0
    leak_rate: float = 0.0
    water_density: float = WATER_DENSITY


class FloatModel:
    def __init__(self, params: FloatParams):
        self.params = params
        self.state = FloatState()

    def submerged_volume(self) -> float:
        # Simple first-pass model:
        # z < 0 means object center/marker is below waterline.
        depth_fraction = max(0.0, min(1.0, -self.state.z + 0.5))
        return self.params.object_volume * depth_fraction

    def step(self, dt: float) -> dict:
        p = self.params
        s = self.state

        s.flooded_volume += p.leak_rate * dt

        submerged = self.submerged_volume()
        buoyant_force = p.water_density * submerged * GRAVITY
        flooded_mass = s.flooded_volume * p.water_density
        total_mass = p.dry_mass + flooded_mass

        weight = total_mass * GRAVITY
        damping_force = -p.damping * s.velocity
        net_force = buoyant_force - weight + damping_force

        acceleration = net_force / total_mass

        s.velocity += acceleration * dt
        s.z += s.velocity * dt
        s.time += dt

        return {
            "time": s.time,
            "z": s.z,
            "vertical_velocity": s.velocity,
            "vertical_acceleration": acceleration,
            "submerged_volume": submerged,
            "flooded_volume": s.flooded_volume,
            "buoyant_force": buoyant_force,
            "weight": weight,
            "net_force": net_force,
        }