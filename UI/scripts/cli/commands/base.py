# scripts/cli/commands/base.py
from UI.scripts.agents.core.paths import PathResolver

class Command:
    """
    Base class for all CLI commands.
    Ensures every command has access to the central path discovery engine.
    """
    def __init__(self, resolver: PathResolver):
        self.resolver = resolver
    
    def run(self, args):
        """
        Execute the command logic.
        
        :param args: A Namespace object containing parsed CLI arguments.
        """
        raise NotImplementedError(f"Command {self.__class__.__name__} must implement run()")

    def _report(self, status: str, message: str = ""):
        """Helper to standardize output format for the Agent to parse."""
        print(f"status: {status}")
        if message:
            print(f"message: {message}")