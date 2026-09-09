from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.sources.python_source import load_python


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


with TemporaryDirectory() as temp:
    source = Path(temp) / "typed_refs.py"

    source.write_text(
        """
def probe(name: str, mass: float):
    label: str = name
    numeric: int = 2
    text = f"{name} {mass} {label} {numeric}"
    other = thing.member
    return label
""".lstrip(),
        encoding="utf-8",
    )

    document = load_python(source)

    nodes = [
        node
        for child in document.children
        for node in walk(child)
    ]

    refs = [
        node
        for node in nodes
        if node.kind == "reference"
    ]

    def types_for(name):
        return [
            node.source_type
            for node in refs
            if node.name == name
        ]

    assert "str" in types_for("name")
    assert "float" in types_for("mass")
    assert "str" in types_for("label")
    assert "int" in types_for("numeric")

    member = next(
        node
        for node in refs
        if node.name == "thing.member"
    )

    assert member.source_type is None

print(
    "CIPHER_SOURCE_TYPE_REFERENCE_PROPAGATION=PASS"
)
