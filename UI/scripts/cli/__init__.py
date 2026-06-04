# scripts/cli/__init__.py

import argparse

from UI.scripts.cli.commands import COMMAND_REGISTRY
from UI.scripts.agents.core.paths import PathResolver


def run_command(
    cmd_input: str,
    resolver: PathResolver | None = None,
):
    """
    Unified public API for executing CLI commands.

    Examples:
        run_command("git-status")
        run_command("scan-repo --root repo")
        run_command(
            "runtime-state",
            resolver=PathResolver(spaceship_root=ROOT),
        )
    """

    parts = cmd_input.split()

    if not parts:
        return "ERR: No command provided."

    cmd_name = parts[0]

    cmd_class = COMMAND_REGISTRY.get(cmd_name)

    if not cmd_class:
        return f"ERR: Command '{cmd_name}' not found."

    resolver = resolver or PathResolver()

    instance = cmd_class(resolver)

    args = argparse.Namespace(
        **_parse_simple_args(parts[1:])
    )

    return instance.run(args)


def _parse_simple_args(args_list):
    """
    Convert:

        --flag value
        --flag

    into:

        {"flag": value}
        {"flag": True}
    """

    args_dict = {}

    i = 0

    while i < len(args_list):
        arg = args_list[i]

        if arg.startswith("--"):
            key = arg.lstrip("-").replace("-", "_")

            if (
                i + 1 < len(args_list)
                and not args_list[i + 1].startswith("--")
            ):
                args_dict[key] = args_list[i + 1]
                i += 2
                continue

            args_dict[key] = True

        i += 1

    return args_dict


__all__ = ["run_command"]