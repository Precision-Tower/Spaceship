import json
from pathlib import Path
from datetime import datetime, timezone

from Engineering.py.Projects.Float.barrel import BarrelCandidate


OUTPUT_PATH = Path("Engineering/Projects/Float/barrel_result_packet.json")


def run_barrel_trial() -> dict:
    barrel = BarrelCandidate(
        object_id="barrel_001",
        material_id="hdpe_candidate",
        outer_radius_m=0.285,
        height_m=0.82,
        wall_thickness_m=0.004,
        declared_mass_kg=18.0,
    )

    packet = {
        "packet_type": "barrel_candidate_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "object_or_system": "barrel_001",
        "barrel": barrel.to_dict(),
        "prohibited_interpretations": [
            "candidate_barrel_equals_measured_barrel",
            "calculated_volume_equals_validated_volume",
            "estimated_mass_equals_measured_mass",
            "sealed_state_equals_validated_no_leak",
            "geometry_display_equals_physical_truth",
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    print(json.dumps(packet, indent=2))
    print(f"\nWrote packet: {OUTPUT_PATH.resolve()}")

    return packet


if __name__ == "__main__":
    run_barrel_trial()
