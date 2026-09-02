from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicalMaterial:
    material_id: str
    common_name: str
    density_kg_m3: float
    source_state: str = "candidate"

    def to_dict(self) -> dict:
        return {
            "material_id": self.material_id,
            "common_name": self.common_name,
            "density_kg_m3": self.density_kg_m3,
            "source_state": self.source_state,
        }


HDPE_CANDIDATE = PhysicalMaterial(
    material_id="hdpe_candidate",
    common_name="High Density Polyethylene",
    density_kg_m3=950.0,
)

PVC_CANDIDATE = PhysicalMaterial(
    material_id="pvc_candidate",
    common_name="PVC",
    density_kg_m3=1400.0,
)

ALUMINUM_CANDIDATE = PhysicalMaterial(
    material_id="aluminum_candidate",
    common_name="Aluminum",
    density_kg_m3=2700.0,
)

TREATED_LUMBER_CANDIDATE = PhysicalMaterial(
    material_id="treated_lumber_candidate",
    common_name="Treated lumber",
    density_kg_m3=500.0,
)

ALUMINUM_OR_TREATED_LUMBER_CANDIDATE = PhysicalMaterial(
    material_id="aluminum_or_treated_lumber_candidate",
    common_name="Aluminum or treated lumber candidate",
    density_kg_m3=500.0,
)

FRESH_WATER_CANDIDATE = PhysicalMaterial(
    material_id="fresh_water_candidate",
    common_name="Fresh Water",
    density_kg_m3=1000.0,
)

SEA_WATER_CANDIDATE = PhysicalMaterial(
    material_id="sea_water_candidate",
    common_name="Sea Water",
    density_kg_m3=1025.0,
)


MATERIALS = {
    material.material_id: material
    for material in [
        HDPE_CANDIDATE,
        PVC_CANDIDATE,
        ALUMINUM_CANDIDATE,
        TREATED_LUMBER_CANDIDATE,
        ALUMINUM_OR_TREATED_LUMBER_CANDIDATE,
        FRESH_WATER_CANDIDATE,
        SEA_WATER_CANDIDATE,
    ]
}


def get_material(material_id: str) -> PhysicalMaterial:
    return MATERIALS[material_id]


def material_from_density(
    material_id: str,
    density_kg_m3: float,
    *,
    common_name: str | None = None,
    source_state: str = "candidate",
) -> PhysicalMaterial:
    return PhysicalMaterial(
        material_id=material_id,
        common_name=common_name or material_id,
        density_kg_m3=density_kg_m3,
        source_state=source_state,
    )
