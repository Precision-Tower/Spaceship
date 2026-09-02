from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable

CommandHandler = Callable[[argparse.Namespace], int]


@dataclass(frozen=True)
class MissionExecutionHandlers:
    status: CommandHandler
    inspect: CommandHandler
    pinboard_refresh: CommandHandler
    propose: CommandHandler
    mission_create: CommandHandler
    mission_status: CommandHandler
    mission_list: CommandHandler
    mission_show: CommandHandler
    mission_resume: CommandHandler
    mission_inspect: CommandHandler
    mission_plan: CommandHandler
    mission_replan: CommandHandler
    mission_resourcefulness: CommandHandler
    mission_propose: CommandHandler
    mission_review: CommandHandler
    mission_implement: CommandHandler
    mission_verify: CommandHandler


def build_mission_execution_parser(
    handlers: MissionExecutionHandlers,
    *,
    prog: str = "run.py agent local",
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status")
    p.set_defaults(func=handlers.status)

    p = sub.add_parser("inspect")
    p.set_defaults(func=handlers.inspect)

    p = sub.add_parser("pinboard-refresh")
    p.add_argument("--mission", default=None)
    p.set_defaults(func=handlers.pinboard_refresh)

    p = sub.add_parser("propose")
    p.add_argument("--intent", required=True)
    p.add_argument("--scope", action="append", required=True)
    p.add_argument("--start-model-server", action="store_true")
    p.set_defaults(func=handlers.propose)

    mission = sub.add_parser("mission")
    mission_sub = mission.add_subparsers(dest="mission_command", required=True)

    p = mission_sub.add_parser("create")
    p.add_argument("--intent", required=True)
    p.add_argument("--scope", action="append", required=True)
    p.set_defaults(func=handlers.mission_create)

    p = mission_sub.add_parser("status")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_status)

    p = mission_sub.add_parser("list")
    p.set_defaults(func=handlers.mission_list)

    p = mission_sub.add_parser("show")
    p.add_argument("mission")
    p.set_defaults(func=handlers.mission_show)

    p = mission_sub.add_parser("resume")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_resume)

    p = mission_sub.add_parser("inspect")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_inspect)

    p = mission_sub.add_parser("plan")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_plan)

    p = mission_sub.add_parser("replan")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_replan)

    p = mission_sub.add_parser("resourcefulness")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_resourcefulness)

    p = mission_sub.add_parser("propose")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_propose)

    p = mission_sub.add_parser("review")
    p.add_argument("--mission", required=True)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--reject", action="store_true")
    p.add_argument("--request-changes", action="store_true")
    p.add_argument("--note", default="")
    p.set_defaults(func=handlers.mission_review)

    p = mission_sub.add_parser("implement")
    p.add_argument("--mission", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=handlers.mission_implement)

    p = mission_sub.add_parser("verify")
    p.add_argument("--mission", required=True)
    p.set_defaults(func=handlers.mission_verify)

    return parser


def run_mission_execution_commands(
    argv: list[str] | None,
    handlers: MissionExecutionHandlers,
    *,
    prog: str = "run.py agent local",
) -> int:
    parser = build_mission_execution_parser(handlers, prog=prog)
    args = parser.parse_args(argv)
    return args.func(args)

