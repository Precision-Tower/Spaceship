from datetime import datetime
from pathlib import Path
from runtime.paths import UI_ROOT


def _sanitize_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in value).strip().replace(" ", "_")


def run(args):
    category = args.category or "uncategorized"
    title = args.title or "packet_stub"
    packet_root = UI_ROOT / "Packets" / _sanitize_name(category)
    packet_root.mkdir(parents=True, exist_ok=True)

    filename = _sanitize_name(title)
    if not filename:
        filename = "packet_stub"
    path = packet_root / f"{filename}.txt"

    print("CREATE_PACKET")
    print(f"category: {category}")
    print(f"title: {title}")
    print(f"path: {path}")

    if path.exists():
        print("status: exists")
        return

    content = (
        f"Packet stub created on {datetime.utcnow().isoformat(timespec='seconds')} UTC\n"
        f"category: {category}\n"
        f"title: {title}\n"
        "status: candidate\n"
        "promoted: false\n"
    )
    path.write_text(content, encoding="utf-8")
    print("status: created")
    print(f"size: {path.stat().st_size}")
