# agents/core/bridge.py
from UI.scripts.agents.core.paths import PathResolver
from UI.scripts.cli.commands import COMMAND_REGISTRY
import argparse
from pathlib import Path

class CaliBridge:
    def __init__(self, resolver: PathResolver):
        self.resolver = resolver

    def _exec(self, cmd_input: str):
        """Dispatches commands directly to memory-resident classes."""
        try:
            parts = cmd_input.split()
            cmd_name, args_list = parts[0], parts[1:]
            
            cmd_class = COMMAND_REGISTRY.get(cmd_name)
            if not cmd_class:
                return f"ERR: Command '{cmd_name}' not found."

            # Instantiate with our shared path resolver
            instance = cmd_class(self.resolver)
            
            # Simulate CLI execution via Namespace
            # Note: We can map args_list to actual parser logic here
            args = argparse.Namespace(**self._parse_flags(args_list))
            return instance.run(args)
            
        except Exception as e:
            return f"ERR: Bridge failure: {str(e)}"

    def _parse_flags(self, args_list):
        return {arg.lstrip("-").replace("-", "_"): True for arg in args_list if arg.startswith("-")}

    def _safe_path(self, path: str) -> Path:
        root = self.resolver.spaceship_root.resolve()
        target = (root / path).resolve()

        if root not in target.parents and target != root:
            raise ValueError(f"Path escapes Spaceship root: {path}")

        return target

    def read_file(self, path: str) -> str:
        target = self._safe_path(path)

        if not target.exists():
            return f"ERR: file not found: {path}"

        if not target.is_file():
            return f"ERR: not a file: {path}"

        return target.read_text(encoding="utf-8", errors="replace")

    def list_files(self, path: str = ".") -> str:
        target = self._safe_path(path)

        if not target.exists():
            return f"ERR: path not found: {path}"

        if target.is_file():
            return target.relative_to(self.resolver.spaceship_root).as_posix()

        rows = []
        for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            rel = item.relative_to(self.resolver.spaceship_root).as_posix()
            rows.append(rel + ("/" if item.is_dir() else ""))

        return "\n".join(rows)

    def write_file(self, path: str, content: str) -> str:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"WROTE: {target.relative_to(self.resolver.spaceship_root).as_posix()}"