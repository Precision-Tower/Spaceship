from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import uuid


@dataclass
class FloatObservationPacket:
    packet_id: str
    packet_type: str
    object_or_system: str
    declared_state: str
    evidence_state: str
    measurements: dict
    unresolved_variables: list
    prohibited_interpretations: list
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def classify_state(sample: dict) -> str:
    z = sample["z"]
    v = sample["vertical_velocity"]

    if sample["flooded_volume"] > 0.01:
        return "flooding_observed"

    if abs(v) > 0.05:
        return "oscillation_or_transition"

    if z < -0.25:
        return "submerged"

    if -0.25 <= z <= 0.25:
        return "float"

    return "unresolved"

def classify_history(samples: list[dict]) -> list[str]:
    states = []

    min_z = min(s["z"] for s in samples)
    max_z = max(s["z"] for s in samples)
    max_v = max(abs(s["vertical_velocity"]) for s in samples)

    if min_z < -0.25:
        states.append("forced_submerge")

    if max_z > 0.25:
        states.append("overshoot_above_float_band")

    if max_v > 0.5:
        states.append("oscillation_or_transition")

    last_z = samples[-1]["z"]
    last_v = samples[-1]["vertical_velocity"]

    if -0.25 <= last_z <= 0.25 and abs(last_v) < 0.05:
        states.append("returned_to_float_band")
    else:
        states.append("unresolved_final_state")

    return states

def build_packet(samples: list[dict]) -> FloatObservationPacket:
    last = samples[-1]
    declared_state = classify_state(last)

    return FloatObservationPacket(
        packet_id=f"float_packet_{uuid.uuid4().hex[:8]}",
        packet_type="runtime_report_packet",
        object_or_system="FloatingBox",
        declared_state=declared_state,
        evidence_state="simulated",
        measurements={
            "last_sample": last,
            "sample_count": len(samples),
            "max_z": max(s["z"] for s in samples),
            "min_z": min(s["z"] for s in samples),
            "max_vertical_velocity": max(abs(s["vertical_velocity"]) for s in samples),
            "state_history": classify_history(samples),
        },
        unresolved_variables=[
            "real_object_geometry",
            "actual_displaced_volume_curve",
            "real_water_drag",
            "center_of_mass",
            "center_of_buoyancy",
            "leak_behavior_if_any",
        ],
        prohibited_interpretations=[
            "simulation_equals_validation",
            "float_equals_stability",
            "oscillation_equals_stability",
            "visualization_equals_evidence",
            "route_completion_equals_claim_support",
        ],
        created_at=datetime.now(timezone.utc).isoformat(),
    )