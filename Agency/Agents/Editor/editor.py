from __future__ import annotations

import sys
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from Agency.Core.runtime.agent_shell import main as shell_main
from Agency.Core.runtime.authoritative_state import authoritative_state as runtime_authoritative_state

AGENT_NAME = "Editor"


def authoritative_state():
    return runtime_authoritative_state(AGENT_NAME)


def main(argv: list[str] | None = None) -> int:
    return shell_main(AGENT_NAME, argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
