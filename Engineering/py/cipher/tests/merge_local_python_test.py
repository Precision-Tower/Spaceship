from __future__ import annotations

from pathlib import Path

from Engineering.py.cipher.graph.merge import merge_local_python


def main() -> None:
    root = Path(__file__).resolve().parents[4]

    merged = merge_local_python(
        root / "Engineering/py/Physics/Domains/motion.py",
        root,
    )

    units = {
        str(path.relative_to(root))
        for path in merged.closure.units
    }

    assert units == {
        "Engineering/py/Physics/Domains/motion.py",
        "Engineering/py/Physics/constants.py",
        "Engineering/py/Physics/equations.py",
    }

    # Local Engineering imports must disappear from the merged IR.
    local_imports = []

    foreign_imports = []

    for node in merged.document.children:
        if node.kind != "import":
            continue

        for dependency in node.dependencies:
            module = dependency.module or dependency.package

            if module.startswith("Engineering."):
                local_imports.append(module)
            else:
                foreign_imports.append(
                    (
                        module,
                        dependency.symbol,
                    )
                )

    assert local_imports == [], local_imports

    assert (
        "dataclasses",
        "dataclass",
    ) in foreign_imports

    assert (
        "dataclasses",
        "field",
    ) in foreign_imports

    assert (
        "typing",
        "Any",
    ) in foreign_imports

    # Local definitions were physically absorbed.
    names = [
        node.name
        for node in merged.document.children
        if node.name
    ]

    assert "weight_force_n" in names
    assert "GRAVITY_EARTH_M_S2" in names
    assert "EquationResult" in names

    # Each local module appears once in the closure.
    assert len(merged.closure.units) == 3

    print("Cipher local Python merge: PASS")


if __name__ == "__main__":
    main()
