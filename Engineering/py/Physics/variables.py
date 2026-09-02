from dataclasses import dataclass
from typing import Any


@dataclass
class Variable:
    name: str
    value: Any
    unit: str
    domain: str

    source: str = "unspecified"
    unresolved: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "domain": self.domain,
            "source": self.source,
            "unresolved": self.unresolved,
        }
