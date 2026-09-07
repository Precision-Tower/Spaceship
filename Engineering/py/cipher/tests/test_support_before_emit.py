from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.plan import (
    build_conversion_plan,
)


NEWLINE = chr(10)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def python_source(lines: list[str]) -> str:
    return NEWLINE.join(lines) + NEWLINE


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        source = root / "partial.py"
        destination = root / "partial.qps"

        source.write_text(
            python_source([
                "from dataclasses import dataclass",
                "",
                "@dataclass",
                "class Result:",
                "    value: float",
                "",
                "def build(x):",
                "    return Result(value=x)",
            ]),
            encoding="utf-8",
        )

        plan = build_conversion_plan(
            source,
            destination,
            workspace_root=root,
        )

        require(
            not plan.ready,
            "unsupported source unexpectedly ready",
        )

        require(
            len(plan.units) == 1,
            repr(plan.units),
        )

        unit = plan.units[0]

        require(
            unit.status == "partial",
            repr(unit),
        )

        require(
            unit.candidate is None,
            "unsupported transaction should not emit candidate bytes",
        )

        require(
            "keyword call arguments"
            in unit.detail,
            unit.detail,
        )

        require(
            not destination.exists(),
            "planning wrote destination",
        )

        structured = root / "structured.py"
        structured_destination = root / "structured.qps"

        structured.write_text(
            python_source([
                "def build(mass_kg, gravity_m_s2):",
                "    value = mass_kg * gravity_m_s2",
                "    return EquationResult(",
                "        equation_id=\"MC.weight_force\",",
                "        inputs={",
                "            \"mass_kg\": mass_kg,",
                "            \"gravity_m_s2\": gravity_m_s2,",
                "        },",
                "        blocked_interpretations=[",
                "            \"mass_equals_weight\",",
                "        ],",
                "    )",
            ]),
            encoding="utf-8",
        )

        structured_plan = build_conversion_plan(
            structured,
            structured_destination,
            workspace_root=root,
        )

        require(
            not structured_plan.ready,
            "structured source unexpectedly ready",
        )

        structured_unit = structured_plan.units[0]

        require(
            structured_unit.candidate is None,
            "structured partial source emitted candidate bytes",
        )

        for reason in (
            "structured keyword-constructor",
            "keyword call arguments",
            "mapping expressions",
            "list expressions",
        ):
            require(
                reason in structured_unit.detail,
                structured_unit.detail,
            )

        require(
            not structured_destination.exists(),
            "structured planning wrote destination",
        )

    print("CIPHER_SUPPORT_BEFORE_EMIT=PASS")


if __name__ == "__main__":
    main()
