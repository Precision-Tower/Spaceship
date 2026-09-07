from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.plan import build_conversion_plan


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        source = root / "example.py"
        source.write_text(
            "VALUE = 2\n"
            "\n"
            "def twice(x):\n"
            "    value = x * VALUE\n"
            "    return value\n",
            encoding="utf-8",
        )

        destination = root / "out.qps"

        before = sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
        )

        plan = build_conversion_plan(
            source,
            destination,
            workspace_root=root,
        )

        after = sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
        )

        require(plan.ready, repr(plan.blockers))
        require(len(plan.units) == 1, repr(plan.units))
        require(
            plan.units[0].destination == destination,
            repr(plan.units[0]),
        )
        require(
            not destination.exists(),
            "planning wrote destination",
        )
        require(
            before == after,
            "planning mutated filesystem",
        )

        destination.write_text(
            "existing\n",
            encoding="utf-8",
        )

        blocked = build_conversion_plan(
            source,
            destination,
            workspace_root=root,
        )

        require(
            not blocked.ready,
            "existing destination must block plan",
        )
        require(
            any(
                "destination exists" in blocker
                for blocker in blocked.blockers
            ),
            repr(blocked.blockers),
        )

        partial_source = root / "partial.py"

        partial_source.write_text(
            "from dataclasses import dataclass\n"
            "\n"
            "@dataclass\n"
            "class Result:\n"
            "    value: float\n"
            "\n"
            "def build(x):\n"
            "    return Result(value=x)\n",
            encoding="utf-8",
        )

        partial_plan = build_conversion_plan(
            partial_source,
            root / "partial.qps",
            workspace_root=root,
        )

        require(
            not partial_plan.ready,
            "partial conversion must not be ready",
        )

        require(
            partial_plan.units[0].status
            == "partial",
            repr(partial_plan.units[0]),
        )

    print("CIPHER_PLAN=PASS")


if __name__ == "__main__":
    main()
