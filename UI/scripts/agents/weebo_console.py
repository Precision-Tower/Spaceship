import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DASHBOARD_ROOT = SCRIPT_DIR.parents[2]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# ---------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------

from UI.scripts.agents.core import PathResolver, WeeboMemory, WeeboAgent, CaliBridge
from UI.scripts.UI.scripts.agents.reasoners.gguf import CodeReasoner as Reasoner

# ---------------------------------------------------------------------
# Console colors
# ---------------------------------------------------------------------

CLR_CYAN = "\033[96m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_RESET = "\033[0m"
CLR_RED = "\033[91m"
CLR_BOLD = "\033[1m"


# ---------------------------------------------------------------------
# Model path resolution
# ---------------------------------------------------------------------

def find_model_path() -> str:
    local_model_dir = DASHBOARD_ROOT / "Models" / "local"
    local_config = SCRIPT_DIR / "weebo.local.json"
    preferred_local = local_model_dir / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
    configured_model = None
    if local_config.exists():
        config = json.loads(local_config.read_text(encoding="utf-8"))
        if str(config.get("backend", "gguf")).lower() == "gguf":
            configured_model = config.get("model_path")

    candidates = [
        os.environ.get("WEEBO_MODEL_PATH"),
        configured_model,
        preferred_local,
        DASHBOARD_ROOT / "Models" / "local" / "gemma-2b-it.Q4_K_M.gguf",
        DASHBOARD_ROOT / "Models" / "local" / "Gemma" / "gemma-2b-it.Q4_K_M.gguf",
        DASHBOARD_ROOT / "Models" / "local" / "gemma" / "gemma-2b-it.Q4_K_M.gguf",
    ]

    for candidate in candidates:
        if not candidate:
            continue

        path = Path(candidate).expanduser()
        if not path.is_absolute():
            path = DASHBOARD_ROOT / path

        if path.exists():
            return str(path)

    for path in sorted(local_model_dir.glob("*.gguf")):
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        "No WEEBO model found.\n\n"
        "Set WEEBO_MODEL_PATH or place the model at:\n"
        "  Dashboard/Models/local/gemma-2b-it.Q4_K_M.gguf\n\n"
        "Windows example:\n"
        '  $env:WEEBO_MODEL_PATH="C:\\Users\\Freed\\1\\Dashboard\\Models\\local\\gemma-2b-it.Q4_K_M.gguf"\n\n'
        "Linux example:\n"
        "  export WEEBO_MODEL_PATH=/home/spaztic/Core/Spaceship/Models/local/gemma-2b-it.Q4_K_M.gguf"
    )


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

def print_banner() -> None:
    print(f"""{CLR_CYAN}{CLR_BOLD}
  _      ________  ______ ____ 
 | | /| / / __/ __/  _ / __ \\
 | |/ |/ / _// _/_/ / / /_/ /
 |__/|__/___/___/___/\\____/ 
{CLR_GREEN}WEEBO Foundational AI | Partner for JARVIS Development
Status: READY | Target: Cali-Core
{CLR_RESET}""")


def print_help() -> None:
    print(f"\n{CLR_BOLD}WEEBO Commands:{CLR_RESET}")
    print(f"  {CLR_GREEN}ask <q>{CLR_RESET}       : Direct query to local GGUF reasoner.")
    print(f"  {CLR_GREEN}state{CLR_RESET}         : Query live system context via CaliBridge.")
    print(f"  {CLR_GREEN}plan <goal>{CLR_RESET}   : Formulate a JARVIS build plan.")
    print(f"  {CLR_GREEN}remember <n>{CLR_RESET}  : Store an operator note.")
    print(f"  {CLR_GREEN}recall{CLR_RESET}        : Review recent notes.")
    print(f"  {CLR_GREEN}todo <t>{CLR_RESET}      : Add task to WEEBO's queue.")
    print(f"  {CLR_GREEN}tasks{CLR_RESET}         : List all pending and active tasks.")
    print(f"  {CLR_GREEN}complete <id>{CLR_RESET} : Mark a specific task as DONE.")
    print(f"  {CLR_GREEN}clear{CLR_RESET}         : Clear the terminal viewport.")
    print(f"  {CLR_GREEN}exit/q{CLR_RESET}        : Quit.")
    print()


# ---------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------

def run_console() -> None:
    resolver = PathResolver()

    reasoner = Reasoner(find_model_path())
    bridge = CaliBridge(resolver)

    persistence_path = SCRIPT_DIR / "persistence"
    persistence_path.mkdir(parents=True, exist_ok=True)

    memory = WeeboMemory(str(persistence_path))
    weebo = WeeboAgent(reasoner, bridge, memory)
    memory.log_event("session_start", {"model_path": getattr(reasoner, "model_path", "unknown")})

    print_banner()

    while True:
        try:
            user_input = input(f"{CLR_CYAN}weebo>{CLR_RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        parts = user_input.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ["exit", "q"]:
            break

        if cmd == "help":
            print_help()

        elif cmd == "remember":
            if args:
                memory.remember(args)
                print(f"{CLR_GREEN}[*] WEEBO recorded the note.{CLR_RESET}")
            else:
                print(f"{CLR_RED}Usage: remember <note>{CLR_RESET}")

        elif cmd == "recall":
            memory.log_event("recall", {})
            print(f"\n{CLR_BOLD}--- RECENT NOTES ---{CLR_RESET}")
            for note in memory.recall():
                print(f"{CLR_CYAN}[{note['ts']}]{CLR_RESET} {note['note']}")
            print()

        elif cmd == "todo":
            if args:
                memory.todo(args)
                print(f"{CLR_GREEN}[*] Task added to the queue.{CLR_RESET}")
            else:
                print(f"{CLR_RED}Usage: todo <task>{CLR_RESET}")

        elif cmd == "tasks":
            memory.log_event("tasks", {})
            print(f"\n{CLR_BOLD}--- ACTIVE TASK QUEUE ---{CLR_RESET}")
            for task in memory.get_tasks():
                status_clr = CLR_GREEN if task["status"] == "PENDING" else CLR_YELLOW
                print(
                    f"  {CLR_BOLD}{task['id']}.{CLR_RESET} "
                    f"{task['task']} [{status_clr}{task['status']}{CLR_RESET}]"
                )
            print()

        elif cmd == "complete":
            if args:
                if memory.complete_task(args):
                    print(f"{CLR_GREEN}[*] Task {args} marked as DONE.{CLR_RESET}")
                else:
                    print(f"{CLR_RED}[!] Task ID {args} not found.{CLR_RESET}")
            else:
                print(f"{CLR_RED}Usage: complete <id>{CLR_RESET}")

        elif cmd == "plan":
            if args:
                print(f"{CLR_YELLOW}[*] WEEBO is formulating a plan...{CLR_RESET}")
                print(f"\n{weebo.plan(args)}\n")
            else:
                print(f"{CLR_RED}Usage: plan <goal>{CLR_RESET}")

        elif cmd == "state":
            print(f"\n{CLR_GREEN}{bridge.get_system_context()}{CLR_RESET}\n")

        elif cmd == "ask":
            if args:
                memory.log_event("ask", {"prompt": args})
                print(f"\n{weebo.process_command(args)}\n")
            else:
                print(f"{CLR_RED}Usage: ask <prompt>{CLR_RESET}")

        elif cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")

        else:
            memory.log_event("ask", {"prompt": user_input})
            print(f"\n{weebo.process_command(user_input)}\n")


if __name__ == "__main__":
    try:
        run_console()
    except Exception as exc:
        print(f"{CLR_RED}[WEEBO BOOT FAILURE]{CLR_RESET} {exc}")
        raise

