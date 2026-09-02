from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
BOAT_PACKET = ROOT / "Boat" / "boat_assembly_packet.json"

def load_packet(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def workbench_sections() -> dict:
    packet = load_packet(BOAT_PACKET)
    assembly = packet.get("assembly", {})
    objects = assembly.get("objects", [])
    summary = assembly.get("summary", {})

    return {
        "Overview": {
            "project": "Float",
            "packet_type": packet.get("packet_type"),
            "evidence_state": packet.get("evidence_state"),
            "object_count": len(objects),
            "total_mass_kg": summary.get("total_mass_kg"),
            "float_margin_n": summary.get("float_margin_n"),
        },
        "Packets": {
            "source_packets": packet.get("source_packets", []),
        },
        "Warnings": {
            "physical_overlap_warning_count": summary.get("physical_overlap_warning_count"),
            "blocked_interpretations": assembly.get("blocked_interpretations", []),
            "prohibited_interpretations": packet.get("prohibited_interpretations", []),
        },
        "Objects": {
            "object_types": sorted(set(str(o.get("object_type", "missing")) for o in objects)),
        },
    }