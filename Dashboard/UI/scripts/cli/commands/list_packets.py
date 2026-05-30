from pathlib import Path
from runtime.paths import UI_ROOT


def run(args):
    packet_root = UI_ROOT / "Packets"
    print("LIST_PACKETS")
    if not packet_root.exists():
        print("status: missing")
        print("reason: Packet registry directory not found")
        print("packets: 0")
        return

    files = sorted([p for p in packet_root.rglob("*") if p.is_file() and p.name != ".keep"])
    print("status: listed")
    print(f"packets: {len(files)}")
    if not files:
        print("note: no packets present")
        return

    print("packet_paths:")
    for p in files:
        print(f"- {p.relative_to(packet_root)}")
