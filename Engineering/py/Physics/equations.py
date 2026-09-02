from dataclasses import dataclass, field
from typing import Any


@dataclass
class EquationResult:
    equation_id: str
    description: str
    inputs: dict[str, Any]
    output_name: str
    output_value: float
    output_unit: str
    domain: str
    blocked_interpretations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "equation_id": self.equation_id,
            "description": self.description,
            "inputs": self.inputs,
            "output_name": self.output_name,
            "output_value": self.output_value,
            "output_unit": self.output_unit,
            "domain": self.domain,
            "blocked_interpretations": self.blocked_interpretations,
        }
