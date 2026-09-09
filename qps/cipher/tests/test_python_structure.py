from pathlib import Path

from qps.cipher.emit.qps_emitter import emit_qps
from qps.cipher.ir.nodes import TranslationState
from qps.cipher.sources.python_source import load_python


def test_python_class_and_function_structure(tmp_path: Path):
    source = tmp_path / "pipe.py"

    source.write_text(
        '''
PIPE_KIND = "pipe"

class Pipe:
    """Engineering pipe article."""

    family = "pipe"

    def __init__(self, od, length=100):
        self.od = od
        self.length = length

    def volume(self):
        return 3.14
''',
        encoding="utf-8",
    )

    document = load_python(source)

    names = [
        node.name
        for node in document.children
    ]

    assert "PIPE_KIND" in names
    assert "Pipe" in names

    pipe = next(
        node
        for node in document.children
        if node.name == "Pipe"
    )

    init = next(
        child
        for child in pipe.children
        if child.kind == "function"
        and child.name == "__init__"
    )

    body = next(
        child
        for child in init.children
        if child.kind == "execution"
    )

    assert body.state == TranslationState.DEFERRED

    qps = emit_qps(document)

    assert 'PIPE_KIND- "pipe"/a;' in qps
    assert "Pipe: (" in qps
    assert "__init__: (" in qps
    assert "length- 100;" in qps
    assert "body- /n;" in qps
