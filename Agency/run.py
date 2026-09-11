#!/usr/bin/env python3
"""Thin repository CLI compatibility entrypoint.

Semantic behavior remains owned by Agency/Core.  This file only routes the
documented repository-level command surface into those authoritative modules.
"""

from __future__ import annotations

import argparse
import sys


def run_agent_command(argv: list[str]) -> int:
    from Agency.Core.agents.discovery import discover_agents, launch_agent
    from Agency.Core.agents.tooling.create_agent import main as create_agent_main
    from Agency.Core.runtime import agent_shell

    if not argv:
        parser = argparse.ArgumentParser(prog="python run.py agent")
        parser.print_help()
        return 0

    command = argv[0]

    if command in {"-h", "--help"}:
        available = discover_agents()
        names = sorted(available)
        print("usage: python run.py agent {list,create,action,<AgentName>} ...")
        print()
        print("commands:")
        print("  list")
        print("  create")
        print("  action")
        print("  <AgentName>")
        for name in names:
            print(f"  {name}")
        return 0

    if command == "list":
        for name in discover_agents():
            print(name)
        return 0

    if command == "create":
        return create_agent_main(argv[1:])

    if command == "action":
        if len(argv) == 1 or argv[1] in {"-h", "--help"}:
            print("usage: python run.py agent action {propose,review,apply} ...")
            print()
            print("ActionPacket compatibility commands:")
            print("  propose uses WorkPackets.")
            print("  review and apply still use legacy ActionPackets.")
            print("  python run.py work-packet --help")
            return 0

        action = argv[1]
        from Agency.Core.agents.tooling import agent_actions

        if action == "review":
            parser = argparse.ArgumentParser(prog="python run.py agent action review")
            parser.add_argument("agent")
            parser.add_argument("packet", nargs="?")
            parser.add_argument("--latest", action="store_true")
            args = parser.parse_args(argv[2:])
            print("LEGACY_ACTION_PACKET_COMMAND")
            print("command: review")
            return agent_actions.review_action_packet(
                args.agent,
                packet_arg=args.packet,
                latest=args.latest,
            )

        if action == "apply":
            parser = argparse.ArgumentParser(prog="python run.py agent action apply")
            parser.add_argument("agent")
            parser.add_argument("packet", nargs="?")
            parser.add_argument("--latest", action="store_true")
            parser.add_argument("--approved", action="store_true")
            args = parser.parse_args(argv[2:])
            print("LEGACY_ACTION_PACKET_COMMAND")
            print("command: apply")
            return agent_actions.apply_action_packet(
                args.agent,
                packet_arg=args.packet,
                latest=args.latest,
                approved=args.approved,
            )

        if action == "propose":
            parser = argparse.ArgumentParser(prog="python run.py agent action propose")
            parser.add_argument("agent")
            parser.add_argument("task", nargs="+")
            args = parser.parse_args(argv[2:])
            return agent_actions.propose_action(args.agent, " ".join(args.task))

        print(f"ERR: unknown action command: {action}")
        return 2

    return launch_agent(command, argv[1:])


def run_task_command(argv: list[str]) -> int:
    from Agency.Core.work.tasks.editor.execution import main
    return main(argv)


def run_work_packet_command(argv: list[str]) -> int:
    from Agency.Core.work.work_packets.execution import main
    return main(argv)


def run_mission_command(argv: list[str]) -> int:
    from Agency.Core.work.missions.mission_factory import main
    return main(argv)


def run_dashboard_command(argv: list[str]) -> int:
    from Agency.Core.interfaces.cli.dashboard_cli import run_command
    return run_command(argv)


def run_status_command(argv: list[str]) -> int:
    if argv:
        print("usage: python run.py status")
        return 2
    from Agency.Core.runtime.agent_shell import status
    import json
    print(json.dumps(status(), indent=2, sort_keys=True))
    return 0


def run_scope_command(argv: list[str]) -> int:
    if argv:
        print("usage: python run.py scope")
        return 2
    from Agency.Core.foundation.paths import DASHBOARD_ROOT, AGENCY_ROOT
    import json
    print(json.dumps({
        "repository": str(DASHBOARD_ROOT),
        "agency": str(AGENCY_ROOT),
        "authority": "current_repository_checkout",
    }, indent=2, sort_keys=True))
    return 0


def run_shell_command(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print("usage: python run.py shell status")
        return 0
    if argv == ["status"]:
        print("OperatorShell runtime route: available")
        return 0
    print(f"ERR: unsupported shell command: {' '.join(argv)}")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description="Agency repository CLI compatibility entrypoint.",
    )
    parser.add_argument("command", nargs="?")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    if parsed.command is None:
        parser.print_help()
        return 0

    routes = {
        "agent": run_agent_command,
        "task": run_task_command,
        "work-packet": run_work_packet_command,
        "mission": run_mission_command,
        "cmd": run_dashboard_command,
        "status": run_status_command,
        "scope": run_scope_command,
        "shell": run_shell_command,
    }
    route = routes.get(parsed.command)
    if route is None:
        parser.error(f"unknown command: {parsed.command}")
    return route(parsed.args)


if __name__ == "__main__":
    raise SystemExit(main())
