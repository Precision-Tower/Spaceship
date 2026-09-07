from __future__ import annotations

import tempfile
from pathlib import Path

from Engineering.py.cipher.graph.dependency_closure import (
    build_dependency_closure,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)

        write(
            root / "Engineering/py/Physics/constants.py",
            "GRAVITY = 9.80665\n",
        )

        write(
            root / "Engineering/py/Physics/equations.py",
            "from dataclasses import dataclass\n"
            "from typing import Any\n"
            "\n"
            "class EquationResult:\n"
            "    pass\n",
        )

        write(
            root / "Engineering/py/Physics/Domains/motion.py",
            "from Engineering.py.Physics.constants "
            "import GRAVITY as gravity\n"
            "from Engineering.py.Physics.equations "
            "import EquationResult\n"
            "\n"
            "def weight(mass):\n"
            "    return mass * gravity\n",
        )

        closure = build_dependency_closure(
            root / "Engineering/py/Physics/Domains/motion.py",
            root,
        )

        relative_units = {
            str(path.relative_to(root))
            for path in closure.units
        }

        expected = {
            "Engineering/py/Physics/Domains/motion.py",
            "Engineering/py/Physics/constants.py",
            "Engineering/py/Physics/equations.py",
        }

        assert relative_units == expected, (
            relative_units
        )

        external = {
            (
                binding.module,
                binding.symbol,
                binding.alias,
            )
            for binding in closure.external
        }

        assert (
            "dataclasses",
            "dataclass",
            None,
        ) in external

        assert (
            "typing",
            "Any",
            None,
        ) in external

        motion = closure.units[
            (
                root
                / "Engineering/py/Physics/Domains/motion.py"
            ).resolve()
        ]

        gravity = next(
            binding
            for binding in motion.imports
            if binding.symbol == "GRAVITY"
        )

        assert gravity.alias == "gravity"
        assert gravity.local_name == "gravity"

    # Real repository acceptance case.
    repo_root = Path(__file__).resolve().parents[4]

    real = build_dependency_closure(
        repo_root / "Engineering/py/Physics/Domains/motion.py",
        repo_root,
    )

    real_relative = {
        str(path.relative_to(repo_root))
        for path in real.units
    }

    assert (
        "Engineering/py/Physics/Domains/motion.py"
        in real_relative
    )
    assert (
        "Engineering/py/Physics/constants.py"
        in real_relative
    )
    assert (
        "Engineering/py/Physics/equations.py"
        in real_relative
    )

    real_external = {
        (
            binding.module,
            binding.symbol,
        )
        for binding in real.external
    }

    assert ("dataclasses", "dataclass") in real_external
    assert ("dataclasses", "field") in real_external
    assert ("typing", "Any") in real_external

    print("Cipher dependency closure: PASS")


if __name__ == "__main__":
    main()
