import json
from pathlib import Path

PACKET_PATH = Path(__file__).resolve().parent / "boat_assembly_packet.json"

packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))

assembly = packet["assembly"]
summary = assembly["summary"]
objects = assembly["objects"]

print("packet_type:", packet["packet_type"])
print("object_count:", len(objects))
print("source_packets:", [p["packet_type"] for p in packet.get("source_packets", [])])

print("\nsummary:")
for key in [
    "total_mass_kg",
    "total_displacement_volume_m3",
    "total_weight_force_n",
    "total_buoyant_force_n",
    "float_margin_n",
    "center_of_mass_candidate_m",
    "center_of_buoyancy_candidate_m",
]:
    print(f"  {key}: {summary.get(key)}")

print("\nobject_count_breakdown:")
for key, value in summary.get("object_count_breakdown", {}).items():
    print(f"  {key}: {value}")

print("\nassembly_group_breakdown:")
for key, value in summary.get("assembly_group_breakdown", {}).items():
    print(f"  {key}: {value}")

print("\nframe objects:")
for obj in objects:
    if obj.get("object_type") == "frame_beam":
        print(f"  {obj['object_id']} @ {obj['position_m']} size={obj.get('dimensions_m')}")
