from __future__ import annotations

import os
import tempfile
from pathlib import Path

from Engineering.py.cipher.plan import build_conversion_plan
from Engineering.py.cipher.publish import publish_conversion


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    repo = Path(__file__).resolve().parents[4]
    os.environ["QPS_EXECUTABLE"] = str(
        repo / "qps/cpp/build-pixel/qps"
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source.py"
        destination = root / "output.qps"

        source.write_text(
            "VALUE = 7\n",
            encoding="utf-8",
        )

        plan = build_conversion_plan(
            source,
            destination,
            workspace_root=repo,
        )

        require(plan.ready, repr(plan.blockers))
        require(len(plan.units) == 1, repr(plan.units))

        unit = plan.units[0]
        require(unit.candidate is not None, repr(unit))
        candidate = unit.candidate

        # Mutate the source after planning. Publication must use the
        # candidate owned by the transaction, not translate again.
        source.write_text(
            "VALUE = 999\n",
            encoding="utf-8",
        )

        published = publish_conversion(
            plan,
            converge=True,
        )

        require(
            published == [destination],
            repr(published),
        )

        require(
            destination.read_text(encoding="utf-8")
            == candidate,
            "publication did not preserve planned candidate bytes",
        )

    print("CIPHER_TRANSACTION_CANDIDATE=PASS")


if __name__ == "__main__":
    main()
