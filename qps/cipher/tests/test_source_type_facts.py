from pathlib import Path
from tempfile import TemporaryDirectory

from qps.cipher.sources.python_source import load_python


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


with TemporaryDirectory() as temp:
    source = Path(temp) / "typed.py"
    source.write_text(
        """
def probe(name: str, mass: float, count: int, maybe: str | None):
    local: str = name
    text = f"{name} {mass} {count} {maybe}"
    return local
""".lstrip(),
        encoding="utf-8",
    )

    document = load_python(source)

    nodes = [
        node
        for child in document.children
        for node in walk(child)
    ]

    parameters = {
        node.name: node.source_type
        for node in nodes
        if node.kind == "parameter"
    }

    assert parameters["name"] == "str"
    assert parameters["mass"] == "float"
    assert parameters["count"] == "int"
    assert parameters["maybe"] == "str | None"

    local = next(
        node
        for node in nodes
        if node.kind == "assignment"
        and node.name == "local"
    )

    assert local.source_type == "str"

print("CIPHER_SOURCE_TYPE_FACTS=PASS")
