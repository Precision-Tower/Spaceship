from pathlib import Path
from Agency.Core.foundation.paths import AGENTS_ROOT, stable_path
from Agency.Core.interfaces.cli.commands.base import Command

class ListAgentsCommand(Command):
    name = "list-agents"

    def run(self, args):
        agents_root = AGENTS_ROOT
        if not agents_root.exists():
            print("AGENTS")
            print("status: missing")
            print(f"path: {agents_root}")
            return 1

        print("AGENTS")
        print(f"path: {agents_root}")

        for agent_dir in sorted(p for p in agents_root.iterdir() if p.is_dir()):
            checks = {
                "runtime": agent_dir / "runtime.yaml",
                "memory_sources": agent_dir / "memory" / "sources.yaml",
                "state": agent_dir / "state" / "agent_state.yaml",
                "autonomy": agent_dir / "autonomy" / "autonomy.yaml",
                "output_contract": agent_dir / "output_contract.yaml",
            }
            required = list(checks.values())
            present_count = sum(path.exists() for path in required)

            if present_count == len(required):
                status = "complete"
            elif present_count == 0:
                status = "empty"
            else:
                status = "partial"

            print()
            print(f"{agent_dir.name} [{status}]")
            for key, path in checks.items():
                print(f"  {key}: {path.exists()}")

        return 0
