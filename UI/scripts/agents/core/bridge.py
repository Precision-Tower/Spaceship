# agents/core/bridge.py
from UI.scripts.agents.core.paths import PathResolver
from UI.scripts.cli.commands import COMMAND_REGISTRY
import argparse

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