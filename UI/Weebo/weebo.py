from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from UI.Weebo.memory.ceos_memory import CEOSMemory
from UI.Weebo.memory.decision_memory import DecisionMemory
from UI.Weebo.memory.mission_memory import MissionMemory


COMMANDS = {
    "answer",
    "approval",
    "boundaries",
    "brief",
    "card",
    "cards",
    "context",
    "decided",
    "decisions",
    "exists",
    "files",
    "focus",
    "inspect",
    "inventory",
    "mission",
    "next",
    "approved",
    "patch-plan",
    "propose",
    "rejected",
}


def split_command(argv: list[str]) -> tuple[str, str]:
    if not argv:
        return "brief", "Weebo supervised memory proposal layer"

    first = argv[0].lower()
    if first in COMMANDS:
        return first, " ".join(argv[1:]).strip()

    return "answer", " ".join(argv).strip()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command, query = split_command(argv)
    memory = CEOSMemory(ROOT)
    decisions = DecisionMemory(ROOT)
    mission = MissionMemory(ROOT)

    if command == "inventory":
        print(memory.inventory())
    elif command == "decisions":
        print(decisions.format_decisions())
    elif command == "approved":
        print(decisions.format_approved())
    elif command == "rejected":
        print(decisions.format_rejected())
    elif command == "decided":
        print(decisions.format_already_decided(query))
    elif command == "mission":
        print(mission.format_mission())
    elif command == "next":
        print(mission.format_next())
    elif command == "focus":
        print(mission.format_focus())
    elif command == "inspect":
        print(memory.format_inspect(query))
    elif command == "cards":
        print(memory.format_cards())
    elif command == "card":
        print(memory.format_card(query))
    elif command == "context":
        print(memory.build_context(query or "memory"))
    elif command == "exists":
        print(memory.format_existing_work(query))
    elif command == "files":
        print(memory.format_important_files(query))
    elif command == "boundaries":
        print(memory.format_authority_boundaries())
    elif command == "propose":
        goal = query or "Weebo supervised memory proposal layer"
        print(format_preproposal_check(memory, decisions, mission, goal))
    elif command == "patch-plan":
        task = query or "Unspecified supervised Weebo patch plan"
        print(format_patch_plan(memory, decisions, mission, task))
    elif command == "approval":
        print(memory.format_approval_items(query))
    elif command == "brief":
        print(memory.supervised_brief(query or "Weebo supervised memory proposal layer"))
    else:
        print(memory.answer(query or "What already exists?"))

    return 0


def format_preproposal_check(
    memory: CEOSMemory,
    decisions: DecisionMemory,
    mission: MissionMemory,
    goal: str,
) -> str:
    prior = decisions.already_decided(goal)
    sections = [
        "PRE-PROPOSAL CHECK",
        memory.format_existing_work(goal),
        memory.format_authority_boundaries(),
        decisions.format_already_decided(goal),
        mission.format_mission_check(),
        memory.format_memory_card_check(goal),
        memory.format_inspection_summary(goal),
    ]

    if prior["decided"]:
        sections.append(
            "DECISION GATE\n"
            "- Prior decision surfaced before new work.\n"
            "- Any next proposal must account for that decision and still waits for Seth approval."
        )

    sections.append(memory.format_proposal(goal))
    return "\n\n".join(sections)


def format_patch_plan(
    memory: CEOSMemory,
    decisions: DecisionMemory,
    mission: MissionMemory,
    task: str,
) -> str:
    sections = [
        "PATCH PLAN PREFLIGHT",
        format_preproposal_checks_only(memory, decisions, mission, task),
    ]
    write_result = memory.write_patch_packet(task)
    sections.append(memory.format_patch_packet_summary(write_result))
    return "\n\n".join(sections)


def format_preproposal_checks_only(
    memory: CEOSMemory,
    decisions: DecisionMemory,
    mission: MissionMemory,
    goal: str,
) -> str:
    prior = decisions.already_decided(goal)
    sections = [
        memory.format_existing_work(goal),
        memory.format_authority_boundaries(),
        decisions.format_already_decided(goal),
        mission.format_mission_check(),
        memory.format_memory_card_check(goal),
        memory.format_inspection_summary(goal),
    ]

    if prior["decided"]:
        sections.append(
            "DECISION GATE\n"
            "- Prior decision surfaced before new work.\n"
            "- Any patch packet must account for that decision and still waits for Seth approval."
        )

    return "\n\n".join(sections)


if __name__ == "__main__":
    raise SystemExit(main())
