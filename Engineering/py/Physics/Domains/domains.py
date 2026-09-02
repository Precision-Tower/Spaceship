from enum import Enum


class Domain(str, Enum):
    MASS_CENTRIC = "MC"
    FIELD_CENTRIC = "FC"


class MassCentricSubdomain(str, Enum):
    MECHANICAL = "mechanical"
    FLUID_DYNAMIC = "fluid_dynamic"
    BUOYANCY = "buoyancy"
    HYDRAULIC = "hydraulic"


class FieldCentricSubdomain(str, Enum):
    ELECTRIC = "electric"
    MAGNETIC = "magnetic"
    ELECTROMAGNETIC = "electromagnetic"
