"""Shared work orchestration contracts and execution structures.

Work is the umbrella for reusable execution structures that may be consumed by
agents, capabilities, missions, and future autonomous orchestration.
"""

from Agency.Core.work.work_packets import (
    WorkPacket,
    WorkPacketStep,
    authorize_patch,
    create_packet_from_file,
    dispatch_step,
    packet_from_mapping,
    packet_result,
    select_step,
    validate_work_packet,
)

__all__ = [
    "WorkPacket",
    "WorkPacketStep",
    "authorize_patch",
    "create_packet_from_file",
    "dispatch_step",
    "packet_from_mapping",
    "packet_result",
    "select_step",
    "validate_work_packet",
]
