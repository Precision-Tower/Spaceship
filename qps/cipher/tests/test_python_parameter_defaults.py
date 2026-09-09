from pathlib import Path

from qps.cipher.sources.python_source import load_python


def main():
    source = Path(
        "Engineering/py/Physics/Domains/motion.py"
    )

    document = load_python(source)

    function = next(
        node
        for node in document.children
        if node.kind == "function"
        and node.name == "weight_force_n"
    )

    gravity = next(
        child
        for child in function.children
        if child.kind == "parameter"
        and child.name == "gravity_m_s2"
    )

    assert gravity.value is None
    assert len(gravity.children) == 1

    default = gravity.children[0]

    assert default.kind == "default"
    assert len(default.children) == 1

    reference = default.children[0]

    assert reference.kind == "reference"
    assert reference.name == "GRAVITY_EARTH_M_S2"

    print("Cipher parameter defaults: PASS")


if __name__ == "__main__":
    main()
