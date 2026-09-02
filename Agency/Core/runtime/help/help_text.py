"""
Dashboard CLI subsystem metadata.

This module owns operator-facing descriptions for Dashboard's
top-level capability groups. Parser construction consumes this data
but does not own it.
"""

SUBSYSTEMS = {
    "shell": {
        "help_text": "Open the Dashboard operator shell.",
        "overview": """
Shell

Open the interactive Dashboard operator interface.

Use:

    python run.py shell <command>

to route commands through the operator shell.
""".strip(),
    },

    "workbench": {
        "help_text": "Operate the engineering workbench.",
        "overview": """
Workbench

Run workbench-oriented engineering operations.

Use:

    python run.py workbench <command>

for available workbench actions.
""".strip(),
    },

    "task": {
        "help_text": "Execute and inspect task packets.",
        "overview": """
Task

Execute individual engineering tasks.

Use:

    python run.py task <command>

for task-specific operations.
""".strip(),
    },

    "mission": {
        "help_text": "Coordinate engineering work.",
        "overview": """
Mission

Coordinate long-running engineering work.

Primary lifecycle

  create       Create a mission
  inspect      Inspect mission state
  transition   Move a mission through its lifecycle
  handoff      Transfer ownership

Use:

    python run.py mission <command> --help

for command-specific documentation.
""".strip(),
    },

    "repository": {
        "help_text": "Repository engineering operations.",
        "overview": """
Repository

Operate on repositories and engineering state.

Use:

    python run.py repository <command>

for repository-specific operations.
""".strip(),
    },

    "remote": {
        "help_text": "Operate configured remote systems.",
        "overview": """
Remote

Route supported operations to configured remote systems.

Use:

    python run.py remote <command>

for remote-specific operations.
""".strip(),
    },

    "state": {
        "help_text": "Inspect and operate Dashboard state.",
        "overview": """
State

Inspect and operate persistent Dashboard state.

Use:

    python run.py state <command>

for state-specific operations.
""".strip(),
    },

    "godot": {
        "help_text": "Launch and inspect the Godot integration.",
        "overview": """
Godot

Operate the Dashboard Godot cockpit integration.

Use:

    python run.py godot <command>

for supported Godot operations.
""".strip(),
    },

    "status": {
        "help_text": "Report Dashboard readiness and paths.",
        "overview": """
Status

Report Dashboard readiness and authoritative runtime paths.

Run:

    python run.py status
""".strip(),
    },

    "scope": {
        "help_text": "Report the current operational scope.",
        "overview": """
Scope

Inspect the current Dashboard operational scope and authority.

Run:

    python run.py scope
""".strip(),
    },

    "agent": {
        "help_text": "Agent lifecycle and execution.",
        "overview": """
Agent

Manage engineering agents.

Use:

    python run.py agent <command>

for agent-specific operations.
""".strip(),
    },

    "model": {
        "help_text": "Operate local and remote model services.",
        "overview": """
Model

Inspect and operate Dashboard model services.

Primary operations include model status, local inference,
agent-directed inference, and configured remote model routes.

Use:

    python run.py model <command> --help

for model-specific documentation.
""".strip(),
    },

    "cmd": {
        "help_text": "Execute a Dashboard command route.",
        "overview": """
Command

Execute a command through Dashboard's command-routing layer.

Use:

    python run.py cmd <command>
""".strip(),
    },

    "watch": {
        "help_text": "Inspect recent Dashboard watch events.",
        "overview": """
Watch

Display recent Dashboard watch-log events.

Use:

    python run.py watch --lines <count>
""".strip(),
    },
}
