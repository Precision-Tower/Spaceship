from pathlib import Path

from qps.cipher.graph.dependency_closure import (
    build_dependency_closure,
    project_dependency_destinations,
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

    destination = (
        root
        / "Engineering/qps/Physics/Domains/motion.qps"
    )

    closure = build_dependency_closure(
        motion,
        root,
    )

    projected = project_dependency_destinations(
        closure,
        destination,
    )

    actual = {
        str(source.relative_to(root)):
        str(target.relative_to(root))
        for source, target in projected.items()
    }

    expected = {
        "Engineering/py/Physics/Domains/motion.py":
            "Engineering/qps/Physics/Domains/motion.qps",
        "Engineering/py/Physics/constants.py":
            "Engineering/qps/Physics/constants.qps",
        "Engineering/py/Physics/equations.py":
            "Engineering/qps/Physics/equations.qps",
    }

    require(
        actual == expected,
        repr(actual),
    )

    require(
        projected[motion.resolve()]
        == destination,
        "entry projection changed requested destination",
    )

    print("CIPHER_DEPENDENCY_PROJECTION=PASS")


if __name__ == "__main__":
    main()
