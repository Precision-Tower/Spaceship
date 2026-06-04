# scripts/cli/commands/packet_commands.py
from datetime import datetime
from UI.scripts.cli.commands.base import Command

class CreatePacketCommand(Command):
    def run(self, args):
        category = args.category or "uncategorized"
        title = args.title or "packet_stub"
        
        # Access UI_ROOT via the resolver
        packet_root = self.resolver.ui_root / "Packets" / self._sanitize(category)
        packet_root.mkdir(parents=True, exist_ok=True)

        filename = self._sanitize(title) or "packet_stub"
        path = packet_root / f"{filename}.txt"

        print("CREATE_PACKET")
        print(f"category: {category}\ntitle: {title}\npath: {path}")

        if path.exists():
            return self._report("exists")

        content = (
            f"Packet stub created on {datetime.utcnow().isoformat(timespec='seconds')} UTC\n"
            f"category: {category}\n"
            f"title: {title}\n"
            "status: candidate\n"
            "promoted: false\n"
        )
        path.write_text(content, encoding="utf-8")
        print(f"status: created\nsize: {path.stat().st_size}")

    def _sanitize(self, value: str) -> str:
        return "".join(c if c.isalnum() or c in "-_ " else "_" for c in value).strip().replace(" ", "_")

class ListPacketsCommand(Command):
    def run(self, args):
        packet_root = self.resolver.ui_root / "Packets"
        print("LIST_PACKETS")
        
        if not packet_root.exists():
            return self._report("missing", "Packet registry directory not found")

        files = sorted([p for p in packet_root.rglob("*") if p.is_file() and p.name != ".keep"])
        print(f"status: listed\npackets: {len(files)}")
        
        if files:
            print("packet_paths:")
            for p in files:
                print(f"- {p.relative_to(packet_root)}")
