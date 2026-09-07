from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.sources.python_source import load_python
from Engineering.py.cipher.support import inspect_support


NEWLINE = chr(10)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def python_source(lines: list[str]) -> str:
    return NEWLINE.join(lines) + NEWLINE


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        simple = root / "simple.py"
        simple.write_text(
            python_source([
                "VALUE = 2",
                "",
                "def twice(x):",
                "    value = x * VALUE",
                "    return value",
            ]),
            encoding="utf-8",
        )

        simple_report = inspect_support(
            load_python(simple)
        )

        require(
            simple_report.status == "ready",
            repr(simple_report),
        )

        partial = root / "partial.py"
        partial.write_text(
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

        partial_report = inspect_support(
            load_python(partial)
        )

        require(
            partial_report.status == "partial",
            repr(partial_report),
        )

        joined = " | ".join(
            partial_report.reasons
        )

        require(
            "definition/object semantics"
            in joined,
            joined,
        )

        require(
            "foreign dependency"
            not in joined,
            joined,
        )

        require(
            "keyword"
            in joined,
            joined,
        )

        structured = root / "structured.py"
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

        structured_report = inspect_support(
            load_python(structured)
        )

        require(
            structured_report.status == "partial",
            repr(structured_report),
        )

        structured_reasons = " | ".join(
            structured_report.reasons
        )

        for reason in (
            "structured keyword-constructor",
            "keyword call arguments",
            "mapping expressions",
            "list expressions",
        ):
            require(
                reason in structured_reasons,
                structured_reasons,
            )

    print("CIPHER_SUPPORT=PASS")


if __name__ == "__main__":
    main()
