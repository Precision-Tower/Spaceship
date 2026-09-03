from pathlib import Path

from Engineering.py.cipher.sources.cpp_source import load_cpp
from Engineering.py.cipher.mapping.geometry import (
    semantic_vocabulary,
)


def test_geometry_semantic_mapping(tmp_path: Path):
    source = tmp_path / "geometry.cpp"

    source.write_text(
        r'''
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepMesh_IncrementalMesh.hxx>

void build() {
    BRepPrimAPI_MakeCylinder cylinder(10.0, 20.0);

    BRepAlgoAPI_Cut cut(source, tool);

    BRepCheck_Analyzer analyzer(shape);

    BRepMesh_IncrementalMesh mesher(shape, 0.1);
    mesher.Perform();
}
''',
        encoding="utf-8",
    )

    document = load_cpp(source)

    vocabulary = semantic_vocabulary(document)

    assert "construct.cylinder" in vocabulary
    assert "boolean.cut" in vocabulary
    assert "validate.brep" in vocabulary
    assert "mesh.triangulate" in vocabulary
