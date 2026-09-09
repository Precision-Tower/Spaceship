from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from qps.cipher.plan import build_conversion_plan


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "source.py"
        destination = root / "output.qps"

        source.write_text(
            "VALUE = 7\n",
            encoding="utf-8",
        )

        with patch(
            "qps.cipher.cipher.emit_prepared_document",
            side_effect=ValueError("synthetic emission failure"),
        ):
            plan = build_conversion_plan(
                source,
                destination,
                workspace_root=root,
            )

        require(not plan.ready, repr(plan))
        require(len(plan.units) == 1, repr(plan.units))
        require(
            plan.units[0].candidate is None,
            repr(plan.units[0]),
        )
        require(
            "synthetic emission failure"
            in plan.units[0].detail,
            plan.units[0].detail,
        )
        require(
            not destination.exists(),
            "failed planning mutated destination",
        )

    print("CIPHER_PLAN_EMISSION_FAILURE=PASS")


if __name__ == "__main__":
    main()
