from __future__ import annotations

import os
import tempfile
from pathlib import Path

from Engineering.py.cipher.plan import (
    build_conversion_plan,
)
from Engineering.py.cipher.publish import (
    publish_conversion,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    repo = Path(__file__).resolve().parents[4]

    os.environ["QPS_EXECUTABLE"] = str(
        repo / "qps/cpp/build-pixel/qps"
    )

    with tempfile.TemporaryDirectory(
        dir=os.environ.get("TMPDIR")
    ) as tmp:
        root = Path(tmp)

        source = root / "source.py"
        destination = root / "source.qps"

        source.write_text(
            "VALUE = 4\n"
            "\n"
            "def twice(x):\n"
            "    value = x * VALUE\n"
            "    return value\n",
            encoding="utf-8",
        )

        plan = build_conversion_plan(
            source,
            destination,
            workspace_root=root,
        )

        require(
            plan.ready,
            repr(plan.blockers),
        )

        require(
            len(plan.units) == 1,
            repr(plan.units),
        )

        unit = plan.units[0]

        require(
            unit.status == "ready",
            repr(unit),
        )

        require(
            unit.candidate is not None,
            repr(unit),
        )

        # If READY is true, publication of those already-proven bytes
        # must succeed without translating or validating them again.
        published = publish_conversion(
            plan,
            converge=True,
        )

        require(
            published == [destination],
            repr(published),
        )

        require(
            destination.read_text(
                encoding="utf-8"
            )
            == unit.candidate,
            "published bytes differ from validated candidate",
        )

    print(
        "CIPHER_BOOLEAN_TRUTH=PASS"
    )


if __name__ == "__main__":
    main()
