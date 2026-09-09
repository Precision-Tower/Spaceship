from __future__ import annotations

from qps.cipher.ir.document import CipherDocument
from qps.cipher.profiles.base import SemanticCapability

from Engineering.py.cipher.mapping.geometry import (
    geometry_capabilities,
)


class EngineeringGeometryProfile:
    name = "engineering.geometry"

    def capabilities(
        self,
        document: CipherDocument,
    ) -> list[SemanticCapability]:
        return [
            SemanticCapability(
                semantic_name=item.semantic_name,
                implementation_symbol=item.implementation_symbol,
                source_path=item.source_path,
                source_line=item.source_line,
            )
            for item in geometry_capabilities(document)
        ]
