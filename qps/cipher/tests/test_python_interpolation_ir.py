from pathlib import Path

from qps.cipher.sources.python_source import load_python
from qps.cipher.reports.inspect import unresolved


def test_python_fstring_is_preserved(tmp_path: Path):
    source = tmp_path / "message.py"

    source.write_text(
        '''
def fail(radius):
    raise ValueError(f"bad radius {radius}")
''',
        encoding="utf-8",
    )

    document = load_python(source)

    assert unresolved(document) == []

    function = next(
        node
        for node in document.children
        if node.kind == "function"
    )

    body = next(
        node
        for node in function.children
        if node.kind == "execution"
    )

    raise_node = next(
        node
        for node in body.children
        if node.kind == "raise"
    )

    call = raise_node.children[0]
    interpolation = call.children[0].children[0]

    assert interpolation.kind == "interpolation"
    assert interpolation.state.value == "mapped"
