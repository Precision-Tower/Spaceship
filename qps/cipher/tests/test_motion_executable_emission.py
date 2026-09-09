from __future__ import annotations

from pathlib import Path

from qps.cipher.plan import (
    build_conversion_plan,
)
from qps.cipher.sources.python_source import (
    load_python,
)
from qps.cipher.support import (
    inspect_support,
)


def _repo_root() -> Path:
    current = Path(__file__).resolve().parent

    for candidate in (current, *current.parents):
        if (
            (candidate / ".git").exists()
            and (candidate / "qps").is_dir()
            and (candidate / "Engineering").is_dir()
        ):
            return candidate

    raise RuntimeError(
        "CE-OS repository root not found"
    )


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    root = _repo_root()

    motion = (
        root
        / "Engineering/py/Physics/Domains/motion.py"
    )

    document = load_python(motion)
    support = inspect_support(document)

    # Direct support inspection has no dependency-closure resolution
    # context. motion.py therefore remains partial here only because its
    # repository-local imports have not yet been supplied as resolved.
    # Mapping syntax itself is now supported.
    require(
        support.status == "partial",
        repr(support),
    )

    reasons = " | ".join(
        support.reasons
    )

    require(
        "foreign dependency remains unresolved"
        in reasons,
        reasons,
    )

    require(
        "mapping expressions are not emitted"
        not in reasons,
        reasons,
    )

    require(
        "keyword call arguments are not emitted"
        not in reasons,
        reasons,
    )

    require(
        "structured keyword-constructor return is not emitted"
        not in reasons,
        reasons,
    )

    destination = (
        root
        / "trash/tmp/cipher-motion-test"
        / "Engineering/qps/Physics/Domains/motion.qps"
    )

    plan = build_conversion_plan(
        motion,
        destination,
        workspace_root=root,
    )

    require(
        plan.ready,
        "motion dependency closure did not produce a ready plan",
    )

    units = {
        str(unit.source.relative_to(root)):
        unit
        for unit in plan.units
    }

    require(
        {
            "Engineering/py/Physics/Domains/motion.py",
            "Engineering/py/Physics/constants.py",
            "Engineering/py/Physics/equations.py",
        }.issubset(units),
        repr(units),
    )

    motion_unit = units[
        "Engineering/py/Physics/Domains/motion.py"
    ]

    require(
        motion_unit.status == "ready",
        repr(motion_unit),
    )

    require(
        motion_unit.candidate is not None,
        "ready motion unit owns no candidate bytes",
    )

    require(
        "inputs: ("
        in motion_unit.candidate,
        motion_unit.candidate,
    )

    require(
        "mass_kg- mass_kg;"
        in motion_unit.candidate,
        motion_unit.candidate,
    )

    require(
        "gravity_m_s2- gravity_m_s2;"
        in motion_unit.candidate,
        motion_unit.candidate,
    )

    require(
        "EquationResult("
        in motion_unit.candidate,
        motion_unit.candidate,
    )

    require(
        str(
            units[
                "Engineering/py/Physics/constants.py"
            ].destination.relative_to(root)
        ).endswith(
            "Engineering/qps/Physics/constants.qps"
        ),
        repr(units),
    )

    require(
        str(
            units[
                "Engineering/py/Physics/equations.py"
            ].destination.relative_to(root)
        ).endswith(
            "Engineering/qps/Physics/equations.qps"
        ),
        repr(units),
    )

    print(
        "CIPHER_MOTION_SUPPORT_TOPOLOGY=PASS"
    )


if __name__ == "__main__":
    main()
