from pathlib import Path

from Engineering.py.cipher.sources.cpp_source import load_cpp
from Engineering.py.cipher.reports.inspect import unresolved


def test_cpp_geometry_surface(tmp_path: Path):
    source = tmp_path / "geometry.cpp"

    source.write_text(
        r'''
#include <Shape.hxx>

void execute(const Step& step) {
    if (step.operation == "cylinder") {
        MakeCylinder(step.radius, step.width);
    }

    if (step.operation == "bore") {
        Cut(source, tool);
    }
}
''',
        encoding="utf-8",
    )

    document = load_cpp(source)

    assert unresolved(document) == []

    function = next(
        node
        for node in document.children
        if node.kind == "function"
        and node.name == "execute"
    )

    body = next(
        node
        for node in function.children
        if node.kind == "execution"
    )

    comparisons = [
        child
        for child in body.children
        if child.kind == "comparison"
    ]

    assert {node.value for node in comparisons} == {
        "cylinder",
        "bore",
    }

    calls = {
        child.name
        for child in body.children
        if child.kind == "call"
    }

    assert "MakeCylinder" in calls
    assert "Cut" in calls
