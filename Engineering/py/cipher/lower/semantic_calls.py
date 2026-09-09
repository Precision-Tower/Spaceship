"""Engineering compatibility adapter for canonical Cipher lowering.

Canonical lowering lives in qps.cipher.lower.semantic_calls and is profile
neutral. Historical Engineering callers implicitly received Engineering
geometry semantics, so this compatibility surface injects that profile while
the universal core remains independent.
"""

from __future__ import annotations

from qps.cipher.lower.semantic_calls import (
    lower_semantic_calls as _lower_semantic_calls,
)
from Engineering.py.cipher.profiles.geometry import (
    EngineeringGeometryProfile,
)


def lower_semantic_calls(
    document,
    *,
    capability_provider=None,
):
    if capability_provider is None:
        capability_provider = (
            EngineeringGeometryProfile().capabilities
        )

    return _lower_semantic_calls(
        document,
        capability_provider=capability_provider,
    )
