import json
from pathlib import Path
from datetime import datetime, timezone

from Dashboard.Engineering.Physics.Objects.objects import FloatBody
from Dashboard.Engineering.Physics.Domains.fluids import FRESH_WATER, SEA_WATER
from Engineering.py.Projects.Float.boat import Boat


INPUT_PATH = Path("Engineering/Projects/Float/float_input.json")
OUTPUT_PATH = Path("Engineering/Projects/Float/boat_result_packet.json")


def fluid_from_id(fluid_id: str):
    if fluid_id == "sea_water":
        return SEA_WATER

    return FRESH_WATER


def load_objects_from_input(path: Path) -> list[FloatBody]:
    data = json.loads(path.read_text(encoding="utf-8"))

    fluid_id = data.get("fluid_id", "fresh_water")
    fluid = fluid_from_id(fluid_id)

    return [
        FloatBody(
            object_id=obj["object_id"],
            object_type=obj["object_type"],
            mass_kg=float(obj["mass_kg"]),
            volume_m3=float(obj["volume_m3"]),
            flooded_volume_m3=float(obj.get("flooded_volume_m3", 0.0)),
            fluid=fluid,
        )
        for obj in data.get("objects", [])
    ]


def run_boat_trial() -> dict:
    objects = load_objects_from_input(INPUT_PATH)

    hull = next(obj for obj in objects if obj.object_type == "boat_hull")
    payloads = [obj for obj in objects if obj.object_type != "boat_hull"]

    boat = Boat(
        boat_id="boat_001",
        hull=hull,
        payloads=payloads,
    )

    packet = {
        "packet_type": "boat_float_trial_packet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_state": "calculated_candidate",
        "source_input_path": str(INPUT_PATH),
        "boat": boat.to_dict(),
    }

    OUTPUT_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    print(json.dumps(packet, indent=2))
    print(f"\nWrote packet: {OUTPUT_PATH.resolve()}")

    return packet


if __name__ == "__main__":
    run_boat_trial()