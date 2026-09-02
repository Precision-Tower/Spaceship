import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Engineering.py.Projects.Float.dynamics import (
    FloatBody,
    simulate_vertical_cylinder_float,
)

OUTPUT_PATH = (
    Path(__file__).resolve().parent
    / "barrel_float_dynamic_result_packet.json"
)


def main() -> None:
    body = FloatBody(
        object_id="barrel_001",
        object_type="barrel",
        mass_kg=18.0,
        radius_m=0.285,
        height_m=0.82,
    )

    result = simulate_vertical_cylinder_float(
        body=body
    )

    packet = {
        "packet_type": "barrel_float_dynamic_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "environment": result["environment"],
        "barrel": result,
        "prohibited_interpretations": [
            "simulation_equals_truth",
            "animation_equals_validation",
            "floating_candidate_equals_validated_stability",
        ],
    }

    OUTPUT_PATH.write_text(
        json.dumps(packet, indent=2),
        encoding="utf-8"
    )

    print(f"Wrote {OUTPUT_PATH}")

    print(
        f"Equilibrium center Z: "
        f"{result['float_state']['equilibrium_center_z_m']:.4f} m"
    )

    print(
        f"Final center Z: "
        f"{result['float_state']['final_center_z_m']:.4f} m"
    )


if __name__ == "__main__":
    main()
