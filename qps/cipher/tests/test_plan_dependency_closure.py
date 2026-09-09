from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from qps.cipher.plan import (
    PlannedUnit,
    build_conversion_plan,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)

        app = root / "app"
        pkg = app / "pkg"

        pkg.mkdir(parents=True)

        # The entry imports both:
        # - a concrete local module, which must remain helper.qps
        # - the local package itself, which resolves __init__.py and
        #   therefore must project to _index.qps.
        (app / "run.py").write_text(
            "import app.pkg\n"
            "from app.pkg.helper import helper\n"
            "value = helper()\n",
            encoding="utf-8",
        )

        (pkg / "__init__.py").write_text(
            "PACKAGE_VALUE = 1\n",
            encoding="utf-8",
        )

        (pkg / "helper.py").write_text(
            "def helper():\n"
            "    return 1\n",
            encoding="utf-8",
        )

        destination = (
            root
            / "translated"
            / "app"
            / "run.qps"
        )

        inspected = []

        def inspect(
            source,
            destination,
            *,
            workspace_root=None,
            resolved_dependencies=None,
        ):
            inspected.append(
                (
                    Path(source).resolve(),
                    Path(destination).resolve(),
                    set(resolved_dependencies or set()),
                )
            )

            return PlannedUnit(
                source=Path(source).resolve(),
                destination=Path(destination).resolve(),
                status="ready",
                candidate=(
                    "Candidate.\n\n"
                    "value- 1;\n"
                ),
            )

        with patch(
            "qps.cipher.plan._inspect_unit",
            side_effect=inspect,
        ):
            plan = build_conversion_plan(
                app / "run.py",
                destination,
                workspace_root=root,
            )

        require(
            plan.ready,
            repr(plan.blockers),
        )

        actual = {
            str(source.relative_to(root)):
            str(target.relative_to(root))
            for source, target, _ in inspected
        }

        expected = {
            "app/run.py":
                "translated/app/run.qps",
            "app/pkg/__init__.py":
                "translated/app/pkg/_index.qps",
            "app/pkg/helper.py":
                "translated/app/pkg/helper.qps",
        }

        require(
            actual == expected,
            repr(actual),
        )

        run_dependencies = next(
            dependencies
            for source, _, dependencies in inspected
            if source.name == "run.py"
        )

        require(
            (
                "app.pkg.helper",
                "helper",
                None,
            )
            in run_dependencies,
            repr(run_dependencies),
        )

        require(
            (
                "app.pkg",
                None,
                None,
            )
            in run_dependencies,
            repr(run_dependencies),
        )

        require(
            len(plan.units) == 3,
            repr(plan.units),
        )

    print(
        "CIPHER_PLAN_DEPENDENCY_CLOSURE=PASS"
    )


if __name__ == "__main__":
    main()
