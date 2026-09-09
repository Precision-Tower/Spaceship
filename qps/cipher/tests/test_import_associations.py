from pathlib import Path

from qps.cipher.emit.associations_qps import (
    emit_association,
)
from qps.cipher.graph.dependency_closure import (
    build_dependency_closure,
    project_dependency_destinations,
    resolve_local_import,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    root = Path.cwd().resolve()

    motion = (
        root
        / "Engineering/py/Physics/Domains/motion.py"
    )

    motion_qps = (
        root
        / "Engineering/qps/Physics/Domains/motion.qps"
    )

    closure = build_dependency_closure(
        motion,
        root,
    )

    projection = project_dependency_destinations(
        closure,
        motion_qps,
    )

    emitted = {}

    for binding in closure.units[motion.resolve()].imports:
        dependency = resolve_local_import(
            motion,
            binding,
            root,
        )

        if dependency is None:
            continue

        association = emit_association(
            local_name=binding.local_name,
            source_qps=projection[motion.resolve()],
            target_qps=projection[dependency],
            target_identity=binding.symbol,
        )

        emitted[
            binding.symbol or binding.module
        ] = association

    require(
        emitted.get("EquationResult")
        == (
            "EquationResult: "
            "[>/equations.EquationResult];"
        ),
        repr(emitted),
    )

    require(
        emitted.get("GRAVITY_EARTH_M_S2")
        == (
            "GRAVITY_EARTH_M_S2: "
            "[>/constants.GRAVITY_EARTH_M_S2];"
        ),
        repr(emitted),
    )

    print("CIPHER_PROJECTED_ASSOCIATIONS=PASS")


if __name__ == "__main__":
    main()
