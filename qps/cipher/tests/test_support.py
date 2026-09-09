from __future__ import annotations

import tempfile
from pathlib import Path

from qps.cipher.sources.python_source import load_python
from qps.cipher.support import inspect_support


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
                "def build(x):",
                "    return x if x else 0",
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
            "conditional expressions are not emitted"
            in joined,
            joined,
        )

        require(
            "foreign dependency"
            not in joined,
            joined,
        )

        require(
            "keyword call arguments"
            not in joined,
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
            structured_report.status == "ready",
            repr(structured_report),
        )

        structured_reasons = " | ".join(
            structured_report.reasons
        )

        require(
            "mapping expressions are not emitted"
            not in structured_reasons,
            structured_reasons,
        )

        require(
            "structured keyword-constructor"
            not in structured_reasons,
            structured_reasons,
        )

        require(
            "keyword call arguments"
            not in structured_reasons,
            structured_reasons,
        )

    print("CIPHER_SUPPORT=PASS")


if __name__ == "__main__":
    main()
