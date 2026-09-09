from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.plan import (
    ConversionPlan,
    PlannedUnit,
)
from qps.cipher.publish import publish_conversion


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def unit(
    source: Path,
    destination: Path,
    candidate: str,
) -> PlannedUnit:
    return PlannedUnit(
        source=source,
        destination=destination,
        status="ready",
        candidate=candidate,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)

        source_root = root / "source"
        output = root / "translated"

        source_root.mkdir()

        run_source = source_root / "run.py"
        helper_source = source_root / "pkg/helper.py"
        index_source = source_root / "pkg/__init__.py"

        helper_source.parent.mkdir()

        for path in (
            run_source,
            helper_source,
            index_source,
        ):
            path.write_text(
                "# source\n",
                encoding="utf-8",
            )

        run_destination = output / "run.qps"
        helper_destination = output / "pkg/helper.qps"
        index_destination = output / "pkg/_index.qps"

        candidates = {
            run_destination:
                "Run.\n\nvalue- 1;\n",
            helper_destination:
                "Helper.\n\nvalue- 2;\n",
            index_destination:
                "Package.\n\nvalue- 3;\n",
        }

        plan = ConversionPlan(
            source=run_source,
            destination=run_destination,
            units=[
                unit(
                    run_source,
                    run_destination,
                    candidates[run_destination],
                ),
                unit(
                    helper_source,
                    helper_destination,
                    candidates[helper_destination],
                ),
                unit(
                    index_source,
                    index_destination,
                    candidates[index_destination],
                ),
            ],
        )

        published = publish_conversion(
            plan,
        )

        require(
            set(published) == set(candidates),
            repr(published),
        )

        for destination, expected in candidates.items():
            require(
                destination.read_text(
                    encoding="utf-8"
                )
                == expected,
                f"candidate bytes changed: {destination}",
            )

        # Duplicate destinations must be rejected before anything
        # can be published.
        duplicate_root = root / "duplicate"
        duplicate_destination = (
            duplicate_root / "same.qps"
        )

        duplicate_plan = ConversionPlan(
            source=run_source,
            destination=duplicate_destination,
            units=[
                unit(
                    run_source,
                    duplicate_destination,
                    "One.\n\nvalue- 1;\n",
                ),
                unit(
                    helper_source,
                    duplicate_destination,
                    "Two.\n\nvalue- 2;\n",
                ),
            ],
        )

        try:
            publish_conversion(
                duplicate_plan,
            )
        except RuntimeError as exc:
            require(
                "duplicate destinations" in str(exc),
                str(exc),
            )
        else:
            raise AssertionError(
                "duplicate destinations unexpectedly published"
            )

        require(
            not duplicate_destination.exists(),
            "duplicate plan touched destination",
        )

        # Rollback must preserve a pre-existing parent and unrelated
        # file while deleting every output created by the failed
        # transaction.
        rollback_root = root / "rollback"
        rollback_root.mkdir()

        sentinel = rollback_root / "keep.txt"
        sentinel.write_text(
            "KEEP\n",
            encoding="utf-8",
        )

        first = rollback_root / "pkg/one.qps"
        second = rollback_root / "pkg/two.qps"

        rollback_plan = ConversionPlan(
            source=run_source,
            destination=first,
            units=[
                unit(
                    run_source,
                    first,
                    "One.\n\nvalue- 1;\n",
                ),
                unit(
                    helper_source,
                    second,
                    "Two.\n\nvalue- 2;\n",
                ),
            ],
        )

        try:
            publish_conversion(
                rollback_plan,
                fail_after=1,
            )
        except RuntimeError as exc:
            require(
                "injected Cipher publication failure"
                in str(exc),
                str(exc),
            )
        else:
            raise AssertionError(
                "rollback injection did not fire"
            )

        require(
            not first.exists(),
            "first transaction file survived rollback",
        )

        require(
            not second.exists(),
            "second transaction file exists after rollback",
        )

        require(
            rollback_root.exists(),
            "pre-existing parent was removed",
        )

        require(
            sentinel.read_text(encoding="utf-8")
            == "KEEP\n",
            "unrelated file changed during rollback",
        )

    print(
        "CIPHER_MULTI_UNIT_TRANSACTION=PASS"
    )


if __name__ == "__main__":
    main()
