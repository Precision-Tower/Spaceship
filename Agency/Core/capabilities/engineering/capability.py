from __future__ import annotations

from Agency.Core.capabilities.base import CapabilityDefinition
from Agency.Core.capabilities.registry import get_capability

ENGINEERING_CAPABILITY: CapabilityDefinition = get_capability("engineering")
