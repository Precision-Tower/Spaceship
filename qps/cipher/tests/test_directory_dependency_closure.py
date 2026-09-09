from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.plan import build_conversion_plan


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "src/pkg"
        source.mkdir(parents=True)
        destination = root / "translated/pkg"

        (source / "constants.py").write_text(
            "VALUE = 7\n",
            encoding="utf-8",
        )
        (source / "main.py").write_text(
            "from .constants import VALUE\n\n"
            "result = VALUE\n",
            encoding="utf-8",
        )

        plan = build_conversion_plan(
            source,
            destination,
            workspace_root=root,
        )

        require(plan.ready, repr(plan.blockers))
        require(plan.foreign == [], repr(plan.foreign))

        actual = {
            str(unit.source.relative_to(root)):
            str(unit.destination.relative_to(root))
            for unit in plan.units
        }

        require(
            actual
            == {
                "src/pkg/constants.py":
                    "translated/pkg/constants.qps",
                "src/pkg/main.py":
                    "translated/pkg/main.qps",
            },
            repr(actual),
        )

        require(
            len(plan.units) == 2,
            repr(plan.units),
        )

    print("CIPHER_DIRECTORY_DEPENDENCY_CLOSURE=PASS")


if __name__ == "__main__":
    main()
