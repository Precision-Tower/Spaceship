from pathlib import Path

from qps.cipher.sources.python_source import load_python


def test_python_execution_structure(tmp_path: Path):
    source = tmp_path / "geometry.py"

    source.write_text(
        '''
def inner_radius(outer_radius, wall):
    result = outer_radius - wall
    return result

class Pipe:
    def __init__(self, outer_radius, wall):
        self.outer_radius = outer_radius
        self.inner_radius = outer_radius - wall
''',
        encoding="utf-8",
    )

    document = load_python(source)

    function = next(
        node
        for node in document.children
        if node.kind == "function"
        and node.name == "inner_radius"
    )

    execution = next(
        node
        for node in function.children
        if node.kind == "execution"
    )

    assignment = next(
        node
        for node in execution.children
        if node.kind == "assignment"
        and node.name == "result"
    )

    expression = assignment.children[0]

    assert expression.kind == "expression"
    assert expression.name == "subtract"
    assert expression.children[0].name == "outer_radius"
    assert expression.children[1].name == "wall"

    pipe = next(
        node
        for node in document.children
        if node.kind == "definition"
        and node.name == "Pipe"
    )

    init = next(
        node
        for node in pipe.children
        if node.kind == "function"
        and node.name == "__init__"
    )

    init_execution = next(
        node
        for node in init.children
        if node.kind == "execution"
    )

    inner = next(
        node
        for node in init_execution.children
        if node.kind == "assignment"
        and node.name == "self.inner_radius"
    )

    assert inner.children[0].name == "subtract"
