# scripts/cli/__init__.py

from UI.scripts.cli.commands import COMMAND_REGISTRY
from UI.scripts.agents.core.paths import PathResolver

def run_command(cmd_input: str):
    """
    The unified public API for executing commands.
    
    Usage:
        from UI.scripts.cli import run_command
        run_command("git-status --root /some/path")
    """
    # 1. Split input into name and arguments
    parts = cmd_input.split()
    if not parts:
        return "ERR: No command provided."
        
    cmd_name = parts[0]
    # 2. Get the class from UI.scripts registry
    cmd_class = COMMAND_REGISTRY.get(cmd_name)
    if not cmd_class:
        return f"ERR: Command '{cmd_name}' not found."
    
    # 3. Instantiate with a fresh PathResolver and execute
    # We use a simple Namespace for arguments as discussed
    import argparse
    resolver = PathResolver()
    instance = cmd_class(resolver)
    
    # Mocking args for the simple runner
    args = argparse.Namespace(**_parse_simple_args(parts[1:]))
    return instance.run(args)

def _parse_simple_args(args_list):
    """Simple parser to turn '--flag value' or '--flag' into a dict."""
    args_dict = {}
    for i, arg in enumerate(args_list):
        if arg.startswith("--"):
            key = arg.lstrip("-").replace("-", "_")
            # If next item exists and isn't a flag, use it as value
            if i + 1 < len(args_list) and not args_list[i+1].startswith("--"):
                args_dict[key] = args_list[i+1]
            else:
                args_dict[key] = True
    return args_dict

__all__ = ["run_command"]